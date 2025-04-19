from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from models import db, AdventureLocation, UserInterest, UserPreference, Trip, User
from sqlalchemy import func
from datetime import datetime

adventure_suggestions_bp = Blueprint('adventure_suggestions', __name__, url_prefix='/adventure')

def get_adventure_suggestions(user_id):
    # Get user's interests
    interests = UserInterest.query.filter_by(user_id=user_id).all()
    
    # Get user's preferences
    preferences = UserPreference.query.filter_by(user_id=user_id).first()
    
    # Get user's past trips
    past_trips = Trip.query.filter_by(user_id=user_id).all()
    
    # Get all locations
    query = AdventureLocation.query
    
    # Initialize scoring system
    locations = query.all()
    location_scores = {}
    
    # Score locations based on various factors
    for location in locations:
        score = 0
        
        # Interest matching
        if interests:
            for interest in interests:
                if interest.activity_type == location.category:
                    score += 2  # Base score for matching interest
                    
                    # Experience level matching
                    if interest.experience_level == 'beginner' and location.difficulty <= 2:
                        score += 2
                    elif interest.experience_level == 'intermediate' and 2 < location.difficulty <= 4:
                        score += 2
                    elif interest.experience_level == 'advanced' and location.difficulty > 4:
                        score += 2
        
        # Past trip matching
        if past_trips:
            for trip in past_trips:
                if trip.location_id == location.id:
                    score += 1  # Bonus for locations user has visited before
        
        # Preference matching
        if preferences:
            if preferences.difficulty_level:
                if location.difficulty <= preferences.difficulty_level:
                    score += 1
            
            if preferences.preferred_categories:
                categories = [cat.strip() for cat in preferences.preferred_categories.split(',')]
                if location.category in categories:
                    score += 1
        
        # Add base rating score
        score += location.average_rating * 2
        
        location_scores[location.id] = {
            'location': location,
            'score': score
        }
    
    # Sort locations by score
    sorted_locations = sorted(
        location_scores.values(),
        key=lambda x: x['score'],
        reverse=True
    )
    
    # Get top 10 suggestions
    top_suggestions = sorted_locations[:10]
    
    return [{
        'id': loc['location'].id,
        'name': loc['location'].name,
        'description': loc['location'].description,
        'category': loc['location'].category,
        'difficulty': loc['location'].difficulty,
        'average_rating': loc['location'].average_rating,
        'score': loc['score'],
        'latitude': loc['location'].latitude,
        'longitude': loc['location'].longitude,
        'weather_info': loc['location'].weather_info
    } for loc in top_suggestions]

@adventure_suggestions_bp.route('/suggestions', methods=['GET'])
def show_suggestions():
    return render_template('adventure_suggestions.html')

@adventure_suggestions_bp.route('/api/suggestions', methods=['GET'])
def api_get_suggestions():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    suggestions = get_adventure_suggestions(session['user_id'])
    
    # Add user's interests to response for display
    user = User.query.get(session['user_id'])
    interests = [{'activity': i.activity_type, 'level': i.experience_level} for i in user.interests]
    
    return jsonify({
        'suggestions': suggestions,
        'user_interests': interests
    })
