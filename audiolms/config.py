# audiolms/config.py
import os

class Settings:
    """
    Configuration settings for the audiolms application.
    """
    # Base directory for uploads (conceptual for this live demo)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    # S3 bucket name (uncomment and configure if using S3)
    S3_BUCKET = 'your-audiolms-s3-bucket' # Replace with your actual S3 bucket name

    # Default STUN servers for WebRTC connectivity
    # These are public STUN servers that help peers discover each other's public IP addresses
    # and ports, facilitating connections across NATs.
    DEFAULT_STUN_SERVERS = [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"},
        {"urls": "stun:stun2.l.google.com:19302"},
        {"urls": "stun:stun3.l.google.com:19302"},
        {"urls": "stun:stun4.l.google.com:19302"},
    ]

# Create an instance of the settings to be imported by other modules
settings = Settings()

# Ensure the upload folder exists
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
