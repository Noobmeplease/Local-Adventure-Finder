from flask_login import login_required

def format_difficulty(value):
    if value == 1:
        return "Easy"
    elif value == 2:
        return "Moderate"
    elif value == 3:
        return "Hard"
    elif isinstance(value, str): # Handle if it's already a string
        return value.capitalize()
    return "Unknown" # Default or for other values

