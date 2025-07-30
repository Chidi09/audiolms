    # wsgi.py
    import os
    import sys

    # Add the project root to the Python path
    # This ensures that 'audiolms' can be imported correctly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'audiolms'))
    sys.path.insert(0, os.path.dirname(project_root))

    from audiolms.__main__ import app, socketio # Import the Flask app and SocketIO instance

    # This file is used by Gunicorn to find the application.
    # Gunicorn will automatically patch standard library modules for async compatibility
    # when using eventlet/gevent workers.
    