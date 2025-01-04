from django.shortcuts import render, redirect
from .models import Account, Transaction, CustomUser
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Account, Transaction
from django.db import models
from django.db.models import Q
from decimal import Decimal



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


def user_logout(request):
    logout(request)  # Déconnecte l'utilisateur
    return redirect('login')  # Redirige vers la page de connexion


@login_required
def dashboard(request):
    account = request.user.account
    recent_transactions = Transaction.objects.filter(
        models.Q(sender=account) | models.Q(receiver=account)
    ).order_by('-timestamp')[:5]  # Les 5 dernières transactions
    return render(request, 'dashboard.html', {
        'account': account,
        'recent_transactions': recent_transactions,
    })




from django.http import JsonResponse

@login_required
def transfer_funds(request):
    if request.method == 'POST':
        receiver_username = request.POST.get('receiver')
        amount = Decimal(request.POST.get('amount'))  # Convertir en Decimal
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
        sender.balance -= amount  # Maintenant, les deux sont des Decimal
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

        messages.success(request, f'Transfert de {amount} € vers {receiver_username} réussi !')
        return redirect('dashboard')

    return render(request, 'transfer.html')

@login_required
def transaction_history(request):
    account = request.user.account
    transactions = Transaction.objects.filter(
        models.Q(sender=account) | models.Q(receiver=account)
    ).order_by('-timestamp')
    return render(request, 'history.html', {
        'transactions': transactions,
    })