"""
Vercel WSGI entry point for MindSynth
"""
import sys
import os

# Add parent directory to path so we can import our app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app

# This is the WSGI callable that Vercel will use
application = app

if __name__ == "__main__":
    app.run()
