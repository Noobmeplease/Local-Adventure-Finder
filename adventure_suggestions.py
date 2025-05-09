from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from models import db, AdventureLocation, UserInterest, UserPreference, Trip, User
from sqlalchemy import func
from datetime import datetime
from utils import format_difficulty # Import the filter function

adventure_suggestions_bp = Blueprint('adventure_suggestions', __name__, url_prefix='/adventure')

def get_adventure_suggestions(user_id):
    interests = UserInterest.query.filter_by(user_id=user_id).all()
    preferences = UserPreference.query.filter_by(user_id=user_id).first()
    past_trips = Trip.query.filter_by(user_id=user_id).all()
    query = AdventureLocation.query
    locations = query.all()
    location_scores = {}
    
    for location in locations:
        score = 0
        
        if interests:
            for interest in interests:
                if interest.activity_type == location.category:
                    score += 2
        
        if past_trips:
            for trip in past_trips:
                if trip.location_id == location.id:
                    score += 1
        
        if preferences:
            if preferences.preferred_categories:
                categories = [cat.strip() for cat in preferences.preferred_categories.split(',')]
                if location.category in categories:
                    score += 1
        
        location_scores[location.id] = {
            'location': location,
            'score': score
        }
    
    sorted_locations = sorted(
        location_scores.values(),
        key=lambda x: x['score'],
        reverse=True
    )
    
    top_suggestions = sorted_locations[:10]
    
    return [{
        'id': loc['location'].id,
        'name': loc['location'].name,
        'description': loc['location'].description,
        'category': loc['location'].category,
        'score': loc['score'],
        'latitude': loc['location'].latitude,
        'longitude': loc['location'].longitude,
        'weather_info': loc['location'].weather_info
    } for loc in top_suggestions]

@adventure_suggestions_bp.route('/suggestions', methods=['GET'])
def show_suggestions():
    query = AdventureLocation.query
    
    suggestions = query.all()
    
    processed_suggestions = [{
        'id': loc.id,
        'name': loc.name,
        'description': loc.description,
        'category': loc.category,
        'latitude': loc.latitude,
        'longitude': loc.longitude
    } for loc in suggestions]

    return render_template('adventure_suggestions.html', 
                           suggestions=processed_suggestions)

@adventure_suggestions_bp.route('/api/suggestions', methods=['GET'])
def api_get_suggestions():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    suggestions = get_adventure_suggestions(session['user_id'])
    user_prefs = UserPreference.query.filter_by(user_id=session['user_id']).first()
    user_difficulty_pref = user_prefs.difficulty_level if user_prefs and user_prefs.difficulty_level is not None else 0
    
    # Also, let's fetch user interests to display them as before
    user_interests_records = UserInterest.query.filter_by(user_id=session['user_id']).all()
    user_interests_data = [{'activity': interest.activity_type, 'level': interest.experience_level} for interest in user_interests_records]

    return jsonify({
        'suggestions': suggestions,
        'user_difficulty_preference': user_difficulty_pref,
        'user_interests': user_interests_data # Sending this back as it was used in the HTML
    })

@adventure_suggestions_bp.route('/location/<int:adventure_id>')
def adventure_detail(adventure_id):
    location = AdventureLocation.query.get_or_404(adventure_id)
    # Assuming you have a template named 'adventure_detail.html'
    return render_template('adventure_detail.html', location=location)

@adventure_suggestions_bp.route('/plan-trip')
def create_trip_from_suggestion():
    location_id = request.args.get('location_id', type=int)
    if not location_id:
        # Handle error: no location_id provided
        return "Error: Missing location_id", 400
    
    location = AdventureLocation.query.get_or_404(location_id)
    # For now, let's just show a placeholder or redirect to a general trip planning page
    # You might want to redirect to a page like url_for('trip_bp.plan_new_trip', location_id=location_id)
    # or render a template that pre-fills some trip details based on the location.
    # Example: return redirect(url_for('your_trip_planning_blueprint.create_trip', location_id=location_id))
    return f"Planning trip for: {location.name} (ID: {location_id}). Placeholder page."
