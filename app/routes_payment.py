from flask import Blueprint, request, jsonify, flash, redirect, url_for, current_app, render_template
from flask_login import login_required, current_user

from .models import db, Booking, BookingStatus, Payment, PaymentStatus, UserRole
from .services_payment.mpesa_service import initiate_stk_push, process_mpesa_callback
from .utils import roles_required

payment_bp = Blueprint('payment', __name__, url_prefix='/payments')


@payment_bp.route('/initiate/booking/<int:booking_id>', methods=['POST', 'GET']) # GET for easy testing, POST for real
@login_required
@roles_required(UserRole.CLIENT) # Only clients can initiate payment for their bookings
def initiate_booking_payment(booking_id):
    booking = Booking.query.filter_by(id=booking_id, client_id=current_user.id).first_or_404()

    if booking.status != BookingStatus.CONFIRMED:
        flash('Payment can only be made for confirmed bookings.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Check if a payment record already exists and is pending or successful
    existing_payment = Payment.query.filter_by(booking_id=booking.id).first()
    if existing_payment and existing_payment.status == PaymentStatus.SUCCESSFUL:
        flash('This booking has already been paid for.', 'info')
        return redirect(url_for('main.dashboard'))

    if existing_payment and existing_payment.status == PaymentStatus.PENDING:
        # Could allow retrying STK push or just inform user
        flash('A payment for this booking is already pending. Please check your phone or try again after some time.', 'info')
        # Optionally, you might want to re-trigger STK if some time has passed and no callback received.
        # For now, simple redirect.
        return redirect(url_for('main.dashboard'))

    # Create a new payment record or use existing FAILED one to retry
    payment_to_process = existing_payment if existing_payment and existing_payment.status == PaymentStatus.FAILED else None

    if not payment_to_process:
        # For simplicity, let's assume service price is stored in service.estimated_price
        # A more robust system would have a clear 'final_price' on the booking itself.
        # For MVP, we'll use a placeholder amount or service's estimated price if available.
        amount_to_pay = booking.service.estimated_price if booking.service and booking.service.estimated_price else current_app.config.get('DEFAULT_BOOKING_PRICE', 100) # Default to 1 KES for testing if no price
        if amount_to_pay <=0: # Mpesa amount must be > 0
            amount_to_pay = 1

        payment_to_process = Payment(
            booking_id=booking.id,
            amount=amount_to_pay,
            currency="KES",
            status=PaymentStatus.PENDING
        )
        db.session.add(payment_to_process)
        try:
            db.session.commit() # Commit to get payment_to_process.id if it's new
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating payment record for booking {booking.id}: {e}")
            flash("Error preparing payment. Please try again.", "error")
            return redirect(url_for('main.dashboard'))
    else: # Retrying a previously FAILED payment
        payment_to_process.status = PaymentStatus.PENDING
        payment_to_process.mpesa_transaction_id = None # Clear old txn id
        payment_to_process.merchant_request_id = None
        payment_to_process.checkout_request_id = None
        payment_to_process.payment_confirmation_payload = None
        db.session.commit()


    stk_initiated = initiate_stk_push(booking, payment_to_process)

    if stk_initiated:
        flash('STK Push initiated. Please check your phone and enter your M-Pesa PIN to complete payment.', 'success')
    else:
        # error already logged in initiate_stk_push, payment status might be set to FAILED there
        flash('Failed to initiate M-Pesa STK Push. Please ensure your M-Pesa details are correct and try again.', 'error')

    return redirect(url_for('main.dashboard'))


@payment_bp.route('/mpesa_callback', methods=['POST'])
def mpesa_callback():
    """
    Safaricom M-Pesa STK Push Callback URL.
    This endpoint must be publicly accessible.
    """
    callback_data = request.json
    current_app.logger.info("M-Pesa Callback Received:")
    current_app.logger.info(json.dumps(callback_data, indent=2))

    # It's good practice to validate the source of the callback if possible,
    # e.g., by checking source IP if Safaricom provides a list, or using other security measures.

    success = process_mpesa_callback(callback_data)

    if success:
        # Safaricom expects a JSON response acknowledging receipt.
        # Using a generic success message. The actual content might vary based on Safaricom's docs for specific APIs.
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
    else:
        # Even if processing fails on our end, acknowledge receipt to Safaricom if the request format was valid.
        # The error is logged internally.
        # If the callback_data itself was malformed leading to an exception before processing,
        # Flask might return a 500.
        return jsonify({"ResultCode": 1, "ResultDesc": "Rejected"}), 200 # Or another appropriate code


# Example route to display payment status (for testing/debugging)
@payment_bp.route('/status/booking/<int:booking_id>')
@login_required # Or admin only
def payment_status_view(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not (current_user.id == booking.client_id or current_user.id == booking.freelancer_id or current_user.role == UserRole.ADMIN):
        abort(403)

    payment = Payment.query.filter_by(booking_id=booking.id).first()
    if not payment:
        flash("No payment record found for this booking.", "warning")
        return redirect(request.referrer or url_for('main.dashboard'))

    # This template needs to be created
    return render_template('payments/payment_status.html', booking=booking, payment=payment)

print("Created app/routes_payment.py with M-Pesa routes")
