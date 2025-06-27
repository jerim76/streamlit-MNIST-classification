from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone

from . import db # or from .models import db
from .models import User, Service, ServiceCategory, Booking, Review, UserRole, BookingStatus, PaymentStatus
from .forms import ServiceForm, BookingForm, ReviewForm # Assuming these forms are defined
from .utils import normalize_phone_number, roles_required # We'll create roles_required decorator

main_bp = Blueprint('main', __name__)

@main_bp.app_context_processor
def inject_global_vars():
    """Inject global variables into all templates."""
    return {
        'UserRole': UserRole,
        'BookingStatus': BookingStatus,
        'PaymentStatus': PaymentStatus,
        'now': datetime.now(timezone.utc)
    }

@main_bp.route('/')
def index():
    # Potentially fetch some featured services or categories to display
    return render_template('index.html', title="Home")

@main_bp.route('/dashboard')
@login_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 5) # Define ITEMS_PER_PAGE in config

    client_bookings = None
    freelancer_bookings = None

    if current_user.role == UserRole.CLIENT:
        client_bookings = Booking.query.filter_by(client_id=current_user.id)\
            .order_by(Booking.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
    elif current_user.role == UserRole.FREELANCER:
        freelancer_bookings = Booking.query.filter_by(freelancer_id=current_user.id)\
            .order_by(Booking.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
    # Admin dashboard might show other stats, handled in a separate admin blueprint later

    return render_template('dashboard.html', title="Dashboard",
                           client_bookings=client_bookings,
                           freelancer_bookings=freelancer_bookings)

@main_bp.route('/services/manage', methods=['GET', 'POST'])
@login_required
@roles_required(UserRole.FREELANCER) # Custom decorator to restrict access
def manage_services():
    form = ServiceForm()
    # Dynamically populate category choices
    form.category.choices = [(c.id, c.name) for c in ServiceCategory.query.order_by('name').all()]

    if form.validate_on_submit():
        try:
            new_service = Service(
                freelancer_id=current_user.id,
                name=form.name.data,
                category_id=form.category.data,
                description=form.description.data,
                price_description=form.price_description.data,
                estimated_price=form.estimated_price.data,
                location_served=form.location_served.data,
                availability_schedule=form.availability_schedule.data,
                is_active=form.is_active.data
            )
            db.session.add(new_service)
            db.session.commit()
            flash('New service added successfully!', 'success')
            return redirect(url_for('main.manage_services'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding service: {e}', 'error')

    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 5)
    services = Service.query.filter_by(freelancer_id=current_user.id)\
                .order_by(Service.created_at.desc())\
                .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('services/manage_services.html', title="Manage Services", form=form, services=services)

@main_bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required(UserRole.FREELANCER)
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    if service.freelancer_id != current_user.id:
        abort(403) # Forbidden

    form = ServiceForm(obj=service) # Pre-populate form with service data
    form.category.choices = [(c.id, c.name) for c in ServiceCategory.query.order_by('name').all()]
    form.service_id.data = service.id # Ensure service_id is set for the form action

    if form.validate_on_submit():
        try:
            service.name = form.name.data
            service.category_id = form.category.data
            service.description = form.description.data
            service.price_description = form.price_description.data
            service.estimated_price = form.estimated_price.data
            service.location_served = form.location_served.data
            service.availability_schedule = form.availability_schedule.data
            service.is_active = form.is_active.data
            db.session.commit()
            flash('Service updated successfully!', 'success')
            return redirect(url_for('main.manage_services'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating service: {e}', 'error')

    # For GET request, ensure form is populated correctly if obj wasn't enough or for select fields
    form.name.data = service.name
    form.category.data = service.category_id
    form.description.data = service.description
    form.price_description.data = service.price_description
    form.estimated_price.data = service.estimated_price
    form.location_served.data = service.location_served
    form.availability_schedule.data = service.availability_schedule
    form.is_active.data = service.is_active

    return render_template('services/manage_services.html', title="Edit Service", form=form, service_id=service.id)


@main_bp.route('/services/<int:service_id>/toggle_activation', methods=['GET']) # Should be POST for safety
@login_required
@roles_required(UserRole.FREELANCER)
def toggle_service_activation(service_id):
    service = Service.query.get_or_404(service_id)
    if service.freelancer_id != current_user.id:
        abort(403)
    try:
        service.is_active = not service.is_active
        db.session.commit()
        status = "activated" if service.is_active else "deactivated"
        flash(f'Service "{service.name}" has been {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error toggling service activation: {e}', 'error')
    return redirect(url_for('main.manage_services'))

@main_bp.route('/search')
def search_results():
    query = request.args.get('service_type', '')
    location = request.args.get('location', '')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)

    # Basic search: by service name, category name, or freelancer name (if joined)
    # For MVP, search active services and their categories/freelancers.
    search_query = Service.query.join(User, Service.freelancer_id == User.id)\
                                .join(ServiceCategory, Service.category_id == ServiceCategory.id)\
                                .filter(Service.is_active == True, User.is_verified_freelancer == True) # Only show active services from verified freelancers

    if query:
        search_term = f"%{query}%"
        search_query = search_query.filter(
            db.or_(
                Service.name.ilike(search_term),
                Service.description.ilike(search_term),
                ServiceCategory.name.ilike(search_term),
                User.full_name.ilike(search_term) # Search by freelancer name
            )
        )

    if location:
        location_term = f"%{location}%"
        search_query = search_query.filter(Service.location_served.ilike(location_term))

    services_found = search_query.order_by(Service.name).paginate(page=page, per_page=per_page, error_out=False)

    # This template needs to be created
    return render_template('services/search_results.html',
                           title="Search Results",
                           services=services_found,
                           query=query,
                           location=location)


@main_bp.route('/freelancer/<int:freelancer_id>/profile')
def freelancer_profile(freelancer_id):
    freelancer = User.query.filter_by(id=freelancer_id, role=UserRole.FREELANCER, is_verified_freelancer=True).first_or_404()
    services = Service.query.filter_by(freelancer_id=freelancer.id, is_active=True).order_by(Service.name).all()
    reviews = Review.query.join(Booking, Review.booking_id == Booking.id)\
                          .filter(Booking.freelancer_id == freelancer.id)\
                          .order_by(Review.created_at.desc()).limit(10).all() # Show recent reviews
    # Calculate average rating
    avg_rating_query = db.session.query(db.func.avg(Review.rating))\
        .join(Booking, Review.booking_id == Booking.id)\
        .filter(Booking.freelancer_id == freelancer.id).scalar()
    average_rating = round(avg_rating_query, 1) if avg_rating_query else "No ratings yet"

    # This template needs to be created
    booking_form = None
    if current_user.is_authenticated and current_user.role == UserRole.CLIENT:
        booking_form = BookingForm() # For the modal

    return render_template('freelancer_profile.html',
                           title=f"{freelancer.full_name}'s Profile",
                           freelancer=freelancer,
                           services=services,
                           reviews=reviews,
                           average_rating=average_rating,
                           booking_form=booking_form)


# Placeholder for health check if needed by `app/__init__.py`'s example route
# @main_bp.route('/health')
# def health_check():
# return "OK from main_bp", 200


@main_bp.route('/booking/request', methods=['POST'])
@login_required
@roles_required(UserRole.CLIENT)
def request_booking():
    # form = BookingForm(request.form) # Old way
    form = BookingForm() # Instantiate the form

    # The freelancer_id and service_id are submitted as hidden fields by the modal's JS
    # We still need to validate them even if not explicitly part of BookingForm fields shown to user
    # Or, make them actual fields in BookingForm if preferred for WTForms validation flow.
    # For now, retrieve them from request.form directly as the JS sets them.

    freelancer_id_str = request.form.get('freelancer_id')
    service_id_str = request.form.get('service_id')

    if not freelancer_id_str or not service_id_str:
        flash('Freelancer ID or Service ID missing from request.', 'error')
        return redirect(request.referrer or url_for('main.index'))

    try:
        freelancer_id = int(freelancer_id_str)
        service_id = int(service_id_str)
    except ValueError:
        flash('Invalid Freelancer ID or Service ID.', 'error')
        return redirect(request.referrer or url_for('main.index'))


    if form.validate_on_submit(): # This will validate booking_time_str, location_address, client_notes
        freelancer = User.query.filter_by(id=freelancer_id, role=UserRole.FREELANCER, is_active=True, is_verified_freelancer=True).first()
        if not freelancer:
            flash('Selected freelancer is not available or invalid.', 'error')
            return redirect(request.referrer or url_for('main.index'))

        service = Service.query.filter_by(id=service_id, freelancer_id=freelancer.id, is_active=True).first()
        if not service:
            flash('Selected service is not available or invalid.', 'error')
            return redirect(url_for('main.freelancer_profile', freelancer_id=freelancer_id))

        try:
            booking_datetime_naive = datetime.strptime(form.booking_time_str.data, '%Y-%m-%d %H:%M')
            booking_datetime_utc = booking_datetime_naive.replace(tzinfo=timezone.utc)
            if booking_datetime_utc <= datetime.now(timezone.utc):
                flash('Booking time must be in the future.', 'error')
                # Ideally, re-render the profile page with the modal open and error message
                return redirect(url_for('main.freelancer_profile', freelancer_id=freelancer_id, service_id=service_id) + "#bookingModal")
        except ValueError:
            flash('Invalid date and time format. Please use YYYY-MM-DD HH:MM.', 'error')
            return redirect(url_for('main.freelancer_profile', freelancer_id=freelancer_id, service_id=service_id) + "#bookingModal")

        try:
            new_booking = Booking(
                client_id=current_user.id,
                freelancer_id=freelancer.id, # Use validated freelancer_id
                service_id=service.id,       # Use validated service_id
                booking_time=booking_datetime_utc,
                location_address=form.location_address.data,
                client_notes=form.client_notes.data,
                status=BookingStatus.PENDING
            )
            db.session.add(new_booking)
            db.session.commit()

            # TODO: Create actual notifications (in-app, email, SMS/WhatsApp later)
            # For now, just flash messages
            flash(f'Booking request sent to {freelancer.full_name} for {service.name}. You will be notified upon confirmation.', 'success')
            # Notify freelancer (placeholder)
            # create_notification(freelancer, f"New booking request from {current_user.full_name} for {service.name}")

            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating booking: {e}") # Log the error
        flash(f'An error occurred while sending your booking request: {e}', 'error')
        return redirect(url_for('main.freelancer_profile', freelancer_id=freelancer_id, service_id=service_id))


@main_bp.route('/booking/<int:booking_id>/confirm', methods=['GET']) # Should be POST
@login_required
@roles_required(UserRole.FREELANCER)
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.freelancer_id != current_user.id:
        abort(403)
    if booking.status != BookingStatus.PENDING:
        flash('This booking cannot be confirmed (it may already be confirmed or cancelled).', 'warning')
        return redirect(url_for('main.dashboard'))

    try:
        booking.status = BookingStatus.CONFIRMED
        booking.freelancer_notes = "Booking confirmed by freelancer." # Optional note
        db.session.commit()
        flash(f'Booking ID {booking.id} for {booking.service.name if booking.service else "custom service"} with {booking.client.full_name} has been confirmed.', 'success')
        # TODO: Notify client
        # create_notification(booking.client, f"Your booking for {booking.service.name} with {current_user.full_name} has been confirmed.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error confirming booking {booking_id}: {e}")
        flash(f'Error confirming booking: {e}', 'error')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/booking/<int:booking_id>/reject', methods=['GET']) # Should be POST
@login_required
@roles_required(UserRole.FREELANCER)
def reject_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.freelancer_id != current_user.id:
        abort(403)
    if booking.status != BookingStatus.PENDING:
        flash('This booking cannot be rejected (it may already be confirmed or cancelled).', 'warning')
        return redirect(url_for('main.dashboard'))

    try:
        booking.status = BookingStatus.CANCELLED_FREELANCER # Or a specific REJECTED status if defined
        booking.freelancer_notes = "Booking rejected by freelancer." # TODO: Allow reason input
        db.session.commit()
        flash(f'Booking ID {booking.id} for {booking.service.name if booking.service else "custom service"} with {booking.client.full_name} has been rejected.', 'info')
        # TODO: Notify client
        # create_notification(booking.client, f"Your booking for {booking.service.name} with {current_user.full_name} has been rejected.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting booking {booking_id}: {e}")
        flash(f'Error rejecting booking: {e}', 'error')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/booking/<int:booking_id>/cancel_client', methods=['GET']) # Should be POST
@login_required
@roles_required(UserRole.CLIENT)
def cancel_booking_client(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.client_id != current_user.id:
        abort(403)
    # Define conditions under which a client can cancel (e.g., only if PENDING or CONFIRMED but X hours before)
    if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
        flash('This booking cannot be cancelled by you at its current state.', 'warning')
        return redirect(url_for('main.dashboard'))

    try:
        booking.status = BookingStatus.CANCELLED_CLIENT
        # booking.client_notes = "Cancelled by client." # Optional
        db.session.commit()
        flash(f'Your booking ID {booking.id} for {booking.service.name if booking.service else "custom service"} has been cancelled.', 'success')
        # TODO: Notify freelancer
        # create_notification(booking.freelancer, f"Booking ID {booking.id} for {booking.service.name} was cancelled by the client {current_user.full_name}.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error client cancelling booking {booking_id}: {e}")
        flash(f'Error cancelling booking: {e}', 'error')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/booking/<int:booking_id>/mark_completed', methods=['GET']) # Should be POST
@login_required
@roles_required(UserRole.FREELANCER)
def mark_booking_completed(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.freelancer_id != current_user.id:
        abort(403)
    if booking.status != BookingStatus.CONFIRMED: # Only confirmed bookings can be marked completed by freelancer
        flash('This booking cannot be marked as completed (must be confirmed first).', 'warning')
        return redirect(url_for('main.dashboard'))

    try:
        booking.status = BookingStatus.COMPLETED
        # Or PAYMENT_PENDING if payment is expected after service completion via the platform
        # For M-Pesa, payment might happen before or upon confirmation.
        # Let's assume for now COMPLETED means service delivered, payment handled (or to be handled).
        db.session.commit()
        flash(f'Booking ID {booking.id} with {booking.client.full_name} marked as completed.', 'success')
        # TODO: Notify client, prompt for review if payment is also done.
        # create_notification(booking.client, f"Your service for booking {booking.id} with {current_user.full_name} is marked as completed.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking booking {booking_id} completed: {e}")
        flash(f'Error marking booking as completed: {e}', 'error')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/booking/<int:booking_id>/leave_review', methods=['GET', 'POST'])
@login_required
@roles_required(UserRole.CLIENT)
def leave_review(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.client_id != current_user.id:
        abort(403) # Not their booking
    if booking.status != BookingStatus.COMPLETED: # Or after payment confirmed
        flash('You can only review completed bookings.', 'warning')
        return redirect(url_for('main.dashboard'))

    existing_review = Review.query.filter_by(booking_id=booking.id, reviewer_id=current_user.id).first()
    if existing_review:
        flash('You have already reviewed this booking.', 'info')
        return redirect(url_for('main.dashboard'))

    form = ReviewForm(booking_id=booking.id)
    if form.validate_on_submit():
        try:
            new_review = Review(
                booking_id=booking.id,
                reviewer_id=current_user.id,
                freelancer_id=booking.freelancer_id,
                rating=form.rating.data,
                comment=form.comment.data
            )
            db.session.add(new_review)
            db.session.commit()
            flash('Thank you for your review!', 'success')
            # TODO: Notify freelancer about new review
            # create_notification(booking.freelancer, f"You received a new {form.rating.data}-star review from {current_user.full_name}.")
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting review for booking {booking_id}: {e}")
            flash(f'Error submitting review: {e}', 'error')

    # This template needs to be created
    return render_template('main/leave_review.html', title="Leave Review", form=form, booking=booking)


print("Created main application routes (index, dashboard, service management, search) in app/routes_main.py")
