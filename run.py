import os
import click
from app import create_app, db
from app.models import User, ServiceCategory, UserRole # Import necessary models

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.cli.command("seed-db")
def seed_db_command():
    """Seeds the database with initial data (e.g., Service Categories, Admin User)."""

    # Seed Service Categories
    categories_to_seed = [
        "Plumbing", "Electrical", "Cleaning", "Tutoring",
        "Carpentry", "Welding", "Masonry", "Painting",
        "Mechanics", "Catering", "Event Planning", "Photography",
        "Graphic Design", "Web Development", "Mobile Repair"
    ]
    existing_categories = {cat.name for cat in ServiceCategory.query.all()}

    for cat_name in categories_to_seed:
        if cat_name not in existing_categories:
            category = ServiceCategory(name=cat_name, description=f"Services related to {cat_name.lower()}.")
            db.session.add(category)
            print(f"Added category: {cat_name}")

    # Seed an Admin User (example)
    admin_phone = os.getenv('ADMIN_PHONE', '+254700000000') # Get from env or use default
    admin_pass = os.getenv('ADMIN_PASSWORD', 'AdminPass123')

    if not User.query.filter_by(phone_number=admin_phone).first():
        admin_user = User(
            full_name="Admin User",
            phone_number=admin_phone,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified_freelancer=True # Admins are auto-verified if they act as freelancers
        )
        admin_user.set_password(admin_pass)
        db.session.add(admin_user)
        print(f"Added admin user: {admin_phone}")

    try:
        db.session.commit()
        print("Database seeding complete.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during database seeding: {e}")

# Example: Old init-db command (can be kept or removed)
# @app.cli.command("init-db")
# def init_db_command():
#     """Clear existing data and create new tables."""
#     db.drop_all() # Careful with this in production
#     db.create_all()
#     print("Initialized the database (dropped and recreated tables).")

if __name__ == '__main__':
    app.run()
