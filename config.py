import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_default_secret_key')
    DEBUG = False
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 10 # Default number of items for pagination
    # JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_default_jwt_secret_key') # For JWT if we use it

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 'sqlite:///dev.db')
    # Example: SQLALCHEMY_DATABASE_URI = "postgresql://user:password@host:port/database"

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///test.db')
    WTF_CSRF_ENABLED = False # Disable CSRF forms in tests

class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///prod.db') # Should be PostgreSQL in reality
    # Ensure SECRET_KEY, JWT_SECRET_KEY, etc. are securely set from environment variables in production

# Dictionary to access config classes by name
config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig,
    default=DevelopmentConfig
)

def get_config_by_name(config_name: str):
    return config_by_name.get(config_name, DevelopmentConfig)

# Example of how to get JWT secret key if using Flask-JWT-Extended
# jwt_secret = get_config_by_name(os.getenv('FLASK_CONFIG') or 'default').JWT_SECRET_KEY

# M-Pesa Configuration
MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE')
MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY')
MPESA_TRANSACTION_TYPE = os.environ.get('MPESA_TRANSACTION_TYPE', 'CustomerPayBillOnline') # or "CustomerBuyGoodsOnline"
MPESA_CALLBACK_URL_BASE = os.environ.get('MPESA_CALLBACK_URL_BASE')
MPESA_API_ENVIRONMENT = os.environ.get('MPESA_API_ENVIRONMENT', 'sandbox')

# M-Pesa API Endpoints based on environment
if MPESA_API_ENVIRONMENT == 'live':
    MPESA_AUTH_URL = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    MPESA_STK_PUSH_URL = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    MPESA_TRANSACTION_STATUS_URL = 'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'
else: # Sandbox by default
    MPESA_AUTH_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    MPESA_STK_PUSH_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    MPESA_TRANSACTION_STATUS_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER') # The number Twilio uses to send (e.g., sandbox number)
FUNDIS_BOT_WHATSAPP_NUMBER = os.environ.get('FUNDIS_BOT_WHATSAPP_NUMBER') # Your app's dedicated WhatsApp number that users message
TEST_WHATSAPP_RECIPIENT = os.environ.get('TEST_WHATSAPP_RECIPIENT')
