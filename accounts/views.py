from django.shortcuts import render, redirect
from .models import Account, Transaction, CustomUser,Beneficiary
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db.models import Q ,Count, Sum
from decimal import Decimal
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_sms



def register(request):
    if request.method == 'POST':
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        ville = request.POST.get('ville')
        numero_telephone = request.POST.get('numero_telephone')
        emploi = request.POST.get('emploi')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Créer l'utilisateur
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            nom=nom,
            prenom=prenom,
            ville=ville,
            numero_telephone=numero_telephone,
            emploi=emploi
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



@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.nom = request.POST.get('nom')
        user.prenom = request.POST.get('prenom')
        user.email = request.POST.get('email')
        user.ville = request.POST.get('ville')
        user.numero_telephone = request.POST.get('numero_telephone')
        user.emploi = request.POST.get('emploi')
        user.save()
        messages.success(request, 'Profil mis à jour avec succès.')
        return redirect('dashboard')

    return render(request, 'dashboard.html')



# views.py
@login_required
def transfer_funds(request):
    if request.method == 'POST':
        receiver_username = request.POST.get('receiver')
        amount = Decimal(request.POST.get('amount'))
        description = request.POST.get('description', '')

        try:
            receiver = Account.objects.get(user__username=receiver_username)
        except Account.DoesNotExist:
            messages.error(request, 'Destinataire introuvable.')
            return redirect('transfer_funds')

        sender = request.user.account
        if sender.balance < amount:
            messages.error(request, 'Solde insuffisant.')
            return redirect('transfer_funds')

        # Effectuer le transfert
        sender.balance -= amount
        receiver.balance += amount
        sender.save()
        receiver.save()

        # Enregistrer la transaction
        Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            description=description,
            status='completed'
        )

        # Envoyer un SMS à l'expéditeur
        try:
            sender_message = f"Vous avez transféré {amount} € à {receiver_username}."
            send_sms(sender.user.numero_telephone, sender_message)
        except Exception as e:
            messages.warning(request, f"Transfert réussi, mais échec de l'envoi du SMS à l'expéditeur : {str(e)}")

        # Envoyer un SMS au destinataire
        try:
            receiver_message = f"Vous avez reçu {amount} € de {sender.user.username}."
            send_sms(receiver.user.numero_telephone, receiver_message)
        except Exception as e:
            messages.warning(request, f"Transfert réussi, mais échec de l'envoi du SMS au destinataire : {str(e)}")

        messages.success(request, f'Transfert de {amount} € vers {receiver_username} réussi !')
        return redirect('dashboard')

    return render(request, 'transfer.html')




login_required
def dashboard(request):
    account = request.user.account
    recent_transactions = Transaction.objects.filter(
        Q(sender=account) | Q(receiver=account)
    ).order_by('-timestamp')[:5]  # Les 5 dernières transactions
    return render(request, 'dashboard.html', {
        'account': account,
        'recent_transactions': recent_transactions,
    })




@login_required
def transaction_history(request):
    account = request.user.account
    transactions = Transaction.objects.filter(
        Q(sender=account) | Q(receiver=account)
    ).order_by('-timestamp')
    return render(request, 'history.html', {
        'transactions': transactions,
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

    return render(request, 'add_beneficiary.html')

@login_required
def list_beneficiaries(request):
    beneficiaries = Beneficiary.objects.filter(user=request.user)
    return render(request, 'list_beneficiary.html', {
        'beneficiaries': beneficiaries,
    })







def transaction_statistics(request):
    # Données pour le diagramme linéaire (évolution des transactions par jour)
    daily_transactions = Transaction.objects.extra(
        select={'day': 'DATE(timestamp)'}
    ).values('day').annotate(total=Count('id')).order_by('day')

    # Données pour le diagramme en camembert (répartition des transactions par statut)
    status_distribution = Transaction.objects.values('status').annotate(total=Count('id'))

    context = {
        'daily_transactions': list(daily_transactions),
        'status_distribution': list(status_distribution),
    }
    return render(request, 'statistics.html', context)



def user_logout(request):
    logout(request)  # Déconnecte l'utilisateur
    return redirect('login')  # Redirige vers la page de connexion
