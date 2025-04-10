CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE adventure_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    difficulty INTEGER CHECK(difficulty BETWEEN 1 AND 5),
    latitude REAL,
    longitude REAL,
    weather_info TEXT,
    average_rating REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget_estimate REAL,
    shared_publicly BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (location_id) REFERENCES adventure_locations (id)
);

CREATE TABLE packing_checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    is_checked BOOLEAN DEFAULT FALSE,
    category TEXT NOT NULL,
    FOREIGN KEY (trip_id) REFERENCES trips (id)
);

CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    preferred_categories TEXT,
    difficulty_level INTEGER CHECK(difficulty_level BETWEEN 1 AND 5),
    budget_range TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE adventure_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    review_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (location_id) REFERENCES adventure_locations (id)
);

CREATE TABLE itinerary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id INTEGER NOT NULL,
    activity_name TEXT NOT NULL,
    start_time DATETIME,
    end_time DATETIME,
    notes TEXT,
    FOREIGN KEY (trip_id) REFERENCES trips (id)
);

CREATE TABLE travel_buddies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    available_from DATE,
    available_to DATE,
    preferred_location_ids TEXT,
    status TEXT CHECK(status IN ('open', 'connected', 'closed')),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE buddy_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_1_id INTEGER NOT NULL,
    user_2_id INTEGER NOT NULL,
    trip_id INTEGER,
    status TEXT CHECK(status IN ('pending', 'accepted', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_1_id) REFERENCES users (id),
    FOREIGN KEY (user_2_id) REFERENCES users (id),
    FOREIGN KEY (trip_id) REFERENCES trips (id)
);

CREATE TABLE social_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    trip_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    shared_link TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (trip_id) REFERENCES trips (id)
);

CREATE TABLE emergency_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    contact_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    type TEXT CHECK(type IN ('hospital', 'rescue', 'police')),
    FOREIGN KEY (location_id) REFERENCES adventure_locations (id)
);

CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_trips_user ON trips(user_id);
CREATE INDEX idx_trips_location ON trips(location_id);
CREATE INDEX idx_checklist_trip ON packing_checklist(trip_id);
CREATE INDEX idx_reviews_location ON adventure_reviews(location_id);
CREATE INDEX idx_reviews_user ON adventure_reviews(user_id);
