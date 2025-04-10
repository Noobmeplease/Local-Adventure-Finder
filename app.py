from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from typing import Dict

try:
    from fpdf import FPDF
except ImportError:
    print("Installing required package: fpdf2")
    import pip
    pip.main(['install', 'fpdf2'])
    from fpdf import FPDF

app = Flask(__name__, instance_relative_config=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'adventure.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    trips = db.relationship('Trip', backref='user', lazy=True)
    preferences = db.relationship('UserPreference', backref='user', uselist=False)

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    preferred_categories = db.Column(db.Text)
    difficulty_level = db.Column(db.Integer)
    budget_range = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class AdventureLocation(db.Model):
    __tablename__ = 'adventure_locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    weather_info = db.Column(db.Text)
    average_rating = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Trip(db.Model):
    __tablename__ = 'trips'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('adventure_locations.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    budget_estimate = db.Column(db.Float)
    shared_publicly = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    transport = db.Column(db.Integer)
    accommodation = db.Column(db.Integer)
    food = db.Column(db.Integer)
    gear = db.Column(db.Integer)
    total = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PackingItem(db.Model):
    __tablename__ = 'packing_items'
    id = db.Column(db.Integer, primary_key=True)
    adventure_type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    is_default = db.Column(db.Boolean, default=True)

# Ensure instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Initialize database and insert default items
def init_db():
    with app.app_context():
        # Create static folder if it doesn't exist
        if not os.path.exists(app.static_folder):
            os.makedirs(app.static_folder)
        db.create_all()
        
        # Insert default packing items if none exist
        if PackingItem.query.count() == 0:
            default_items = {
                'camping': ['Tent', 'Sleeping Bag', 'Camping Stove', 'Cooler'],
                'hiking': ['Hiking Boots', 'Backpack', 'Trekking Poles', 'Trail Map'],
                'rock_climbing': ['Climbing Shoes', 'Harness', 'Ropes', 'Chalk Bag'],
                'kayaking': ['Life Jacket', 'Dry Bags', 'Paddle', 'Spray Skirt']
            }
            
            for adventure_type, items in default_items.items():
                for item_name in items:
                    item = PackingItem(
                        adventure_type=adventure_type,
                        name=item_name,
                        category='Activity Specific'
                    )
                    db.session.add(item)
            db.session.commit()

def calculate_budget(adventure_type: str, location: str, duration: int, people: int) -> Dict:
    base_costs = {
        'camping': {'transportation': 50, 'accommodation': 30, 'equipment': 100, 'food': 40},
        'hiking': {'transportation': 40, 'accommodation': 50, 'equipment': 80, 'food': 35},
        'rock_climbing': {'transportation': 60, 'accommodation': 60, 'equipment': 150, 'food': 40},
        'kayaking': {'transportation': 70, 'accommodation': 55, 'equipment': 120, 'food': 45}
    }

    costs = base_costs[adventure_type]
    budget = {
        'transportation': costs['transportation'] * people,
        'accommodation': costs['accommodation'] * duration * people,
        'equipment': costs['equipment'] * people,
        'food': costs['food'] * duration * people
    }
    budget['total'] = sum(budget.values())
    return budget

def generate_packing_list(adventure_type: str, duration: int, season: str) -> Dict:
    base_items = {
        'Essentials': [
            'First Aid Kit',
            'Water Bottle',
            'Flashlight/Headlamp',
            'Multi-tool',
            'Navigation Tools'
        ],
        'Clothing': [
            f'{duration * 2} pairs of socks',
            f'{duration} shirts',
            'Rain Jacket',
            'Hat'
        ],
        'Personal Items': [
            'Toiletries',
            'Sunscreen',
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
