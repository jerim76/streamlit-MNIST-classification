import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
# from flask_bcrypt import Bcrypt # Using werkzeug.security directly in models for now

from config import get_config_by_name

db = SQLAlchemy()
migrate = Migrate()
# bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # The route for login page
login_manager.login_message_category = 'info' # Flash message category for login_required

# Import models here to ensure they are known to SQLAlchemy and Flask-Migrate
# However, it's better to import them where they are used or in a specific models package.
# For now, models will be imported by Flask-Migrate via run.py or by blueprints.

def create_app(config_name: str = None):
    """
    Application factory function.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app_config = get_config_by_name(config_name)
    app.config.from_object(app_config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    # bcrypt.init_app(app)
    login_manager.init_app(app)

    # Configure ITEMS_PER_PAGE for pagination (example)
    app.config.setdefault('ITEMS_PER_PAGE', 10)


    # User loader function for Flask-Login
    # This import needs to be here to avoid circular dependencies with models.py
    from .models import User  # Ensure User model is imported
    @login_manager.user_loader
    def load_user(user_id):
        # user_id is typically a string, convert to int for DB query
        return User.query.get(int(user_id))

    # Register Blueprints
    from .routes_main import main_bp
    app.register_blueprint(main_bp)

    from .routes_auth import auth_bp
    app.register_blueprint(auth_bp) # url_prefix='/auth' is set in the blueprint itself

    # Placeholder for Admin Blueprint (to be created later)
    # from .routes_admin import admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')

    from .routes_payment import payment_bp
    app.register_blueprint(payment_bp) # url_prefix='/payments' is set in the blueprint

    from .routes_whatsapp import whatsapp_bp
    app.register_blueprint(whatsapp_bp) # url_prefix='/whatsapp' is set in the blueprint

    from .routes_admin import admin_bp
    app.register_blueprint(admin_bp) # url_prefix='/admin' is set in the blueprint

    # Placeholder for API Blueprint (to be created later)
    # from .api.routes import api_bp
    # app.register_blueprint(api_bp, url_prefix='/api/v1')


    # Shell context for Flask CLI
    # Import models for easy access in `flask shell`
    from .models import User, ServiceCategory, Service, Booking, Payment, Review, Notification, UserRole, BookingStatus, PaymentStatus
    @app.shell_context_processor
    def ctx():
        return {
            "app": app,
            "db": db,
            "User": User,
            "ServiceCategory": ServiceCategory,
            "Service": Service,
            "Booking": Booking,
            "Payment": Payment,
            "Review": Review,
            "Notification": Notification,
            "UserRole": UserRole,
            "BookingStatus": BookingStatus,
            "PaymentStatus": PaymentStatus
        }

    # Example health check route (can be removed or kept)
    @app.route('/health')
    def health_check():
        return "OK", 200

    return app
