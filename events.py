from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import current_user, login_required
from datetime import datetime, time # Add time import
from models import db, SuggestedEvent # Import SuggestedEvent model and db
from sqlalchemy import func

# It's a good practice to have a separate blueprint for each major feature
events_bp = Blueprint('events_bp', __name__, url_prefix='/events')

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

@events_bp.route('/')
def show_nearby_events():
    """Renders the main page for nearby events."""
    community_events = SuggestedEvent.query.order_by(SuggestedEvent.event_date, SuggestedEvent.event_time).all()
    return render_template('nearby_events.html', community_events=community_events)


@events_bp.route('/suggest', methods=['GET', 'POST'])
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
                # Pass current form values back to template
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
            return redirect(url_for('events_bp.show_nearby_events'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting event: {str(e)}', 'danger')
            # Log the error e for debugging
            print(f"Error submitting event: {e}")

    return render_template('suggest_event.html')


@events_bp.route('/api/filter_community_events')
def api_filter_community_events():
    category_filter = request.args.get('category', type=str)
    date_filter_str = request.args.get('date', type=str)

    query = SuggestedEvent.query

    if category_filter:
        query = query.filter(SuggestedEvent.category.ilike(f'%{category_filter}%')) # Case-insensitive partial match

    if date_filter_str:
        try:
            filter_date = datetime.strptime(date_filter_str, '%Y-%m-%d').date()
            query = query.filter(SuggestedEvent.event_date == filter_date)
        except ValueError:
            # Invalid date format, perhaps return an error or ignore
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


@events_bp.route('/api/nearby')
def api_get_nearby_events():
    """
    API endpoint to fetch nearby events.
    Filters events based on category and date query parameters.
    """
    category_filter = request.args.get('category', type=str)
    date_filter_str = request.args.get('date', type=str)

    filtered_events = placeholder_events

    if category_filter:
        filtered_events = [event for event in filtered_events if event.get('category', '').lower() == category_filter.lower()]

    if date_filter_str:
        try:
            # Assuming date_filter_str is in 'YYYY-MM-DD' format, matching event dates
            filtered_events = [event for event in filtered_events if event.get('date') == date_filter_str]
        except ValueError:
            # Silently ignore invalid date format for now, or could return an error
            pass 
            
    return jsonify({"events": filtered_events})

# You might also want an endpoint for a specific event's details later:
# @events_bp.route('/<int:event_id>')
# def event_detail(event_id):
#     event = next((event for event in placeholder_events if event["id"] == event_id), None)
#     if event:
#         return render_template('event_detail.html', event=event) # You'd need to create event_detail.html
#     return "Event not found", 404
