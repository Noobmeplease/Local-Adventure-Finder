from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user
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
from models import db, User, UserPreference, AdventureLocation, Trip, Budget, PackingItem, UserInterest, UserSubmittedSpot, Notification

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'adventure.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev'

    # Initialize SQLAlchemy
    db.init_app(app)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register blueprints
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # Register adventure suggestions blueprint
    from adventure_suggestions import adventure_suggestions_bp
    app.register_blueprint(adventure_suggestions_bp, url_prefix='/adventure')

    # Emergency Contacts Management
    @app.route('/emergency-contacts', methods=['GET', 'POST'])
    @login_required
    def manage_emergency_contacts():
        if request.method == 'POST':
            name = request.form.get('name')
            relationship = request.form.get('relationship')
            phone = request.form.get('phone')
            email = request.form.get('email')
            
            if not all([name, relationship, phone]):
                flash('All fields are required!', 'danger')
                return redirect(url_for('manage_emergency_contacts'))
            
            contact = EmergencyContact(
                user_id=current_user.id,
                name=name,
                relationship=relationship,
                phone=phone,
                email=email
            )
            db.session.add(contact)
            db.session.commit()
            flash('Emergency contact added successfully!', 'success')
            return redirect(url_for('manage_emergency_contacts'))
        
        contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
        return render_template('emergency_contacts.html', contacts=contacts)

    @app.route('/emergency-contacts/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_emergency_contact(id):
        contact = EmergencyContact.query.get_or_404(id)
        if contact.user_id != current_user.id:
            abort(403)
            
        if request.method == 'POST':
            contact.name = request.form.get('name')
            contact.relationship = request.form.get('relationship')
            contact.phone = request.form.get('phone')
            contact.email = request.form.get('email')
            
            db.session.commit()
            flash('Emergency contact updated successfully!', 'success')
            return redirect(url_for('manage_emergency_contacts'))
        
        return render_template('edit_emergency_contact.html', contact=contact)

    @app.route('/emergency-contacts/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_emergency_contact(id):
        contact = EmergencyContact.query.get_or_404(id)
        if contact.user_id != current_user.id:
            abort(403)
            
        db.session.delete(contact)
        db.session.commit()
        flash('Emergency contact deleted successfully!', 'success')
        return redirect(url_for('manage_emergency_contacts'))
    app.register_blueprint(adventure_suggestions_bp, url_prefix='/adventure')

    pass

    return app

app = create_app()

# Initialize database and insert default items
def init_db():
    with app.app_context():
        # Only create tables if they don't exist
        db.create_all()
        
        # Add default packing items only if they don't exist
        default_items = {
            'camping': ['Tent', 'Sleeping Bag', 'Camping Stove', 'Cooler'],
            'hiking': ['Hiking Boots', 'Backpack', 'Trekking Poles', 'Trail Map'],
            'rock_climbing': ['Climbing Shoes', 'Harness', 'Ropes', 'Chalk Bag'],
            'kayaking': ['Life Jacket', 'Dry Bags', 'Paddle', 'Spray Skirt']
        }
        
        # Check if any default packing items exist
        existing_items = PackingItem.query.filter_by(is_default=True).all()
        if not existing_items:
            for activity, items in default_items.items():
                for item in items:
                    packing_item = PackingItem(
                        adventure_type=activity,
                        name=item,
                        is_default=True
                    )
                    db.session.add(packing_item)
            db.session.commit()
            print("Default packing items added successfully!")
        else:
            print("Database already initialized. No changes made.")

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

def get_adventure_suggestions(user_id):
    user = User.query.get(user_id)
    if not user:
        return []
    
    preferences = user.preferences
    interests = user.interests
    
    # Get user's past trips
    past_trips = Trip.query.filter_by(user_id=user_id).all()
    
    # Get locations that match user's interests
    query = AdventureLocation.query
    
    # First filter by user interests
    if interests:
        # Get all unique activity types from user interests
        activity_types = set(interest.activity_type for interest in interests)
        
        # Create a base query that matches any of the user's interested activities
        base_query = AdventureLocation.category.in_(activity_types)
        
        # Add additional filters for each interest level
        for interest in interests:
            if interest.experience_level == 'beginner':
                base_query = base_query | (AdventureLocation.difficulty <= 2)
            elif interest.experience_level == 'intermediate':
                base_query = base_query | ((AdventureLocation.difficulty > 2) & (AdventureLocation.difficulty <= 4))
            elif interest.experience_level == 'advanced':
                base_query = base_query | (AdventureLocation.difficulty > 4)
        
        query = query.filter(base_query)
    
    # Add preference filters if they exist
    if preferences:
        # Filter by preferred categories if set
        if preferences.preferred_categories:
            categories = [cat.strip() for cat in preferences.preferred_categories.split(',')]
            query = query.filter(AdventureLocation.category.in_(categories))
        
        # Filter by difficulty level if set
        if preferences.difficulty_level:
            query = query.filter(AdventureLocation.difficulty <= preferences.difficulty_level)
    
    # Sort locations based on multiple criteria:
    # 1. Locations that match user's interests exactly (priority)
    # 2. Rating
    # 3. Difficulty level
    query = query.order_by(
        # Priority for exact interest matches
        AdventureLocation.category.in_(activity_types).desc(),
        AdventureLocation.average_rating.desc(),
        AdventureLocation.difficulty.asc()
    )
    
    # Get top 10 results
    locations = query.limit(10).all()
    
    # Convert to dictionary format with additional interest matching info
    suggestions = []
    for location in locations:
        # Check how well this location matches user interests
        interest_score = 0
        matching_interests = []
        
        for interest in interests:
            if interest.activity_type == location.category:
                interest_score += 1
                matching_interests.append(interest.activity_type)
                
                # Add bonus points based on experience level match
                if interest.experience_level == 'beginner' and location.difficulty <= 2:
                    interest_score += 1
                elif interest.experience_level == 'intermediate' and 2 < location.difficulty <= 4:
                    interest_score += 1
                elif interest.experience_level == 'advanced' and location.difficulty > 4:
                    interest_score += 1
        
        suggestions.append({
            'id': location.id,
            'name': location.name,
            'description': location.description,
            'category': location.category,
            'difficulty': location.difficulty,
            'average_rating': location.average_rating,
            'latitude': location.latitude,
            'longitude': location.longitude,
            'interest_score': interest_score,
            'matching_interests': matching_interests
        })
    
    # Sort suggestions by interest score first, then rating
    suggestions.sort(key=lambda x: (-x['interest_score'], -x['average_rating']))
    
    return suggestions

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
    user_interests = UserInterest.query.filter_by(user_id=current_user.id).all()
    user_activities = [interest.activity_type for interest in user_interests]
    user_experience = user_interests[0].experience_level if user_interests else None
    
    # Find matching buddies
    matching_buddies = []
    if user_interests:
        # Get all users except current user
        potential_buddies = User.query.filter(User.id != current_user.id).all()
        
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
        UserInterest.query.filter_by(user_id=current_user.id).delete()
        
        # Get form data
        interests = request.form.getlist('interests')
        experience_level = request.form.get('experience_level')
        bio = request.form.get('bio')
        
        # Update user bio
        current_user.bio = bio
        
        # Add new interests
        for activity in interests:
            interest = UserInterest(
                user_id=current_user.id,
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

# --- User Submitted Adventure Spots Feature ---
from flask import Markup, jsonify
from sqlalchemy import func

@app.route('/submit-spot', methods=['GET', 'POST'])
@login_required
def submit_spot():
    if request.method == 'POST':
        spot_name = request.form.get('spot_name')
        location = request.form.get('location')
        description = request.form.get('description')
        
        if spot_name and location:
            spot = UserSubmittedSpot(
                spot_name=spot_name,
                location=location,
                description=description,
                contributor_id=current_user.id,
                contributor_name=current_user.username
            )
            
            db.session.add(spot)
            db.session.commit()
            flash(Markup('Adventure spot submitted! <a href="' + url_for('user_spots') + '">View all spots</a>'))
            return redirect(url_for('submit_spot'))
        else:
            flash('Please provide both spot name and location.')
    return render_template('submit_spot.html')

@app.route('/user-spots')
def user_spots():
    # Get all spots with their contributors
    spots = UserSubmittedSpot.query.join(User, UserSubmittedSpot.contributor_id == User.id)\
        .order_by(UserSubmittedSpot.created_at.desc())\
        .all()
    return render_template('user_spots.html', spots=spots)

@app.route('/spot-request-form/<int:spot_id>')
@login_required
def spot_request_form(spot_id):
    spot = UserSubmittedSpot.query.get_or_404(spot_id)
    return render_template('spot_request.html', spot=spot)

@app.route('/send-spot-request/<int:spot_id>', methods=['POST'])
@login_required
def send_spot_request(spot_id):
    spot = UserSubmittedSpot.query.get_or_404(spot_id)
    email = request.form.get('email')
    
    if not email:
        flash('Please provide your email address.', 'danger')
        return redirect(url_for('spot_request_form', spot_id=spot_id))
    
    # Create notification for the spot submitter
    notification = Notification(
        user_id=spot.contributor_id,
        message=f'New spot request received from {current_user.username} ({email}) for your spot: {spot.spot_name}'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'Request sent to {spot.contributor.username} for spot: {spot.spot_name}. They will contact you at {email}.', 'success')
    return redirect(url_for('user_spots'))

@app.route('/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    notification.mark_as_read()
    return jsonify({'success': True})

@app.route('/notifications')
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/adventure-suggestions', methods=['GET'])
@login_required
def adventure_suggestions():
    suggestions = get_adventure_suggestions(session['user_id'])
    return render_template('adventure_suggestions.html', suggestions=suggestions)

@app.route('/api/suggestions', methods=['GET'])
@login_required
def get_suggestions_api():
    suggestions = get_adventure_suggestions(session['user_id'])
    return jsonify(suggestions)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
