import os
import sys
from app import app

if __name__ == '__main__':
    # Set the project directory as current directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Ensure all required directories exist
    try:
        os.makedirs('instance')
    except OSError:
        pass
    
    # Run the Flask application
    app.run(debug=True, port=5000)
