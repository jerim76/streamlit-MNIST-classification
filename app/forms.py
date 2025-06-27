from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, FloatField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError, Regexp
from .models import User, UserRole, ServiceCategory

# Phone number regex: Kenyan format (07xx..., 01xx...) or international (+2547xx..., +2541xx...)
PHONE_REGEX = r"^(?:\+254|0)?(7\d{8}|1\d{8})$"

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone_number = StringField('Phone Number', validators=[
        DataRequired(),
        Regexp(PHONE_REGEX, message="Invalid phone number format. Use 07xxxxxxxx, 01xxxxxxxx or +2547xxxxxxxx, +2541xxxxxxxx.")
    ])
    email = StringField('Email (Optional)', validators=[Optional(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=60)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Register as', choices=[(role.value, role.name.capitalize()) for role in UserRole if role != UserRole.ADMIN],
                       validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_phone_number(self, phone_number):
        # Normalize phone to +254 format for storage/uniqueness check if needed later
        # For now, just check existence
        user = User.query.filter_by(phone_number=phone_number.data).first()
        if user:
            raise ValidationError('That phone number is already registered. Please choose a different one or login.')

    def validate_email(self, email):
        if email.data: # Only validate if email is provided
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please choose a different one or login.')

class LoginForm(FlaskForm):
    phone_number = StringField('Phone Number', validators=[
        DataRequired(),
        Regexp(PHONE_REGEX, message="Invalid phone number format.")
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class EditProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email (Optional)', validators=[Optional(), Email(), Length(max=120)])
    current_password = PasswordField('Current Password', validators=[Optional(), Length(min=6)])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[Optional(), EqualTo('new_password', message='New passwords must match.')])
    submit = SubmitField('Update Profile')

    def __init__(self, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data and email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already taken by another user.')

class ServiceForm(FlaskForm):
    service_id = HiddenField("Service ID") # For editing existing service
    name = StringField('Service Name', validators=[DataRequired(), Length(min=3, max=150)])
    category = SelectField('Category', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10)])
    price_description = StringField('Price Description (e.g., per hour, fixed)', validators=[DataRequired(), Length(max=100)])
    estimated_price = FloatField('Estimated Price (KES, Optional)', validators=[Optional()])
    location_served = StringField('Location(s) Served', validators=[Optional(), Length(max=200)])
    availability_schedule = TextAreaField('Typical Availability (e.g., Mon-Fri 9am-5pm)', validators=[Optional()])
    is_active = BooleanField('Service is Active', default=True)
    submit = SubmitField('Save Service')

    def __init__(self, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)
        # Choices for 'category' SelectField are now set in the routes (e.g., main.manage_services)
        # This avoids issues with app context during form class definition or instantiation outside a request.
        # If choices were passed via kwargs (e.g. for testing), they could be handled here:
        # if 'category_choices' in kwargs:
        #     self.category.choices = kwargs.pop('category_choices')


class BookingForm(FlaskForm):
    # Assuming client is booking a specific service of a freelancer
    freelancer_id = HiddenField("Freelancer ID", validators=[DataRequired()])
    service_id = HiddenField("Service ID", validators=[DataRequired()])
    # Or allow booking general freelancer availability:
    # service_id = SelectField('Choose Service (Optional)', coerce=int, validators=[Optional()])

    booking_time_str = StringField('Preferred Date and Time (e.g., YYYY-MM-DD HH:MM)', validators=[DataRequired()])
    # In a real app, use a DateTimeLocalField and proper parsing/validation
    # For now, a string field that needs manual parsing in the route.

    location_address = TextAreaField('Service Address / Location Details', validators=[DataRequired(), Length(min=5, max=300)])
    client_notes = TextAreaField('Notes for Freelancer (Optional)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Request Booking')

class ReviewForm(FlaskForm):
    booking_id = HiddenField("Booking ID", validators=[DataRequired()])
    rating = SelectField('Rating', coerce=int, choices=[(i, str(i)) for i in range(1, 6)], validators=[DataRequired()])
    comment = TextAreaField('Comment (Optional)', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Review')


# TODO: Add forms for:
# - Admin actions (e.g., verify freelancer, manage categories)
# - Payment interaction (though M-Pesa might not be a direct form)
# - Search/Filter form for services/freelancers (can be simple GET params too)

print("Defined Flask-WTF forms in app/forms.py")
