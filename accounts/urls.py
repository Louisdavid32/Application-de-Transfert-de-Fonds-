# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('transfer/', views.transfer_funds, name='transfer_funds'),
    path('history/', views.transaction_history, name='transaction_history'),
    path('update_profile/', views.update_profile, name='update_profile'), 
    path('add_beneficiary/', views.add_beneficiary, name='add_beneficiary'),
    path('list_beneficiaries/', views.list_beneficiaries, name='list_beneficiaries'),
    path('statistics/', views.transaction_statistics, name='transaction_statistics'),
]


