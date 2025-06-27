from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from .forms import LoginForm, RegistrationForm, EditProfileForm
from .models import User, UserRole, db
from .utils import normalize_phone_number # We'll create this utility

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            phone = normalize_phone_number(form.phone_number.data)
            if not phone: # Should be caught by regex, but double check
                 flash('Invalid phone number format after normalization.', 'error')
                 return render_template('auth/register.html', title='Register', form=form)

            hashed_password = generate_password_hash(form.password.data)
            user_role = UserRole(form.role.data) # Convert string from form to Enum

            new_user = User(
                full_name=form.full_name.data,
                phone_number=phone, # Use normalized phone
                email=form.email.data if form.email.data else None,
                password_hash=hashed_password,
                role=user_role
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'error') # Log this error properly in production
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            phone = normalize_phone_number(form.phone_number.data)
            if not phone:
                flash('Invalid phone number format.', 'error')
                return render_template('auth/login.html', title='Login', form=form)

            user = User.query.filter_by(phone_number=phone).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.dashboard'))
            else:
                flash('Login Unsuccessful. Please check phone number and password', 'error')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error') # Log this error
    return render_template('auth/login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(original_email=current_user.email)
    if form.validate_on_submit():
        try:
            current_user.full_name = form.full_name.data
            if form.email.data and form.email.data != current_user.email:
                 # Validate_email in form should handle uniqueness, but check again or rely on db unique constraint
                current_user.email = form.email.data

            if form.current_password.data and form.new_password.data:
                if current_user.check_password(form.current_password.data):
                    current_user.set_password(form.new_password.data)
                    flash('Password updated successfully.', 'success')
                else:
                    flash('Incorrect current password. Password not updated.', 'error')
                    return render_template('auth/edit_profile.html', title='Edit Profile', form=form)

            db.session.commit()
            flash('Your profile has been updated.', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {e}', 'error') # Log error
    elif request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
    return render_template('auth/edit_profile.html', title='Edit Profile', form=form)

# Utility function to normalize phone numbers (e.g., to +254 format)
# This should ideally be in a separate utils.py
# For now, placing it here for brevity, will move later.
# Moved to app/utils.py

print("Created authentication routes (register, login, logout, edit_profile) in app/routes_auth.py")
