import base64
import json
from datetime import datetime, timezone
import requests
from flask import current_app, url_for

from app.models import Payment, Booking, PaymentStatus, db
from app.utils import normalize_phone_number


def get_mpesa_access_token():
    """
    Fetches M-Pesa access token using Basic Auth with Consumer Key and Secret.
    Returns the access token string or None if an error occurs.
    """
    consumer_key = current_app.config.get('MPESA_CONSUMER_KEY')
    consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET')
    auth_url = current_app.config.get('MPESA_AUTH_URL')

    if not all([consumer_key, consumer_secret, auth_url]):
        current_app.logger.error("M-Pesa consumer key, secret, or auth URL not configured.")
        return None

    try:
        credentials = f"{consumer_key}:{consumer_secret}".encode('ascii')
        encoded_credentials = base64.b64encode(credentials).decode('utf-8')
        headers = {'Authorization': f'Basic {encoded_credentials}'}

        response = requests.get(auth_url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        token_data = response.json()
        access_token = token_data.get('access_token')
        # current_app.logger.info(f"M-Pesa Access Token obtained: {access_token[:20]}...") # Log partial token
        return access_token
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error obtaining M-Pesa access token: {e}")
        current_app.logger.error(f"Response content: {response.content if 'response' in locals() else 'N/A'}")
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_mpesa_access_token: {e}")
    return None


def initiate_stk_push(booking: Booking, payment_record: Payment):
    """
    Initiates an STK push request for a given booking and payment record.
    Updates payment_record with MerchantRequestID and CheckoutRequestID on successful initiation.
    Returns True if STK push initiated successfully, False otherwise.
    """
    access_token = get_mpesa_access_token()
    if not access_token:
        return False

    stk_push_url = current_app.config.get('MPESA_STK_PUSH_URL')
    shortcode = current_app.config.get('MPESA_SHORTCODE')
    passkey = current_app.config.get('MPESA_PASSKEY')
    callback_url_base = current_app.config.get('MPESA_CALLBACK_URL_BASE')

    if not all([stk_push_url, shortcode, passkey, callback_url_base]):
        current_app.logger.error("M-Pesa STK Push URL, shortcode, passkey, or callback base URL not configured.")
        return False

    # Ensure callback URL is fully formed
    # The route `payment_bp.mpesa_callback` will be registered with url_prefix `/payments`
    # so url_for('payment.mpesa_callback', _external=True) would be something like http://domain.com/payments/mpesa_callback
    # Safaricom might not like localhost, so this needs to be a publicly accessible URL (e.g. via ngrok for dev)
    # For now, constructing it manually assuming `MPESA_CALLBACK_URL_BASE` is the full base.
    # callback_url = f"{callback_url_base}{url_for('payment.mpesa_callback')}" # This might be better if base is just domain
    callback_url = url_for('payment.mpesa_callback', _external=True) # Flask's way
    # If MPESA_CALLBACK_URL_BASE is provided as a full override (e.g. ngrok URL for local dev):
    if callback_url_base and "ngrok" in callback_url_base: # Simple check for ngrok
        callback_url = f"{callback_url_base}/payments/mpesa_callback" # Assuming /payments prefix for blueprint

    current_app.logger.info(f"Using M-Pesa Callback URL: {callback_url}")


    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    password_str = f"{shortcode}{passkey}{timestamp}"
    password_bytes = password_str.encode('ascii')
    password = base64.b64encode(password_bytes).decode('utf-8')

    client_phone = normalize_phone_number(booking.client.phone_number)
    if not client_phone:
        current_app.logger.error(f"Invalid or non-normalizable phone number for client {booking.client_id}: {booking.client.phone_number}")
        return False

    # Safaricom expects phone number without the leading '+'
    safaricom_phone_format = client_phone.lstrip('+')


    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": current_app.config.get('MPESA_TRANSACTION_TYPE', "CustomerPayBillOnline"),
        "Amount": int(payment_record.amount), # M-Pesa expects integer amount
        "PartyA": safaricom_phone_format, # Customer's phone
        "PartyB": shortcode, # Business shortcode
        "PhoneNumber": safaricom_phone_format, # Customer's phone
        "CallBackURL": callback_url,
        "AccountReference": f"BOOK{booking.id}", # Unique identifier for the transaction
        "TransactionDesc": f"Payment for Booking #{booking.id} Service: {booking.service.name if booking.service else 'Custom'}"
    }
    current_app.logger.info(f"M-Pesa STK Push Payload: {json.dumps(payload, indent=2)}")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(stk_push_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        response_data = response.json()
        current_app.logger.info(f"M-Pesa STK Push Response: {response_data}")

        merchant_request_id = response_data.get('MerchantRequestID')
        checkout_request_id = response_data.get('CheckoutRequestID')
        response_code = response_data.get('ResponseCode')
        # response_description = response_data.get('ResponseDescription')
        # customer_message = response_data.get('CustomerMessage')

        if response_code == "0": # Success
            payment_record.merchant_request_id = merchant_request_id
            payment_record.checkout_request_id = checkout_request_id
            payment_record.payment_initiation_payload = json.dumps(payload) # Store what we sent
            db.session.commit()
            return True
        else:
            current_app.logger.error(f"STK Push initiation failed with ResponseCode {response_code}: {response_data.get('ResponseDescription')}")
            payment_record.status = PaymentStatus.FAILED # Mark as failed if initiation itself fails
            payment_record.payment_initiation_payload = json.dumps(payload)
            payment_record.payment_confirmation_payload = json.dumps(response_data) # Store error response
            db.session.commit()
            return False

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error initiating M-Pesa STK push for Booking {booking.id}: {e}")
        current_app.logger.error(f"Response content: {response.content if 'response' in locals() else 'N/A'}")
    except Exception as e:
        current_app.logger.error(f"Unexpected error in initiate_stk_push for Booking {booking.id}: {e}")

    return False


def process_mpesa_callback(callback_data: dict):
    """
    Processes the M-Pesa callback data.
    Updates Payment and Booking status accordingly.
    """
    current_app.logger.info(f"Processing M-Pesa callback: {json.dumps(callback_data, indent=2)}")

    try:
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = str(stk_callback.get('ResultCode')) # Ensure it's a string for comparison
        # result_desc = stk_callback.get('ResultDesc')

        payment = Payment.query.filter_by(checkout_request_id=checkout_request_id, merchant_request_id=merchant_request_id).first()

        if not payment:
            current_app.logger.error(f"M-Pesa callback received for unknown CheckoutRequestID: {checkout_request_id} or MerchantRequestID: {merchant_request_id}")
            return False # Or raise an error

        # Store the raw callback data
        payment.payment_confirmation_payload = json.dumps(callback_data)

        if result_code == "0": # Payment successful
            payment.status = PaymentStatus.SUCCESSFUL

            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    payment.mpesa_transaction_id = item.get('Value')
                # We can also capture Amount and PhoneNumber from callback if needed for verification,
                # though amount should match payment.amount.

            # Update booking status (optional, depends on flow)
            # booking = payment.booking
            # booking.status = BookingStatus.PAID_CONFIRMED # Or similar
            # db.session.add(booking)
            current_app.logger.info(f"Payment successful for Booking {payment.booking_id}, M-Pesa Receipt: {payment.mpesa_transaction_id}")
            # TODO: Notify client and freelancer of successful payment

        else: # Payment failed or cancelled
            payment.status = PaymentStatus.FAILED
            current_app.logger.warning(f"Payment failed for Booking {payment.booking_id}. ResultCode: {result_code}, Desc: {stk_callback.get('ResultDesc')}")
            # TODO: Notify client of payment failure

        db.session.add(payment)
        db.session.commit()
        return True

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing M-Pesa callback: {e}. Data: {json.dumps(callback_data)}")
        return False

print("Created app/services_payment/mpesa_service.py")
