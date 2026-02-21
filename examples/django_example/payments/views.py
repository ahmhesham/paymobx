from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import sys
import os

from paymobx import PaymobxClient
from paymobx.integrations.django import is_valid_callback, is_valid_response

client = PaymobxClient(api_key=settings.PAYMOBX_API_KEY)

def index(request):
    return render(request, 'payments/index.html')

def pay_with_card(request):
    # 1. Create Order
    order = client.create_order(amount_cents=10000, currency="EGP")
    
    # 2. Get Payment Token
    billing_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+201012345678"
    }
    token = client.generate_payment_key(
        amount_cents=10000,
        order_id=order["id"],
        integration_id=settings.PAYMOBX_CARD_INTEGRATION_ID,
        billing_data=billing_data,
        currency="EGP"
    )
    
    # 3. Get Iframe URL
    iframe_url = client.get_iframe_url(iframe_id=settings.PAYMOBX_IFRAME_ID, payment_token=token)
    return redirect(iframe_url)

def pay_with_wallet(request):
    wallet_number = request.GET.get('wallet_number', '01010101010')
    
    # 1. Create Order
    order = client.create_order(amount_cents=10000, currency="EGP")
    
    # 2. Get Payment Token
    token = client.generate_payment_key(
        amount_cents=10000,
        order_id=order["id"],
        integration_id=settings.PAYMOBX_WALLET_INTEGRATION_ID,
        billing_data={"first_name": "Magka"},
        currency="EGP"
    )
    
    # 3. Get Redirection URL
    redirection_url = client.initiate_wallet_payment(payment_token=token, wallet_number=wallet_number)
    return redirect(redirection_url)

@csrf_exempt
def processed_callback(request):
    """Transaction Processed Webhook Handler"""
    if is_valid_callback(request, settings.PAYMOBX_HMAC):
        data = json.loads(request.body)
        is_success = data['obj']['success']
        order_id = data['obj']['order']['id']
        print(f"WEBHOOK: Payment status for order {order_id} is {is_success}")
        # Update your order status in DB here
        return HttpResponse(status=200)
    return HttpResponse(status=400)

def payment_response(request):
    """Transaction Response Redirect Handler"""
    if is_valid_response(request, settings.PAYMOBX_HMAC):
        success = request.GET.get('success') == 'true'
        return render(request, 'payments/status.html', {'success': success})
    return render(request, 'payments/status.html', {'error': 'Invalid verification'})
