from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUser(AbstractUser):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    ville = models.CharField(max_length=100)
    numero_telephone = models.CharField(max_length=15)
    emploi = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.prenom} {self.nom}"

class Account(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)  # Utilise CustomUser ici
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.balance} €"

@receiver(post_save, sender=CustomUser)  # Écoute CustomUser au lieu de User
def create_account_for_user(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)  # Écoute CustomUser au lieu de User
def save_account_for_user(sender, instance, **kwargs):
    instance.account.save()

class Transaction(models.Model):
    STATUS_CHOICES = [  
        ('pending', 'En attente'),
        ('completed', 'Complétée'),
        ('failed', 'Échouée'),
    ]

    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_transactions')
    receiver = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.user.username} -> {self.receiver.user.username} : {self.amount} €"