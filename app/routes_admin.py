from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app, request
from flask_login import login_required, current_user

from . import db
from .models import User, UserRole, ServiceCategory # Add other models as needed for admin views
from .utils import roles_required
# from .forms import AdminCategoryForm # Example for later

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required # All admin routes require login
@roles_required(UserRole.ADMIN) # And require ADMIN role
def ensure_admin():
    # This function now just ensures the decorators are applied.
    # The roles_required decorator handles the actual role check.
    pass

@admin_bp.route('/')
def index():
    # Link to other admin pages from here
    return render_template('admin/admin_dashboard.html', title="Admin Dashboard")

@admin_bp.route('/freelancers')
def manage_freelancers():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 15)

    freelancers = User.query.filter_by(role=UserRole.FREELANCER)\
        .order_by(User.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin/manage_freelancers.html',
                           title="Manage Freelancers",
                           freelancers=freelancers)

@admin_bp.route('/freelancers/toggle_verification/<int:user_id>', methods=['POST'])
def toggle_freelancer_verification(user_id):
    freelancer = User.query.get_or_404(user_id)
    if freelancer.role != UserRole.FREELANCER:
        flash('This user is not a freelancer.', 'warning')
        return redirect(url_for('admin.manage_freelancers'))

    try:
        freelancer.is_verified_freelancer = not freelancer.is_verified_freelancer
        db.session.commit()
        status = "verified" if freelancer.is_verified_freelancer else "unverified"
        flash(f"Freelancer {freelancer.full_name} has been {status}.", 'success')
        # TODO: Notify freelancer about their status change
        # from app.services_whatsapp.whatsapp_service import send_whatsapp_message # Example
        # if freelancer.is_verified_freelancer:
        #     send_whatsapp_message(freelancer.phone_number, "Congratulations! Your freelancer profile has been verified.")
        # else:
        #     send_whatsapp_message(freelancer.phone_number, "Your freelancer profile verification has been revoked. Please contact support.")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating freelancer verification: {e}", 'error')
        current_app.logger.error(f"Error toggling verification for user {user_id}: {e}")

    return redirect(url_for('admin.manage_freelancers'))


# Placeholder for other admin functionalities like managing service categories
@admin_bp.route('/categories', methods=['GET', 'POST'])
def manage_categories():
    # form = AdminCategoryForm()
    # if form.validate_on_submit():
    #     # Process form to add/edit category
    #     pass
    categories = ServiceCategory.query.order_by(ServiceCategory.name).all()
    return render_template('admin/manage_categories.html', title="Manage Categories", categories=categories) #, form=form)

# Add more admin views as needed: view_users, view_services, view_bookings etc.
# These were referenced in dashboard.html for the admin user.
@admin_bp.route('/users')
def view_users():
    # Basic user listing, can be expanded
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/view_users.html', title="View All Users", users=users)

@admin_bp.route('/services')
def view_services():
    # Basic service listing
    services = [] # Replace with actual query: Service.query.all() or paginated
    flash("Service viewing not fully implemented yet.", "info")
    return render_template('admin/view_services.html', title="View All Services", services=services)

@admin_bp.route('/bookings')
def view_bookings():
    # Basic booking listing
    bookings = [] # Replace with actual query: Booking.query.all() or paginated
    flash("Booking viewing not fully implemented yet.", "info")
    return render_template('admin/view_bookings.html', title="View All Bookings", bookings=bookings)

# The route for verifying freelancers in dashboard.html was /admin.verify_freelancers
# Let's make manage_freelancers the one for that.
@admin_bp.route('/verify_freelancers')
def verify_freelancers_redirect():
    return redirect(url_for('admin.manage_freelancers'))


print("Created app/routes_admin.py with basic admin routes for freelancer verification.")
