from django.contrib import admin
from .models import Account, Transaction,CustomUser

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Account)
admin.site.register(Transaction)
