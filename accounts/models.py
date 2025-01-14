
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator 
from django.core.exceptions import ValidationError

# Fonction de chiffrement MiROIR
def chiffrement_miroir(texte):
    return texte[::-1]  # Inverse la chaîne de caractères

# Fonction de chiffrement César 2
def chiffrement_cesar2(texte):
    resultat = ""
    for char in texte:
        if char.isalpha():  # Ne chiffre que les lettres
            decalage = 2
            if char.islower():
                resultat += chr(((ord(char) - ord('a') + decalage) % 26) + ord('a'))
            else:
                resultat += chr(((ord(char) - ord('A') + decalage) % 26) + ord('A'))
        else:
            resultat += char  # Laisse les autres caractères inchangés
    return resultat

# Fonction pour générer le numéro de compte
def generer_numero_compte(user):
    # Combine l'ID de l'utilisateur et son nom
    base = f"{user.id}{user.nom}"
    # Applique le chiffrement MiROIR
    miroir = chiffrement_miroir(base)
    # Applique le chiffrement César 2
    cesar2 = chiffrement_cesar2(miroir)
    return cesar2



# Modèle CustomUser
class CustomUser(AbstractUser):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    ville = models.CharField(max_length=100)
    numero_telephone = models.CharField(max_length=15)
    emploi = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True)
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

# Modèle Banque
class Banque(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    acronyme = models.CharField(max_length=10, unique=True)  # Exemple : UBA, CCA, Afrikland, etc.

    def __str__(self):
        return f"{self.acronyme} - {self.nom}"
    

# Modèle Account
class Account(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='accounts')  # Un utilisateur peut avoir plusieurs comptes
    banque = models.ForeignKey(Banque, on_delete=models.CASCADE, related_name='comptes')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    numero_compte = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.banque.acronyme} - {self.balance} €"
    

class Beneficiary(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='beneficiaries')
    beneficiary_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='beneficiary_of')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='beneficiary_accounts')

    class Meta:
        unique_together = ('user', 'beneficiary_user')  # Empêche les doublons

    def __str__(self):
        return f"{self.user.username} -> {self.beneficiary_user.username}"



class Transaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complétée'),
        ('failed', 'Échouée'),
    ]

    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_transactions')
    receiver = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    sender_currency = models.CharField(max_length=3, default='EUR')  # Devise de l'expéditeur
    receiver_currency = models.CharField(max_length=3, default='EUR')  # Devise du destinataire
    converted_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Montant converti
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.user.username} -> {self.receiver.user.username} : {self.amount} {self.sender_currency}"

    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("Vous ne pouvez pas vous envoyer de l'argent à vous-même.")
        if self.amount > self.sender.balance:
            raise ValidationError("Solde insuffisant pour effectuer cette transaction.")





# Signal pour créer un compte par défaut lors de la création d'un utilisateur
@receiver(post_save, sender=CustomUser)
def create_account_for_user(sender, instance, created, **kwargs):
    if created:
        # Crée une banque par défaut si elle n'existe pas
        banque_par_defaut, _ = Banque.objects.get_or_create(
            acronyme='UBA',
            defaults={'nom': 'Banque Par Défaut'}
        )
        # Crée un compte pour l'utilisateur
        Account.objects.create(user=instance, banque=banque_par_defaut)



# Signal pour générer le numéro de compte lors de la création d'un compte
@receiver(post_save, sender=Account)
def generer_numero_compte_auto(sender, instance, created, **kwargs):
    if created and not instance.numero_compte:
        # Génère le numéro de compte
        instance.numero_compte = generer_numero_compte(instance.user)
        instance.save()



# Signal pour sauvegarder le compte associé à l'utilisateur
@receiver(post_save, sender=CustomUser)
def save_account_for_user(sender, instance, **kwargs):
    if hasattr(instance, 'account'):  # Vérifie si l'utilisateur a un compte
        instance.account.save()  # Sauvegarde le compte associé


@receiver(post_save, sender=Transaction)
def update_balances(sender, instance, **kwargs):
    if instance.status == 'completed':
        sender_account = instance.sender
        receiver_account = instance.receiver

        sender_account.balance -= instance.amount
        receiver_account.balance += instance.amount

        sender_account.save()
        receiver_account.save()


















"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms import ValidationError

class CustomUser(AbstractUser):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    ville = models.CharField(max_length=100)
    numero_telephone = models.CharField(max_length=15)
    emploi = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True)

class Banque(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    acronyme = models.CharField(max_length=10, unique=True)  # Exemple : UBA, CCA, Afrikland, etc.

    def __str__(self):
        return f"{self.acronyme} - {self.nom}"
    

class Account(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='accounts')
    banque = models.ForeignKey(Banque, on_delete=models.CASCADE, related_name='comptes',default=1)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.banque.acronyme} - {self.balance} €"
    

class Beneficiary(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='beneficiaries')
    beneficiary_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='beneficiary_of', verbose_name='Bénéficiaire',default=1)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='beneficiary_accounts',default=1)

    def __str__(self):
        return f"{self.user.username} -> {self.beneficiary_user.username}"
    

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
    
    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("Vous ne pouvez pas vous envoyer de l'argent à vous-même.")




# Signaux pour créer un compte par défaut lors de la création d'un utilisateur
@receiver(post_save, sender=CustomUser)
def create_account_for_user(sender, instance, created, **kwargs):
    if created:
        # Crée un compte par défaut pour l'utilisateur
        banque_par_defaut = Banque.objects.get_or_create(acronyme='DEF', defaults={'nom': 'Banque Par Défaut'})[0]
        Account.objects.create(user=instance, banque=banque_par_defaut)

@receiver(post_save, sender=CustomUser)
def save_account_for_user(sender, instance, **kwargs):
    if hasattr(instance, 'account'):
        instance.account.save()"""






    
"""class CustomUser(AbstractUser):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    ville = models.CharField(max_length=100)
    numero_telephone = models.CharField(max_length=15)
    emploi = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True)  # Ajout du champ email

    def __str__(self):
        return f"{self.prenom} {self.nom}"

class Beneficiary(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='beneficiaries')
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} - {self.account_number}"

class Account(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)  # Utilise CustomUser ici
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.user.username} - {self.balance} €"

@receiver(post_save, sender=CustomUser)
def create_account_for_user(sender, instance, created, **kwargs):
    if created:
        Account.objects.create(user=instance)

class Transaction(models.Model):
    STATUS_CHOICES = [  
        ('pending', 'En attente'),
        ('completed', 'Complétée'),
        ('failed', 'Échouée'),
    ]

    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_transactions')
    receiver = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.user.username} -> {self.receiver.user.username} : {self.amount} €"

    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("Vous ne pouvez pas vous envoyer de l'argent à vous-même.")

    """