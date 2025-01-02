from django.shortcuts import render, redirect
from .models import Account, Transaction
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Compte créé pour {username} ! Vous pouvez maintenant vous connecter.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})



from django.contrib.auth.views import LoginView

class CustomLoginView(LoginView):
    template_name = 'login.html'


from django.contrib.auth.views import LogoutView

class CustomLogoutView(LogoutView):
    next_page = 'login'


@login_required
def transfer_funds(request):
    if request.method == "POST":
        receiver_username = request.POST.get("receiver")
        amount = request.POST.get("amount")

        # Vérifier la validité du montant
        try:
            amount = float(amount)
            if amount <= 0:
                return render(request, "transfer.html", {"error": "Le montant doit être supérieur à 0."})
        except (ValueError, TypeError):
            return render(request, "transfer.html", {"error": "Veuillez entrer un montant valide."})

        # Récupérer le destinataire
        try:
            receiver = Account.objects.get(user__username=receiver_username)
        except Account.DoesNotExist:
            return render(request, "transfer.html", {"error": "Destinataire introuvable."})

        sender = request.user.account

        # Vérifier si le solde est suffisant
        if sender.balance >= amount:
            sender.balance -= amount
            receiver.balance += amount

            # Sauvegarder les comptes
            sender.save()
            receiver.save()

            # Enregistrer la transaction
            Transaction.objects.create(sender=sender, receiver=receiver, amount=amount)

            return render(request, "transfer.html", {"success": "Transfert réussi."})
        else:
            return render(request, "transfer.html", {"error": "Solde insuffisant."})

    # Afficher la page de transfert pour les requêtes GET
    return render(request, "transfer.html")



@login_required
def transaction_history(request):
    account = request.user.account
    sent_transactions = account.sent_transactions.all()
    received_transactions = account.received_transactions.all()
    return render(request, "historique.html", {
        "sent_transactions": sent_transactions,
        "received_transactions": received_transactions,
    })
