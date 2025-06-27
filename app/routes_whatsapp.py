from flask import Blueprint, request, current_app
from twilio.twiml.messaging_response import MessagingResponse

# Assuming whatsapp_service.py contains the message handling logic
from .services_whatsapp.whatsapp_service import handle_incoming_whatsapp_message, send_whatsapp_message

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/whatsapp')

@whatsapp_bp.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    """
    Webhook for receiving incoming WhatsApp messages from Twilio.
    """
    incoming_data = request.values # Twilio sends data as form-encoded
    current_app.logger.info(f"Twilio Webhook Data Received: {incoming_data}")

    # Process the message and get a TwiML response
    twiml_response_str = handle_incoming_whatsapp_message(incoming_data)

    # Send the TwiML response back to Twilio
    return twiml_response_str, 200, {'Content-Type': 'text/xml'}


# Example of an outbound message trigger (e.g., from an admin panel or system event)
# This is NOT directly part of the Twilio incoming webhook flow.
@whatsapp_bp.route('/send_test', methods=['GET']) # GET for easy testing
def send_test_whatsapp():
    # This is a simplified test route, in a real app, 'to_phone' and 'message' would be dynamic.
    # Ensure your .env has TEST_WHATSAPP_RECIPIENT set to a number that has joined your Twilio Sandbox
    test_recipient = current_app.config.get('TEST_WHATSAPP_RECIPIENT')
    if not test_recipient:
        return "TEST_WHATSAPP_RECIPIENT not set in .env", 400

    if not test_recipient.startswith("whatsapp:"):
         normalized_phone = normalize_phone_number(test_recipient)
         if not normalized_phone:
             return f"Invalid recipient phone: {test_recipient}", 400
         test_recipient_whatsapp = f"whatsapp:{normalized_phone}"
    else:
        test_recipient_whatsapp = test_recipient

    message_body = "Hello from the Fundis Booking Bot! This is a test message from a route."

    success = send_whatsapp_message(to_phone=test_recipient_whatsapp, message_body=message_body)

    if success:
        return f"Test message sent to {test_recipient_whatsapp}!", 200
    else:
        return f"Failed to send test message to {test_recipient_whatsapp}.", 500

# Need to import normalize_phone_number if used here, or ensure it's accessible
from .utils import normalize_phone_number

print("Created app/routes_whatsapp.py with webhook for Twilio.")
