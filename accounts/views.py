from datetime import datetime  
import json
import random
import requests
from django.shortcuts import render, redirect
from django.forms import ValidationError
from .models import Account, Transaction, CustomUser,Beneficiary
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_sms
from django.db.models import Case, When, Value, CharField, Count,Sum,Q
from django.views.decorators.csrf import csrf_exempt
import stripe
import google.generativeai as genai
import locale


locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')  # Définir la locale en français



# Configurer Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

stripe.api_key = settings.STRIPE_SECRET_KEY


def register(request):
    if request.method == 'POST':
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        ville = request.POST.get('ville')
        numero_telephone = request.POST.get('numero_telephone')
        emploi = request.POST.get('emploi')
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        image = request.FILES.get('image')

        # Vérifie si l'email existe déjà
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé. Veuillez en choisir un autre.')
            return redirect('register')  # Redirige vers la page d'inscription

        # Créer l'utilisateur
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            nom=nom,
            prenom=prenom,
            ville=ville,
            numero_telephone=numero_telephone,
            emploi=emploi,
            email=email,
            image=image
        )
        user.save()

        # Connecter l'utilisateur
        login(request, user)
        return redirect('dashboard')  # Rediriger vers le tableau de bord

    return render(request, 'register.html')



def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authentifier l'utilisateur
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')  # Rediriger vers le tableau de bord
        else:
            # Afficher un message d'erreur
            return render(request, 'login.html', {'error': 'Nom d\'utilisateur ou mot de passe incorrect.'})

    return render(request, 'login.html')





@csrf_exempt
def chatbot_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '').lower()  # Convertir en minuscules pour faciliter la comparaison

        # Réponses prédéfinies en fonction de l'intention de l'utilisateur
        if "effectue un transfert de" in user_message:
            try:
                # Extraire le montant et le nom du bénéficiaire
                parts = user_message.split(" ")
                amount = float(parts[3])  # Montant
                beneficiary_name = " ".join(parts[5:])  # Nom du bénéficiaire

                # Récupérer le compte de l'utilisateur
                sender_account = Account.objects.filter(user=request.user).first()
                if not sender_account:
                    return JsonResponse({'response': "Aucun compte trouvé."})

                # Récupérer le compte du bénéficiaire
                beneficiary_account = Account.objects.filter(user__username=beneficiary_name).first()
                if not beneficiary_account:
                    return JsonResponse({'response': f"Bénéficiaire '{beneficiary_name}' introuvable."})

                # Vérifier le solde
                if sender_account.balance < amount:
                    return JsonResponse({'response': "Solde insuffisant."})

                # Effectuer le transfert
                Transaction.objects.create(
                    sender=sender_account,
                    receiver=beneficiary_account,
                    amount=amount,
                    status='completed'
                )

                # Mettre à jour les soldes
                sender_account.balance -= amount
                beneficiary_account.balance += amount
                sender_account.save()
                beneficiary_account.save()

                response_text = f"Transfert de {amount} € à {beneficiary_name} effectué avec succès."
            except Exception as e:
                response_text = f"Erreur lors du transfert : {str(e)}"

        elif "solde" in user_message:
            # Récupérer le solde de l'utilisateur
            account = Account.objects.filter(user=request.user).first()
            if account:
                response_text = f"Votre solde actuel est de {account.balance} €."
            else:
                response_text = "Aucun compte trouvé."

        elif "dernières transactions" in user_message:
            # Récupérer les 5 dernières transactions
            transactions = Transaction.objects.filter(
                Q(sender__user=request.user) | Q(receiver__user=request.user)
            ).order_by('-timestamp')[:5]
            if transactions:
                response_text = "Voici vos 5 dernières transactions :\n"
                for transaction in transactions:
                    response_text += f"- {transaction.amount} € ({transaction.timestamp})\n"
            else:
                response_text = "Aucune transaction trouvée."

        elif "transactions du" in user_message:
            # Extraire la date du message
            try:
                date_str = user_message.split("transactions du ")[1].strip()
                date_obj = datetime.strptime(date_str, "%d %B").replace(year=datetime.now().year)  # Format : "2 janvier"
                transactions = Transaction.objects.filter(
                    (Q(sender__user=request.user) | Q(receiver__user=request.user)) &
                    Q(timestamp__date=date_obj)
                )
                if transactions:
                    response_text = f"Voici vos transactions du {date_str} :\n"
                    for transaction in transactions:
                        response_text += f"- {transaction.amount} € ({transaction.timestamp})\n"
                else:
                    response_text = f"Aucune transaction trouvée pour le {date_str}."
            except Exception as e:
                response_text = f"Erreur : {str(e)}. Veuillez spécifier une date valide (ex: '2 janvier')."

        elif "effectuer un transfert" in user_message:
            # Donner des instructions pour effectuer un transfert
            response_text = "Pour effectuer un transfert, veuillez suivre ces étapes :\n1. Cliquez sur 'Effectuer un transfert'.\n2. Sélectionnez un bénéficiaire.\n3. Entrez le montant.\n4. Confirmez la transaction."

        elif "ajouter un bénéficiaire" in user_message:
            # Donner des instructions pour ajouter un bénéficiaire
            response_text = "Pour ajouter un bénéficiaire, veuillez suivre ces étapes :\n1. Cliquez sur 'Bénéficiaires'.\n2. Cliquez sur 'Ajouter un bénéficiaire'.\n3. Remplissez les informations requises.\n4. Confirmez l'ajout."

        else:
            # Si l'intention n'est pas reconnue, utiliser Gemini pour générer une réponse
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(user_message)
            response_text = response.text

        return JsonResponse({'response': response_text})

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required
def update_profile(request):
    user = request.user

    if request.method == 'POST':
        # Mettre à jour les champs du profil
        user.nom = request.POST.get('nom', user.nom)
        user.prenom = request.POST.get('prenom', user.prenom)
        user.email = request.POST.get('email', user.email)
        user.ville = request.POST.get('ville', user.ville)
        user.numero_telephone = request.POST.get('numero_telephone', user.numero_telephone)
        user.emploi = request.POST.get('emploi', user.emploi)

        # Gérer l'upload de l'image de profil
        if 'image' in request.FILES:
            user.image = request.FILES['image']

        try:
            user.full_clean()  # Valider les champs du modèle
            user.save()
            messages.success(request, 'Profil mis à jour avec succès.')
        except ValidationError as e:
            # Afficher les erreurs de validation
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect('dashboard')

    # Afficher le formulaire de mise à jour du profil
    return render(request, 'dashboard.html', {'user': user})


@csrf_exempt
@login_required
def transfer_funds(request):
    if request.method == 'POST':
        # Étape 1 : Récupérer les données du formulaire
        receiver_username = request.POST.get('receiver')
        receiver_email = request.POST.get('email')
        receiver_account_number = request.POST.get('account_number')
        source_bank_id = request.POST.get('source_bank')
        amount = Decimal(request.POST.get('amount'))
        sender_currency = request.POST.get('sender_currency')
        receiver_currency = request.POST.get('receiver_currency')
        description = request.POST.get('description', '')

        # Valider les données
        if not receiver_username or not receiver_account_number or not source_bank_id or not amount:
            return JsonResponse({'success': False, 'message': 'Veuillez remplir tous les champs obligatoires.'})

        try:
            # Récupérer le compte source
            sender = Account.objects.get(id=source_bank_id, user=request.user)
        except Account.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Compte source invalide.'})

        try:
            # Récupérer le compte du destinataire
            receiver = Account.objects.get(numero_compte=receiver_account_number, user__username=receiver_username)
        except Account.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Destinataire introuvable.'})

        # Vérifier le solde de l'expéditeur
        if sender.balance < amount:
            return JsonResponse({'success': False, 'message': 'Solde insuffisant.'})

        # Générer un code OTP
        otp = str(random.randint(100000, 999999))  # Code à 6 chiffres
        print(otp)
        request.session['otp'] = otp  # Stocker le code OTP dans la session
        request.session['transfer_data'] = {  # Stocker les données du transfert
            'receiver_username': receiver_username,
            'receiver_account_number': receiver_account_number,
            'source_bank_id': source_bank_id,
            'amount': str(amount),
            'sender_currency': sender_currency,
            'receiver_currency': receiver_currency,
            'description': description,
        }

        # Envoyer le code OTP par SMS
        try:
            message = f"Votre code OTP pour confirmer le transfert est : {otp}"
            send_sms(sender.user.numero_telephone, message)
            return JsonResponse({'success': True, 'step': 'otp', 'message': 'Un code OTP a été envoyé à votre numéro de téléphone.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Échec de l'envoi du code OTP : {str(e)}"})

    # Étape 2 : Confirmation du transfert avec le code OTP
    elif request.method == 'PUT':
        data = json.loads(request.body)
        otp = data.get('otp')
        transfer_data = request.session.get('transfer_data')

        if not otp or not transfer_data:
            return JsonResponse({'success': False, 'message': 'Données de transfert invalides.'})

        if otp != request.session.get('otp'):
            return JsonResponse({'success': False, 'message': 'Code OTP incorrect.'})

        # Récupérer les données du transfert
        receiver_username = transfer_data['receiver_username']
        receiver_account_number = transfer_data['receiver_account_number']
        source_bank_id = transfer_data['source_bank_id']
        amount = Decimal(transfer_data['amount'])
        sender_currency = transfer_data['sender_currency']
        receiver_currency = transfer_data['receiver_currency']
        description = transfer_data['description']

        # Récupérer les comptes
        sender = Account.objects.get(id=source_bank_id, user=request.user)
        receiver = Account.objects.get(numero_compte=receiver_account_number, user__username=receiver_username)

        # Convertir le montant si les devises sont différentes
        if sender_currency != receiver_currency:
            url = f"https://api.exchangerate-api.com/v4/latest/{sender_currency}"
            response = requests.get(url)
            data = response.json()
            rate = data['rates'][receiver_currency]
            converted_amount = amount * Decimal(rate)
        else:
            converted_amount = amount

        # Effectuer le transfert desormais dans le signale
        # sender.balance -= amount
        # receiver.balance += converted_amount
        # sender.save()
        # receiver.save()

        # Enregistrer la transaction
        Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            sender_currency=sender_currency,
            receiver_currency=receiver_currency,
            converted_amount=converted_amount,
            description=description,
            status='completed'
        )

        # Envoyer un SMS à l'expéditeur
        try:
            sender_message = f"Vous avez transféré {amount} {sender_currency} à {receiver_username}."
            send_sms(sender.user.numero_telephone, sender_message)
        except Exception as e:
            print(f"Échec de l'envoi du SMS à l'expéditeur : {str(e)}")

        # Envoyer un SMS au destinataire
        try:
            receiver_message = f"Vous avez reçu {converted_amount} {receiver_currency} de {sender.user.username}."
            send_sms(receiver.user.numero_telephone, receiver_message)
        except Exception as e:
            print(f"Échec de l'envoi du SMS au destinataire : {str(e)}")

        # Nettoyer la session
        del request.session['otp']
        del request.session['transfer_data']

        return JsonResponse({'success': True, 'message': f'Transfert de {amount} {sender_currency} vers {receiver_username} réussi !'})

    # Récupérer les comptes de l'utilisateur pour le formulaire
    bank_accounts = Account.objects.filter(user=request.user)
    return render(request, 'transfer.html', {'active_view': 'transfer_funds', 'bank_accounts': bank_accounts})



@login_required
def dashboard(request):
    try:
        # Récupère le premier compte de l'utilisateur connecté
        account = request.user.accounts.first()
        if not account:
            # Si l'utilisateur n'a pas de compte, redirige vers une page d'erreur
            return redirect('erreur')  # Remplace 'erreur' par l'URL de ton choix
    except AttributeError:
        # Si l'utilisateur n'a pas de compte, redirige vers une page d'erreur
        return redirect('erreur')

    # Récupère les 5 dernières transactions de l'utilisateur
    recent_transactions = Transaction.objects.filter(
        Q(sender=account) | Q(receiver=account)
    ).order_by('-timestamp')[:5]

    return render(request, 'dashboard.html', {
        'account': account,
        'recent_transactions': recent_transactions,
        'active_view': 'dashboard',
    })



@login_required
def transaction_history(request):
    try:
        # Récupère le premier compte de l'utilisateur connecté
        account = request.user.accounts.first()
        if not account:
            # Si l'utilisateur n'a pas de compte, rediriger vers une page d'erreur
            return redirect('erreur')  
    except AttributeError:
        # Si l'utilisateur n'a pas de compte, rediriger vers une page d'erreur
        return redirect('erreur')

    # Récupère toutes les transactions de l'utilisateur
    transactions = Transaction.objects.filter(
        Q(sender=account) | Q(receiver=account)
    ).order_by('-timestamp')

    return render(request, 'history.html', {
        'transactions': transactions,
        'active_view': 'transaction_history',
    })



@login_required
def add_beneficiary(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        account_number = request.POST.get('account_number')
        bank_name = request.POST.get('bank_name')

        # Créer le bénéficiaire
        beneficiary = Beneficiary.objects.create(
            user=request.user,
            name=name,
            account_number=account_number,
            bank_name=bank_name
        )

        # Envoyer un SMS de confirmation
        try:
            message = f"Bonjour {request.user.username}, le bénéficiaire {name} a été ajouté avec succès."
            send_sms(request.user.numero_telephone, message)  # Envoie un SMS
            messages.success(request, 'Bénéficiaire ajouté avec succès et SMS envoyé.')
        except Exception as e:
            messages.warning(request, f"Bénéficiaire ajouté, mais échec de l'envoi du SMS : {str(e)}")

        return redirect('dashboard')

    return render(request, 'add_beneficiary.html',{'active_view' :'list_beneficiaries'})




@login_required
def view_cards(request):
    # Récupérer les comptes de l'utilisateur connecté
    accounts = request.user.accounts.all()
    return render(request, 'view_cards.html', {'accounts': accounts,'active_view' :'view_cards'})



@login_required
def list_beneficiaries(request):
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'list_beneficiary.html', {
        'beneficiaries': beneficiaries,
        'active_view' :'list_beneficiaries'
    })




@login_required
def transaction_statistics(request):
    # Données pour le diagramme linéaire (évolution des transactions par jour)
    daily_transactions = Transaction.objects.extra(
        select={'day': 'DATE(timestamp)'}
    ).values('day').annotate(total=Count('id')).order_by('day')

    # Données pour le diagramme en camembert (répartition des transactions par statut)
    status_distribution = Transaction.objects.values('status').annotate(total=Count('id'))

    # Données pour l'histogramme (montant des transactions)
    amount_distribution = Transaction.objects.annotate(
        amount_range=Case(
            When(amount__lt=100, then=Value('0-100')),
            When(amount__gte=100, amount__lt=200, then=Value('100-200')),
            When(amount__gte=200, amount__lt=500, then=Value('200-500')),
            When(amount__gte=500, amount__lt=1000, then=Value('500-1000')),
            When(amount__gte=1000, then=Value('1000+')),
            default=Value('Other'),
            output_field=CharField(),
        )
    ).values('amount_range').annotate(total=Count('id')).order_by('amount_range')

    # Données pour le diagramme en barres (transactions par utilisateur)
    user_transactions = Transaction.objects.exclude(sender__user__username__isnull=True).values('sender__user__username').annotate(total=Count('id')).order_by('-total')

    context = {
        'daily_transactions': list(daily_transactions),
        'status_distribution': list(status_distribution),
        'amount_distribution': list(amount_distribution),
        'user_transactions': list(user_transactions),
        'active_view': 'transaction_statistics'
    }
    print("Daily Transactions:", daily_transactions)
    print("Status Distribution:", status_distribution)
    print("Amount Distribution:", amount_distribution)
    print("User Transactions:", user_transactions)
    return render(request, 'statistics.html', context)



@login_required
def stripe_payment(request):
    if request.method == 'POST':
        amount = int(float(request.POST.get('amount')) * 100)  # Montant en cents
        stripe_token = request.POST.get('stripeToken')  # Token Stripe

        # Récupérer le compte de l'utilisateur
        user = request.user
        account = Account.objects.filter(user=user).first()

        # Vérifier si le compte existe
        if not account:
            return JsonResponse({'error': 'Aucun compte trouvé pour cet utilisateur.'}, status=400)

        try:
            # Créer un paiement avec Stripe
            charge = stripe.Charge.create(
                amount=amount,
                currency='eur',
                source=stripe_token,
                description='Recharge de compte',
            )

            # Recharger le compte de l'utilisateur
            account.balance += Decimal(amount) / 100  # Convertir en euros
            account.save()

            # Enregistrer la transaction réussie
            Transaction.objects.create(
                receiver=account,  # Le compte rechargé
                amount=Decimal(amount) / 100,  # Montant en euros
                sender_currency='EUR',
                receiver_currency='EUR',
                description='Recharge Stripe',
                status='completed',
                type='recharge',  # Type de transaction
            )

            return JsonResponse({'success': True})

        except stripe.error.CardError as e:
            # Enregistrer une transaction échouée en cas d'erreur de carte
            Transaction.objects.create(
                receiver=account,
                amount=Decimal(amount) / 100,
                sender_currency='EUR',
                receiver_currency='EUR',
                description=f'Recharge Stripe échouée: {str(e)}',
                status='failed',
                type='recharge',
            )
            return JsonResponse({'error': str(e)}, status=400)

        except Exception as e:
            # Enregistrer une transaction échouée en cas d'erreur inattendue
            Transaction.objects.create(
                receiver=account,
                amount=Decimal(amount) / 100,
                sender_currency='EUR',
                receiver_currency='EUR',
                description=f'Recharge Stripe échouée: {str(e)}',
                status='failed',
                type='recharge',
            )
            return JsonResponse({'error': str(e)}, status=400)  # Affiche l'erreur réelle

    # Passer la clé publique Stripe au template
    context = {
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        'active_view':'stripe_payment'
    }
    return render(request, 'stripe_payment.html', context)



@csrf_exempt
def stripe_webhook(request): 
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user = request.user
        amount = session['amount_total'] / 100  # Convertir en euros
        # Recharger le compte de l'utilisateur
        account = Account.objects.get(user=user)
        account.balance += Decimal(amount)
        account.save()

    return JsonResponse({'success': True})


def user_logout(request):
    logout(request)  # Déconnecte l'utilisateur
    return redirect('login')  # Redirige vers la page de connexion
