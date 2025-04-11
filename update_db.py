from app import db
from models import User

def update_database():
    # Drop all tables
    db.drop_all()
    
    # Create tables with updated schema
    db.create_all()
    
    # Add default packing items
    default_items = {
        'camping': ['Tent', 'Sleeping Bag', 'Camping Stove', 'Cooler'],
        'hiking': ['Hiking Boots', 'Backpack', 'Trekking Poles', 'Trail Map'],
        'rock_climbing': ['Climbing Shoes', 'Harness', 'Ropes', 'Chalk Bag'],
        'kayaking': ['Life Jacket', 'Dry Bags', 'Paddle', 'Spray Skirt']
    }
    
    for activity, items in default_items.items():
        for item in items:
            packing_item = PackingItem(
                adventure_type=activity,
                name=item,
                is_default=True
            )
            db.session.add(packing_item)
    
    db.session.commit()
    print("Database updated successfully!")

if __name__ == '__main__':
    update_database()
