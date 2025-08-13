"""
Vercel WSGI entry point for MindSynth
"""
import sys
import os
from flask import Flask

# Add parent directory to path so we can import our app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from app import app
    # This is the WSGI callable that Vercel will use
    application = app
except Exception as e:
    # Fallback simple Flask app for debugging
    application = Flask(__name__)
    
    @application.route('/')
    def debug():
        return f"""<h1>Debug Info</h1>
        <p>Error importing main app: {e}</p>
        <p>Python path: {sys.path}</p>
        <p>Current directory: {os.getcwd()}</p>
        <p>Files in current directory: {os.listdir('.')}</p>
        """

if __name__ == "__main__":
    application.run()
