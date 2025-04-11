import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Change to the project directory
os.chdir(project_dir)

# Run the app
if __name__ == '__main__':
    from app import app
    with app.app_context():
        from app import init_db
        init_db()
    app.run(debug=True)
