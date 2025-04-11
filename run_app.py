import os
import sys
import subprocess

# Get the full path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the project directory to Python path
sys.path.append(current_dir)

# Run the application
if __name__ == '__main__':
    # Change to the project directory
    os.chdir(current_dir)
    
    # Run the app using subprocess to ensure proper path handling
    subprocess.run([sys.executable, 'app.py'], check=True)
