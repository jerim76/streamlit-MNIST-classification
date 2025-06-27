import re
from functools import wraps
from flask import abort
from flask_login import current_user
from .models import UserRole

PHONE_REGEX_RAW = r"^(?:\+254|0)?(7\d{8}|1\d{8})$"
PHONE_REGEX_COMPILED = re.compile(PHONE_REGEX_RAW)

def normalize_phone_number(phone_number: str) -> str | None:
    """
    Normalizes a Kenyan phone number to +2547xxxxxxxx or +2541xxxxxxxx format.
    Returns None if the number is not in a recognized valid format.
    """
    if not phone_number:
        return None

    match = PHONE_REGEX_COMPILED.match(phone_number.strip())
    if match:
        # The capturing group (1) will contain '7xxxxxxxx' or '1xxxxxxxx'
        return f"+254{match.group(1)}"
    return None


def roles_required(*roles: UserRole):
    """
    Decorator to ensure a logged-in user has one of the specified roles.
    Example: @roles_required(UserRole.ADMIN, UserRole.FREELANCER)
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                # This should ideally redirect to login, but for API/decorator, abort is simpler.
                # Flask-Login's @login_required handles redirection better for views.
                abort(401) # Unauthorized

            # Ensure current_user.role is a UserRole enum instance
            user_role_enum = current_user.role
            if not isinstance(user_role_enum, UserRole):
                try:
                    # If it's stored as a string, try to convert it
                    user_role_enum = UserRole(str(user_role_enum))
                except ValueError:
                    # If conversion fails, it's an invalid role
                    abort(403) # Forbidden - role is not recognized

            if user_role_enum not in roles:
                abort(403) # Forbidden
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def generate_unique_code(length=8):
    """Generates a unique alphanumeric code."""
    import string
    import random
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Add other utility functions here as needed, e.g., for date formatting,
# M-Pesa specific helpers, notification sending, etc.

print("Created utility functions (normalize_phone_number, roles_required) in app/utils.py")
