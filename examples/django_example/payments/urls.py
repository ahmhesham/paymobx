from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('pay/card/', views.pay_with_card, name='pay_with_card'),
    path('pay/wallet/', views.pay_with_wallet, name='pay_with_wallet'),
    path('callback/processed/', views.processed_callback, name='processed_callback'),
    path('callback/response/', views.payment_response, name='payment_response'),
]
