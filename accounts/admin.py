from django.contrib import admin
from .models import CustomUser, Banque, Account, Beneficiary, Transaction

# Enregistrement des modèles dans l'admin
admin.site.register(CustomUser)
admin.site.register(Banque)
admin.site.register(Account)
admin.site.register(Beneficiary)
admin.site.register(Transaction)