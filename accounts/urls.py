from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),  # Tableau de bord
    path('transfer/', views.transfer_funds, name='transfer_funds'),  # Transfert d'argent
    path('history/', views.transaction_history, name='transaction_history'), # Historique des transactions
]