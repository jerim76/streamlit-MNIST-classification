"""
Database Models for the Fundis Booking Bot
"""
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as DBEnum, Text, Boolean, Float
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy_utils import ChoiceType # For cleaner Enum handling with SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin # For Flask-Login integration

from app import db # Import db object from __init__

# Using SQLAlchemy's recommended way for Base
Base = db.Model

class UserRole(PyEnum):
    CLIENT = "client"
    FREELANCER = "freelancer"
    ADMIN = "admin"

class BookingStatus(PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED_CLIENT = "cancelled_client"
    CANCELLED_FREELANCER = "cancelled_freelancer"
    COMPLETED = "completed"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_FAILED = "payment_failed"
    DISPUTED = "disputed"

class PaymentStatus(PyEnum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REFUNDED = "refunded"

class User(Base, UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=True) # Nullable if WhatsApp only user initially
    email = Column(String(120), unique=True, nullable=True, index=True)
    full_name = Column(String(100), nullable=False)
    role = Column(ChoiceType(UserRole, impl=DBEnum(UserRole, name="user_role_enum")), nullable=False, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified_freelancer = Column(Boolean, default=False, nullable=False) # Admin approved
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # For Flask-Login: get_id must return a string
    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # Relationships
    bookings_as_client = relationship("Booking", foreign_keys="[Booking.client_id]", back_populates="client", lazy="dynamic")
    bookings_as_freelancer = relationship("Booking", foreign_keys="[Booking.freelancer_id]", back_populates="freelancer", lazy="dynamic")
    services_offered = relationship("Service", back_populates="freelancer", lazy="dynamic")
    reviews_given = relationship("Review", foreign_keys="[Review.reviewer_id]", back_populates="reviewer", lazy="dynamic")
    reviews_received = relationship("Review", foreign_keys="[Review.freelancer_id]", back_populates="reviewed_freelancer", lazy="dynamic")
    notifications = relationship("Notification", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.full_name} ({self.phone_number})>"

class ServiceCategory(Base):
    __tablename__ = "service_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    services = relationship("Service", back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<ServiceCategory {self.name}>"

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    price_description = Column(String(100), nullable=False) # e.g., "per hour", "fixed"
    estimated_price = Column(Float, nullable=True)
    availability_schedule = Column(Text, nullable=True) # Could be JSON or simple text
    location_served = Column(String(200), nullable=True) # e.g., "Nairobi West"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    freelancer = relationship("User", back_populates="services_offered")
    category = relationship("ServiceCategory", back_populates="services")
    bookings = relationship("Booking", back_populates="service", lazy="dynamic")

    def __repr__(self):
        return f"<Service {self.name} by {self.freelancer.full_name if self.freelancer else 'N/A'}>"

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True) # Nullable if booking general availability
    service_details_custom = Column(Text, nullable=True) # For specific instructions or if service_id is null
    booking_time = Column(DateTime, nullable=False) # Proposed/confirmed time
    status = Column(ChoiceType(BookingStatus, impl=DBEnum(BookingStatus, name="booking_status_enum")), nullable=False, default=BookingStatus.PENDING, index=True)
    client_notes = Column(Text, nullable=True)
    freelancer_notes = Column(Text, nullable=True)
    location_address = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="bookings_as_client")
    freelancer = relationship("User", foreign_keys=[freelancer_id], back_populates="bookings_as_freelancer")
    service = relationship("Service", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False) # Assuming one payment per booking for now
    reviews = relationship("Review", back_populates="booking", lazy="dynamic")


    def __repr__(self):
        return f"<Booking {self.id} - Status: {self.status.value}>"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True, index=True) # One payment per booking
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="KES")
    mpesa_transaction_id = Column(String(50), nullable=True, unique=True, index=True) # M-Pesa's receipt number
    merchant_request_id = Column(String(100), nullable=True, index=True) # Safaricom's ID for the STK push request
    checkout_request_id = Column(String(100), nullable=True, index=True) # Safaricom's ID for the STK push request
    status = Column(ChoiceType(PaymentStatus, impl=DBEnum(PaymentStatus, name="payment_status_enum")), nullable=False, default=PaymentStatus.PENDING, index=True)
    payment_initiation_payload = Column(Text, nullable=True) # For M-Pesa request log
    payment_confirmation_payload = Column(Text, nullable=True) # For M-Pesa callback log
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    booking = relationship("Booking", back_populates="payment")

    def __repr__(self):
        return f"<Payment {self.id} for Booking {self.booking_id} - Status: {self.status.value}>"

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True) # One review per booking
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Client
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Freelancer
    rating = Column(Integer, nullable=False) # e.g., 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    booking = relationship("Booking", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    reviewed_freelancer = relationship("User", foreign_keys=[freelancer_id], back_populates="reviews_received")

    def __repr__(self):
        return f"<Review {self.id} - Rating: {self.rating} for Booking {self.booking_id}>"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) # Recipient
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    type = Column(String(50), nullable=True) # e.g., 'booking_confirmed', 'payment_received'
    related_booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", back_populates="notifications")
    related_booking = relationship("Booking") # Optional link for navigation

    def __repr__(self):
        return f"<Notification {self.id} for User {self.user_id} - Read: {self.is_read}>"

# To generate migrations:
# 1. (Done) Make sure FLASK_APP=run.py is set in your .env or shell
# 2. (Done) `source venv/bin/activate`
# 3. `flask db init` (only once per project, if migrations folder doesn't exist)
# 4. `flask db migrate -m "Initial database schema"`
# 5. `flask db upgrade`

# Note: Password hashing (set_password, check_password) added to User model.
# Flask-Login UserMixin added for session management.
# Using sqlalchemy_utils.ChoiceType for better Enum handling.
# Timestamps now use timezone.utc.
# Relationships are now defined with back_populates.
# `db.Model` is used as the Base for models.
# Ensured Flask-Login's get_id method returns a string.
# Added `app/__init__.py` import `db`
print("Updated app/models.py with SQLAlchemy specific model definitions.")
