from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, LoginManager, UserMixin
import os
from datetime import datetime
from typing import Dict
from utils import login_required

try:
    from fpdf import FPDF
except ImportError:
    print("Installing required package: fpdf2")
    import pip
    pip.main(['install', 'fpdf2'])
    from fpdf import FPDF

# Import models
from models import db, User, UserPreference, AdventureLocation, Trip, Budget, PackingItem, UserInterest, EmergencyContact, FirstAidKit, FirstAidItem

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'adventure.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev'

    # Initialize SQLAlchemy
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app

app = create_app()

# Initialize database and insert default items
def init_db():
    with app.app_context():
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
        print("Database initialized successfully!")

def calculate_budget(adventure_type: str, location: str, duration: int, people: int) -> Dict:
    base_costs = {
        'camping': {'transport': 50, 'accommodation': 20, 'food': 30, 'gear': 100},
        'hiking': {'transport': 40, 'accommodation': 0, 'food': 25, 'gear': 80},
        'rock_climbing': {'transport': 60, 'accommodation': 40, 'food': 35, 'gear': 150},
        'kayaking': {'transport': 70, 'accommodation': 30, 'food': 35, 'gear': 120}
    }
    
    costs = base_costs.get(adventure_type, base_costs['camping'])
    total = sum(cost * duration * people for cost in costs.values())
    
    return {
        'transportation': costs['transport'] * people,
        'accommodation': costs['accommodation'] * duration * people,
        'food': costs['food'] * duration * people,
        'equipment': costs['gear'] * people,
        'total': total
    }

def generate_packing_list(adventure_type: str, duration: int, season: str) -> Dict:
    base_items = {
        'Clothing': [
            'Socks',
            'Underwear',
            'T-shirts',
            'Long-sleeve shirts',
            'Pants/Shorts',
            'Rain jacket'
        ],
        'Personal Care': [
            'Toothbrush',
            'Toothpaste',
            'Sunscreen',
            'First Aid Kit',
            'Hand Sanitizer',
            'Insect Repellent',
            'Personal Medications'
        ]
    }

    activity_specific = {
        'camping': ['Tent', 'Sleeping Bag', 'Camping Stove', 'Cooler'],
        'hiking': ['Hiking Boots', 'Backpack', 'Trekking Poles', 'Trail Map'],
        'rock_climbing': ['Climbing Shoes', 'Harness', 'Ropes', 'Chalk Bag'],
        'kayaking': ['Life Jacket', 'Dry Bags', 'Paddle', 'Spray Skirt']
    }

    checklist = base_items.copy()
    checklist['Activity Specific'] = activity_specific[adventure_type]
    
    if season in ['winter', 'fall']:
        checklist['Clothing'].extend(['Warm Jacket', 'Thermal Layers', 'Gloves'])

    return checklist

@app.route('/')
@login_required
def index():
    return render_template('base.html')

@app.route('/budget', methods=['GET', 'POST'])
def budget():
    if request.method == 'POST':
        try:
            # Handle the budget calculation
            estimated_budget = calculate_budget(
                request.form['adventure_type'],
                request.form['location'],
                int(request.form['duration']),
                int(request.form['people'])
            )
            
            # Save to database
            budget = Budget(
                transport=estimated_budget['transportation'],
                accommodation=estimated_budget['accommodation'],
                food=estimated_budget['food'],
                gear=estimated_budget['equipment'],
                total=estimated_budget['total']
            )
            db.session.add(budget)
            db.session.commit()
            
            return render_template('budget.html', estimated_budget=estimated_budget)
        except (ValueError, KeyError):
            pass
    return render_template('budget.html')

@app.route('/packing', methods=['GET', 'POST'])
def packing():
    if request.method == 'POST':
        checklist = generate_packing_list(
            request.form['adventure_type'],
            int(request.form['duration']),
            request.form['season']
        )
        return render_template('packing.html', checklist=checklist)
    return render_template('packing.html')

@app.route('/download_pdf')
def download_pdf():
    budget = db.session.query(Budget).order_by(Budget.id.desc()).first()
    
    if not budget:
        return "No budget data found."

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="Trip Budget Estimation", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)

    items = [
        ('Transport', budget.transport),
        ('Accommodation', budget.accommodation),
        ('Food', budget.food),
        ('Gear', budget.gear),
        ('Total', budget.total)
    ]

    for label, value in items:
        pdf.cell(200, 10, txt=f"{label}: ${value}", ln=True)

    filename = "budget_estimate.pdf"
    filepath = os.path.join(app.static_folder, filename)
    pdf.output(filepath)

    return send_file(filepath, as_attachment=True)

@app.route('/checklist_pdf')
def checklist_pdf():
    selected_type = 'Camping'  # default or fetch from session
    items = db.session.query(PackingItem).filter_by(adventure_type=selected_type).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt=f"Packing Checklist: {selected_type}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(10)

    for item in items:
        pdf.cell(200, 10, txt=f"- {item.name}", ln=True)

    filename = "packing_checklist.pdf"
    filepath = os.path.join(app.static_folder, filename)
    pdf.output(filepath)
    return send_file(filepath, as_attachment=True)

@app.route('/buddy-finder', methods=['GET'])
@login_required
def buddy_finder():
    # Get current user's interests
    user_interests = UserInterest.query.filter_by(user_id=session['user_id']).all()
    user_activities = [interest.activity_type for interest in user_interests]
    user_experience = user_interests[0].experience_level if user_interests else None
    current_user = User.query.get(session['user_id'])
    
    # Find matching buddies
    matching_buddies = []
    if user_interests:
        # Get all users except current user
        potential_buddies = User.query.filter(User.id != session['user_id']).all()
        
        for buddy in potential_buddies:
            buddy_interests = [interest.activity_type for interest in buddy.interests]
            # Check for common interests
            common_interests = set(user_activities) & set(buddy_interests)
            if common_interests:
                matching_buddies.append({
                    'id': buddy.id,
                    'username': buddy.username,
                    'interests': ', '.join(buddy_interests),
                    'experience_level': next((i.experience_level for i in buddy.interests if i.activity_type in common_interests), 'Not specified'),
                    'bio': buddy.bio or 'No bio available'
                })
    
    return render_template('buddy_finder.html',
                         matching_buddies=matching_buddies,
                         user_interests=user_activities,
                         user_experience=user_experience,
                         current_user=current_user)

@app.route('/update-interests', methods=['POST'])
@login_required
def update_interests():
    try:
        # Delete existing interests
        UserInterest.query.filter_by(user_id=session['user_id']).delete()
        
        # Get form data
        interests = request.form.getlist('interests')
        experience_level = request.form.get('experience_level')
        bio = request.form.get('bio')
        
        # Update user bio
        user = User.query.get(session['user_id'])
        user.bio = bio
        
        # Add new interests
        for activity in interests:
            interest = UserInterest(
                user_id=session['user_id'],
                activity_type=activity,
                experience_level=experience_level
            )
            db.session.add(interest)
        
        db.session.commit()
        flash('Profile updated successfully!')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating your profile.')
    
    return redirect(url_for('buddy_finder'))

@app.route('/send-buddy-request/<int:buddy_id>')
@login_required
def send_buddy_request(buddy_id):
    # Here you would implement the logic to send a connection request
    flash('Connection request sent!')
    return redirect(url_for('buddy_finder'))

# Safety Routes
@app.route('/safety')
@login_required
def safety_dashboard():
    emergency_contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    first_aid_kit = FirstAidKit.query.filter_by(user_id=current_user.id).first()
    
    if first_aid_kit:
        kit_items = first_aid_kit.items
    else:
        kit_items = []
    
    return render_template('safety.html',
                          emergency_contacts=emergency_contacts,
                          first_aid_kit=first_aid_kit,
                          kit_items=kit_items)

@app.route('/emergency-contacts', methods=['GET', 'POST'])
@login_required
def manage_emergency_contacts():
    if request.method == 'POST':
        new_contact = EmergencyContact(
            user_id=current_user.id,
            name=request.form['name'],
            relationship=request.form['relationship'],
            phone=request.form['phone'],
            email=request.form['email'],
            is_primary=bool(request.form.get('is_primary'))
        )
        
        if new_contact.is_primary:
            # Set all other contacts to non-primary
            EmergencyContact.query.filter_by(user_id=current_user.id).update({EmergencyContact.is_primary: False})
        
        db.session.add(new_contact)
        db.session.commit()
        flash('Emergency contact added successfully!')
        return redirect(url_for('safety_dashboard'))
    
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    return render_template('emergency_contacts.html', contacts=contacts)

@app.route('/first-aid-kit', methods=['GET', 'POST'])
@login_required
def manage_first_aid_kit():
    kit = FirstAidKit.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        if not kit:
            kit = FirstAidKit(user_id=current_user.id, last_checked=datetime.now())
            db.session.add(kit)
            db.session.commit()
        
        new_item = FirstAidItem(
            kit_id=kit.id,
            name=request.form['name'],
            quantity=int(request.form['quantity']),
            expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date() if request.form['expiry_date'] else None,
            status=request.form['status']
        )
        
        db.session.add(new_item)
        db.session.commit()
        flash('First aid item added successfully!')
        return redirect(url_for('manage_first_aid_kit'))
    
    items = FirstAidItem.query.filter_by(kit_id=kit.id).all() if kit else []
    return render_template('first_aid_kit.html', kit=kit, items=items)

@app.route('/sos-alert')
@login_required
def trigger_sos():
    # Get primary emergency contact
    primary_contact = EmergencyContact.query.filter_by(
        user_id=current_user.id,
        is_primary=True
    ).first()
    
    if primary_contact:
        # In a real application, you would implement actual emergency notification logic here
        flash(f'Emergency alert sent to {primary_contact.name} at {primary_contact.phone}')
    else:
        flash('No primary emergency contact found. Please add one in your safety settings.')
    
    return redirect(url_for('safety_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
