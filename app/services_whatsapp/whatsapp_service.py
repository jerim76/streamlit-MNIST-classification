from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask import current_app, request

from app.models import User, db # Assuming User model and db session are available
from app.utils import normalize_phone_number

def get_twilio_client():
    """Initializes and returns a Twilio client."""
    account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
    auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
    if not account_sid or not auth_token:
        current_app.logger.error("Twilio Account SID or Auth Token not configured.")
        return None
    return Client(account_sid, auth_token)

def send_whatsapp_message(to_phone: str, message_body: str):
    """
    Sends a WhatsApp message using Twilio.
    'to_phone' should be in the format 'whatsapp:+2547XXXXXXXX'.
    """
    client = get_twilio_client()
    from_whatsapp_number = current_app.config.get('TWILIO_WHATSAPP_NUMBER') # Twilio's sending number

    if not client or not from_whatsapp_number:
        current_app.logger.error("Twilio client or sender number not configured. Cannot send message.")
        return False

    try:
        # Ensure 'to_phone' starts with 'whatsapp:'
        if not to_phone.startswith('whatsapp:'):
            normalized_to_phone = normalize_phone_number(to_phone) # Returns +254...
            if not normalized_to_phone:
                current_app.logger.error(f"Invalid 'to_phone' number for WhatsApp: {to_phone}")
                return False
            to_whatsapp_number = f"whatsapp:{normalized_to_phone}"
        else:
            to_whatsapp_number = to_phone

        current_app.logger.info(f"Attempting to send WhatsApp message from {from_whatsapp_number} to {to_whatsapp_number}: {message_body}")

        message = client.messages.create(
            from_=from_whatsapp_number,
            body=message_body,
            to=to_whatsapp_number
        )
        current_app.logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending WhatsApp message to {to_phone}: {e}")
        return False

def handle_incoming_whatsapp_message(request_data: dict):
    """
    Processes an incoming WhatsApp message payload from Twilio.
    Returns a TwiML string response.
    """
    response = MessagingResponse()
    incoming_msg_body = request_data.get('Body', '').strip().lower()
    from_phone_raw = request_data.get('From', '') # Format: whatsapp:+2547XXXXXXXX

    # Extract the actual phone number part (+2547...) for user lookup
    if from_phone_raw.startswith('whatsapp:'):
        user_phone_normalized = normalize_phone_number(from_phone_raw.replace('whatsapp:', ''))
    else:
        user_phone_normalized = normalize_phone_number(from_phone_raw)


    current_app.logger.info(f"Incoming WhatsApp message from {from_phone_raw} (normalized: {user_phone_normalized}): '{incoming_msg_body}'")

    # User identification (basic)
    user = None
    if user_phone_normalized:
        user = User.query.filter_by(phone_number=user_phone_normalized).first()

    if user:
        reply_msg = f"Hello {user.full_name}! You said: '{incoming_msg_body}'. How can I help you today?"
        # TODO: Implement actual command parsing and actions
        # e.g., if incoming_msg_body == "status": get_booking_status(user)
    else:
        reply_msg = f"Hello! You said: '{incoming_msg_body}'. Your number {user_phone_normalized if user_phone_normalized else from_phone_raw} is not registered. Please register on our website."
        # TODO: Implement simplified WhatsApp registration later if desired.

    response.message(reply_msg)
    return str(response)

# Example of a more complex command handler (placeholder)
# def get_booking_status(user: User):
#     # Fetch user's active bookings and format a status message
#     active_bookings = Booking.query.filter_by(client_id=user.id, status=BookingStatus.CONFIRMED).all()
#     if not active_bookings:
#         return "You have no active bookings."
#     status_msg = "Your active bookings:\n"
#     for booking in active_bookings:
#         status_msg += f"- Service with {booking.freelancer.full_name} on {booking.booking_time.strftime('%Y-%m-%d %H:%M')}\n"
#     return status_msg

print("Created app/services_whatsapp/whatsapp_service.py")
