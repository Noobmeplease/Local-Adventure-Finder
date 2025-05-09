from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user
import os
from datetime import datetime, time, timedelta
from typing import Dict
from utils import login_required # Updated import

try:
    from fpdf import FPDF
except ImportError:
    print("Installing required package: fpdf2")
    import pip
    pip.main(['install', 'fpdf2'])
    from fpdf import FPDF

# Import models
from models import db, User, UserPreference, AdventureLocation, Trip, Budget, PackingItem, UserInterest, UserSubmittedSpot, Notification, ItineraryItem, Review, UserEmergencyContact, UserMedicalReport, SuggestedEvent, UserAdventureDifficultyFeedback
from werkzeug.utils import secure_filename
from flask import send_from_directory
from sqlalchemy import func

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
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

    # Ensure upload folder exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Initialize SQLAlchemy
    db.init_app(app)

    # Register Jinja2 filters
    from utils import format_difficulty
    app.jinja_env.filters['format_difficulty'] = format_difficulty

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register blueprints
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from adventure_suggestions import adventure_suggestions_bp
    app.register_blueprint(adventure_suggestions_bp, url_prefix='/adventure-suggestions')

    # --- District Adventure & Difficulty Search Feature ---
    DISTRICT_ADVENTURE_DATA = {
        "chittagong": {
            "name": "Chittagong",
            "spots": ["Cox's Bazar", "Bandarban", "Saint Martin's Island", "Rangamati", "Khagrachari"],
            "difficulties": ["Language barrier (local dialects)", "Hotel syndication/price gouging during peak season", "Transportation to remote areas", "Navigating hilly terrains (Bandarban, Rangamati)", "Limited mobile network in some spots"]
        },
        "sylhet": {
            "name": "Sylhet",
            "spots": ["Jaflong", "Ratargul Swamp Forest", "Lalakhal", "Bisnakandi", "Sreemangal (Tea Gardens)"],
            "difficulties": ["Unpredictable weather (especially during monsoon)", "Bargaining with local transport (CNG, boats)", "Accommodation quality varies greatly", "Leeches during rainy season in forests", "Connectivity to some remote spots"]
        },
        "dhaka": {
            "name": "Dhaka Division (Around Dhaka City)",
            "spots": ["Sonargaon (Old Capital)", "Mainamati (Buddhist Ruins, Comilla)", "Baliati Palace (Manikganj)", "National Martyr's Monument (Savar)", "Bangabandhu Safari Park (Gazipur)"],
            "difficulties": ["Heavy traffic congestion (Dhaka city and highways)", "Air and noise pollution (Dhaka city)", "Finding reliable tourist information for lesser-known spots", "Crowds at popular attractions, especially on holidays", "Limited public transport to some outskirts locations"]
        }
        # Add more districts and their data here as needed
    }

    @app.route('/district_search', methods=['GET', 'POST'])
    @login_required
    def district_search():
        district_info = None
        available_districts = sorted([DISTRICT_ADVENTURE_DATA[key]['name'] for key in DISTRICT_ADVENTURE_DATA])

        if request.method == 'POST':
            district_name_query = request.form.get('district_name', '').strip().lower()
            # Find the internal key for the selected display name
            selected_district_key = None
            for key, value in DISTRICT_ADVENTURE_DATA.items():
                if value['name'].lower() == district_name_query:
                    selected_district_key = key
                    break

            if not district_name_query:
                flash('Please select a district name.', 'warning')
            elif selected_district_key and selected_district_key in DISTRICT_ADVENTURE_DATA:
                district_info = DISTRICT_ADVENTURE_DATA[selected_district_key]
            else:
                flash(f'No information found for "{request.form.get("district_name")}".', 'info')
        return render_template('district_difficulty_search.html', district_info=district_info, available_districts=available_districts)

    # Placeholder event data - in a real application, this would come from a database or an external API
    placeholder_events = [
        {
            "id": 1,
            "name": "Summer Music Festival",
            "date": "2025-07-20",
            "time": "14:00",
            "venue": "Central Park Bandshell",
            "location": "New York, NY",
            "description": "An outdoor music festival featuring local and international bands. All ages welcome!",
            "category": "Music",
            "image_url": "https://via.placeholder.com/300x200.png?text=Music+Festival",
            "url": "#"
        },
        {
            "id": 2,
            "name": "Community Art Fair",
            "date": "2025-08-05",
            "time": "10:00 - 18:00",
            "venue": "Town Square",
            "location": "Springfield, IL",
            "description": "Browse and buy art from local artists. Live demonstrations and food trucks.",
            "category": "Arts",
            "image_url": "https://via.placeholder.com/300x200.png?text=Art+Fair",
            "url": "#"
        },
        {
            "id": 3,
            "name": "Tech Workshop: Intro to Python",
            "date": "2025-07-28",
            "time": "18:00 - 20:00",
            "venue": "Downtown Library - Room A",
            "location": "San Francisco, CA",
            "description": "A beginner-friendly workshop on the basics of Python programming.",
            "category": "Workshops",
            "image_url": "https://via.placeholder.com/300x200.png?text=Tech+Workshop",
            "url": "#"
        },
        {
            "id": 4,
            "name": "Charity Fun Run",
            "date": "2025-09-10",
            "time": "09:00",
            "venue": "Riverside Path",
            "location": "Austin, TX",
            "description": "A 5K fun run to support local charities. Get active for a good cause!",
            "category": "Sports",
            "image_url": "https://via.placeholder.com/300x200.png?text=Fun+Run",
            "url": "#"
        }
    ]

    @app.route('/events/')
    def show_nearby_events():
        """Renders the main page for nearby events."""
        community_events = SuggestedEvent.query.order_by(SuggestedEvent.event_date, SuggestedEvent.event_time).all()
        return render_template('nearby_events.html', community_events=community_events)

    @app.route('/events/suggest', methods=['GET', 'POST'])
    @login_required
    def suggest_event():
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            location_text = request.form.get('location_text')
            event_date_str = request.form.get('event_date')
            event_time_str = request.form.get('event_time')
            category = request.form.get('category')

            if not name or not location_text or not event_date_str:
                flash('Event Name, Location, and Date are required.', 'danger')
                return render_template('suggest_event.html') # Re-render form with error

            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                if event_date < datetime.utcnow().date():
                    flash('Event date cannot be in the past.', 'danger')
                    return render_template('suggest_event.html', form_data=request.form)
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return render_template('suggest_event.html', form_data=request.form)

            event_time_obj = None
            if event_time_str:
                try:
                    event_time_obj = datetime.strptime(event_time_str, '%H:%M').time()
                except ValueError:
                    flash('Invalid time format. Please use HH:MM.', 'danger')
                    return render_template('suggest_event.html', form_data=request.form)
            
            new_event = SuggestedEvent(
                name=name,
                description=description,
                location_text=location_text,
                event_date=event_date,
                event_time=event_time_obj,
                category=category,
                user_id=current_user.id
            )
            db.session.add(new_event)
            try:
                db.session.commit()
                flash('Your event suggestion has been submitted!', 'success')
                return redirect(url_for('show_nearby_events')) # Updated url_for
            except Exception as e:
                db.session.rollback()
                flash(f'Error submitting event: {str(e)}', 'danger')
                print(f"Error submitting event: {e}")

        return render_template('suggest_event.html')

    @app.route('/events/api/filter_community_events')
    def api_filter_community_events():
        category_filter = request.args.get('category', type=str)
        date_filter_str = request.args.get('date', type=str)

        query = SuggestedEvent.query

        if category_filter:
            query = query.filter(SuggestedEvent.category.ilike(f'%{category_filter}%'))

        if date_filter_str:
            try:
                filter_date = datetime.strptime(date_filter_str, '%Y-%m-%d').date()
                query = query.filter(SuggestedEvent.event_date == filter_date)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
                
        query = query.order_by(SuggestedEvent.event_date, SuggestedEvent.event_time)
        filtered_community_events = query.all()

        events_list = []
        for event in filtered_community_events:
            events_list.append({
                'id': event.id,
                'name': event.name,
                'description': event.description,
                'location_text': event.location_text,
                'event_date': event.event_date.strftime('%Y-%m-%d') if event.event_date else None,
                'event_time': event.event_time.strftime('%H:%M') if event.event_time else None,
                'category': event.category,
                'suggester_username': event.suggester.username if event.suggester else 'Unknown'
            })
        return jsonify({"events": events_list})

    @app.route('/events/api/nearby')
    def api_get_nearby_events():
        """
        API endpoint to fetch nearby events.
        Filters events based on category and date query parameters.
        """
        category_filter = request.args.get('category', type=str)
        date_filter_str = request.args.get('date', type=str)

        # Use a different variable name for the list being filtered to avoid modifying the global placeholder_events
        current_filtered_events = list(placeholder_events) 

        if category_filter:
            current_filtered_events = [event for event in current_filtered_events if event.get('category', '').lower() == category_filter.lower()]

        if date_filter_str:
            try:
                # Assuming date_filter_str is in 'YYYY-MM-DD' format, matching event dates
                current_filtered_events = [event for event in current_filtered_events if event.get('date') == date_filter_str]
            except ValueError:
                # Silently ignore invalid date format for now, or could return an error
                pass 
                
        return jsonify({"events": current_filtered_events})

    # End of moved event routes

    @app.route('/safety-tips')
    @login_required
    def safety_tips_page():
        user_emergency_contacts = UserEmergencyContact.query.filter_by(user_id=current_user.id).order_by(UserEmergencyContact.created_at.desc()).all()
        user_medical_reports = UserMedicalReport.query.filter_by(user_id=current_user.id).order_by(UserMedicalReport.reported_at.desc()).all()
        return render_template('safety_tips.html', 
                               user_contacts=user_emergency_contacts,
                               user_medical_reports=user_medical_reports)

    @app.route('/add_user_emergency_contact', methods=['POST'])
    @login_required
    def add_user_emergency_contact():
        try:
            contact_name = request.form.get('contact_name')
            phone_number = request.form.get('phone_number')
            relationship = request.form.get('relationship')

            if not contact_name or not phone_number:
                flash('Contact name and phone number are required.', 'danger')
                return redirect(url_for('safety_tips_page'))

            new_contact = UserEmergencyContact(
                user_id=current_user.id,
                contact_name=contact_name,
                phone_number=phone_number,
                relationship=relationship
            )
            db.session.add(new_contact)
            db.session.commit()
            flash('Emergency contact added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding emergency contact. Please try again.', 'danger')
        return redirect(url_for('safety_tips_page'))

    @app.route('/delete_user_emergency_contact/<int:contact_id>', methods=['POST'])
    @login_required
    def delete_user_emergency_contact(contact_id):
        try:
            contact_to_delete = UserEmergencyContact.query.get_or_404(contact_id)
            if contact_to_delete.user_id != current_user.id:
                abort(403) # Forbidden
            db.session.delete(contact_to_delete)
            db.session.commit()
            flash('Emergency contact deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting emergency contact. Please try again.', 'danger')
        return redirect(url_for('safety_tips_page'))

    @app.route('/add_user_medical_report', methods=['POST'])
    @login_required
    def add_user_medical_report():
        try:
            condition_name = request.form.get('condition_name')
            notes = request.form.get('notes')
            if condition_name:
                new_report = UserMedicalReport(
                    user_id=current_user.id,
                    condition_name=condition_name,
                    notes=notes
                )
                db.session.add(new_report)
                db.session.commit()
                flash('Medical report added successfully!', 'success')
            else:
                flash('Failed to add medical report. Condition name is required.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medical report: {str(e)}', 'danger')
        return redirect(url_for('safety_tips_page'))

    @app.route('/delete_user_medical_report/<int:report_id>', methods=['POST'])
    @login_required
    def delete_user_medical_report(report_id):
        try:
            report_to_delete = UserMedicalReport.query.get_or_404(report_id)
            if report_to_delete.user_id != current_user.id:
                abort(403) # Forbidden
            db.session.delete(report_to_delete)
            db.session.commit()
            flash('Medical report deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting medical report: {str(e)}', 'danger')
        return redirect(url_for('safety_tips_page'))

    @app.route('/reviews', methods=['GET'])
    @login_required
    def reviews_page():
        reviews = Review.query.order_by(Review.created_at.desc()).all()
        return render_template('reviews.html', reviews=reviews, current_user=current_user)

    # Helper function to check allowed file extensions
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    @app.route('/submit_review', methods=['POST'])
    @login_required
    def submit_review():
        place_name = request.form.get('placeName')
        rating_str = request.form.get('rating')
        comment = request.form.get('comment')
        picture_file = request.files.get('picture')

        if not place_name or not rating_str:
            flash('Place name and rating are required.', 'danger')
            return redirect(url_for('reviews_page'))
        
        try:
            rating = int(rating_str)
            if not (1 <= rating <= 5):
                flash('Rating must be between 1 and 5.', 'danger')
                return redirect(url_for('reviews_page'))
        except ValueError:
            flash('Invalid rating value. Please enter a number between 1 and 5.', 'danger')
            return redirect(url_for('reviews_page'))

        picture_filename_to_save = None
        if picture_file and picture_file.filename != '':
            if allowed_file(picture_file.filename):
                picture_filename_to_save = secure_filename(picture_file.filename)
                try:
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_filename_to_save)
                    picture_file.save(upload_path)
                except Exception as e:
                    # Log e for server-side debugging
                    flash('An error occurred while saving the picture.', 'danger')
                    return redirect(url_for('reviews_page'))
            else:
                flash('Invalid image file type. Allowed types are: png, jpg, jpeg, gif.', 'danger')
                return redirect(url_for('reviews_page'))
        
        try:
            new_review = Review(
                place_name=place_name,
                rating=rating,
                comment=comment,
                picture_filename=picture_filename_to_save,
                user_id=current_user.id
            )
            db.session.add(new_review)
            db.session.commit()
            flash('Review submitted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            # Log e for server-side debugging
            flash('An error occurred while submitting your review. Please try again.', 'danger')
        
        return redirect(url_for('reviews_page'))


    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app


app = create_app()

def get_or_create_location(location_name, adventure_type):
    """Find existing location or create new one"""
    location = AdventureLocation.query.filter_by(name=location_name).first()
    if not location:
        location = AdventureLocation(
            name=location_name,
            category=adventure_type,
            description=f"{adventure_type} location at {location_name}",
            difficulty=2  # Default medium difficulty
        )
        db.session.add(location)
        db.session.commit()
    return location

@app.route('/trip/new', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            # Validate start date is not in the past
            if start_date < datetime.now().date():
                flash('Start date cannot be in the past', 'danger')
                return redirect(url_for('create_trip'))
            
            # Get selected duration from session
            selected_duration = session.get('selected_location', {}).get('duration')
            if selected_duration:
                # Calculate the date difference
                date_diff = (end_date - start_date).days + 1
                if date_diff != selected_duration:
                    flash(f'Trip duration must be {selected_duration} days as selected in budget estimation', 'danger')
                    return redirect(url_for('create_trip'))

            new_trip = Trip(
                user_id=current_user.id,
                location_id=request.form['location_id'],
                start_date=start_date,
                end_date=end_date,
                budget_estimate=float(request.form.get('budget', 0))
            )
            db.session.add(new_trip)
            db.session.commit()
            flash('Trip created successfully!', 'success')
            
            session.pop('estimated_budget', None)
            session.pop('selected_location', None)
            
            return redirect(url_for('view_itinerary', trip_id=new_trip.id))
        except Exception as e:
            db.session.rollback()
            flash('Error creating trip. Please try again.', 'danger')
            return redirect(url_for('view_trips'))
    
    budget_estimate = session.get('estimated_budget', None)
    selected_location = session.get('selected_location', None)
    
    locations = AdventureLocation.query.all()
    if selected_location:
        locations = sorted(locations, key=lambda x: x.id != selected_location['id'])
    
    # Get current date for min date attribute
    current_date = datetime.now().date().isoformat()
    
    # Calculate default end date based on selected duration
    default_end_date = None
    if selected_location and selected_location.get('duration'):
        default_end_date = (datetime.now().date() + timedelta(days=selected_location['duration'] - 1)).isoformat()
    
    return render_template('create_trip.html', 
                         locations=locations,
                         budget_estimate=budget_estimate,
                         selected_location=selected_location,
                         current_date=current_date,
                         default_end_date=default_end_date)

@app.route('/budget', methods=['GET', 'POST'])
def budget():
    if request.method == 'POST':
        try:
            adventure_type = request.form['adventure_type']
            location_name = request.form['location']
            duration = int(request.form['duration'])
            people = int(request.form['people'])

            # Get or create location in database
            location = get_or_create_location(location_name, adventure_type)
            
            # Calculate budget
            estimated_budget = calculate_budget(adventure_type, location_name, duration, people)
            
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
            
            # Store budget and location details in session
            session['estimated_budget'] = estimated_budget
            session['selected_location'] = {
                'id': location.id,
                'name': location_name,
                'adventure_type': adventure_type,
                'duration': duration,
                'people': people
            }
            
            return render_template('budget.html', 
                                estimated_budget=estimated_budget,
                                show_create_trip=True)
        except (ValueError, KeyError) as e:
            flash('Error calculating budget. Please check your inputs.', 'danger')
    return render_template('budget.html')

# Initialize database and insert default items
def init_db():
    with app.app_context():
        print("[DEBUG] Attempting to initialize database...")
        # Import all models here to ensure they are registered with SQLAlchemy before create_all()
        from models import User, UserPreference, AdventureLocation, Trip, Budget, PackingItem, UserInterest, UserSubmittedSpot, Notification, ItineraryItem, Review, UserEmergencyContact, UserMedicalReport
        
        try:
            db.create_all()  # Create sql tables for our data models
            print("[DEBUG] db.create_all() executed successfully.")
        except Exception as e:
            print(f"[DEBUG] Error during db.create_all(): {e}")
        
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
            print("Database already has default packing items. No changes made to packing items.")

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

def get_difficulty_levels_for_form():
    return [
        {'value': 1, 'name': 'Easy'},
        {'value': 2, 'name': 'Moderate'},
        {'value': 3, 'name': 'Hard'}
    ]

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
    return render_template('submit_spot.html') # Removed difficulty_levels

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

@app.route('/itinerary/<int:trip_id>', methods=['GET'])
@login_required
def view_itinerary(trip_id):
    trip = Trip.query.join(AdventureLocation).filter(Trip.id == trip_id).first_or_404()
    # Ensure user owns this trip
    if trip.user_id != current_user.id:
        abort(403)
    
    itinerary_items = ItineraryItem.query.filter_by(trip_id=trip_id).order_by(ItineraryItem.start_time).all()
    return render_template('itinerary.html', trip=trip, itinerary_items=itinerary_items)

@app.route('/itinerary/<int:trip_id>/add', methods=['GET', 'POST'])
@login_required
def add_itinerary_item(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        new_item = ItineraryItem(
            trip_id=trip_id,
            activity_name=request.form['activity_name'],
            start_time=datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M'),
            end_time=datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M'),
            notes=request.form.get('notes', '')
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Activity added to itinerary!', 'success')
        return redirect(url_for('view_itinerary', trip_id=trip_id))
    
    return render_template('add_itinerary_item.html', trip=trip)

@app.route('/itinerary/<int:trip_id>/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_itinerary_item(trip_id, item_id):
    item = ItineraryItem.query.get_or_404(item_id)
    trip = Trip.query.get_or_404(trip_id)
    
    if trip.user_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        item.activity_name = request.form['activity_name']
        item.start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        item.end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        item.notes = request.form.get('notes', '')
        db.session.commit()
        flash('Activity updated!', 'success')
        return redirect(url_for('view_itinerary', trip_id=trip_id))
    
    return render_template('edit_itinerary_item.html', trip=trip, item=item)

@app.route('/itinerary/<int:trip_id>/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_itinerary_item(trip_id, item_id):
    item = ItineraryItem.query.get_or_404(item_id)
    trip = Trip.query.get_or_404(trip_id)
    
    if trip.user_id != current_user.id:
        abort(403)
    
    db.session.delete(item)
    db.session.commit()
    flash('Activity deleted!', 'success')
    return redirect(url_for('view_itinerary', trip_id=trip_id))

@app.route('/trips')
@login_required
def view_trips():
    trips = Trip.query.filter_by(user_id=current_user.id).order_by(Trip.start_date).all()
    return render_template('trips.html', trips=trips)

@app.route('/export-itinerary/<int:trip_id>')
@login_required
def export_itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != current_user.id:
        abort(403)
    
    itinerary_items = ItineraryItem.query.filter_by(trip_id=trip_id).order_by(ItineraryItem.start_time).all()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt=f"Trip Itinerary - {trip.location.name}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"From: {trip.start_date.strftime('%Y-%m-%d')} To: {trip.end_date.strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(5)
    
    for item in itinerary_items:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=item.activity_name, ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"Time: {item.start_time.strftime('%H:%M')} - {item.end_time.strftime('%H:%M')}", ln=True)
        if item.notes:
            pdf.multi_cell(200, 10, txt=f"Notes: {item.notes}")
        pdf.ln(5)
    
    filename = f"itinerary_{trip_id}.pdf"
    filepath = os.path.join(app.static_folder, filename)
    pdf.output(filepath)
    
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
