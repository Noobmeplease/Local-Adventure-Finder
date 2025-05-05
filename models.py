from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bio = db.Column(db.Text)
    
    trips = db.relationship('Trip', backref='user', lazy=True)
    preferences = db.relationship('UserPreference', backref='user', uselist=False)
    interests = db.relationship('UserInterest', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

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
    location = db.relationship('AdventureLocation', backref='trips', lazy=True)

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

class UserInterest(db.Model):
    __tablename__ = 'user_interests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # hiking, camping, biking, etc.
    experience_level = db.Column(db.String(20))  # beginner, intermediate, advanced
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_activity_types():
        return ['Hiking', 'Camping', 'Biking', 'Kayaking', 'Rock Climbing', 'Bird Watching']

    @staticmethod
    def get_experience_levels():
        return ['Beginner', 'Intermediate', 'Advanced']

class UserSubmittedSpot(db.Model):
    __tablename__ = 'user_submitted_spots'
    id = db.Column(db.Integer, primary_key=True)
    spot_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    contributor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    contributor_name = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    contributor = db.relationship('User', backref='submitted_spots')

# Add Notification model
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def mark_as_read(self):
        self.read = True
        db.session.commit()

class ItineraryItem(db.Model):
    __tablename__ = 'itinerary_items'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    activity_name = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    trip = db.relationship('Trip', backref=db.backref('itinerary_items', lazy=True))
