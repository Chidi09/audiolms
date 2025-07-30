# setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='audiolms',
    version='0.1.0',
    author='Nneji Chidi Ben', # Updated with your name
    author_email='chidiisking7@gmail.com', # Updated with your email
    description='A Python plugin for managing audio in Learning Management Systems (LMS).',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/Chidi09/audiolms', # Updated with your GitHub username
    packages=find_packages(),
    install_requires=[
        'sounddevice>=0.4.6',       # For offline microphone recording (recorder.py) - conceptual for live demo
        'wavio>=0.0.4',             # For WAV file handling (recorder.py) - conceptual for live demo
        'Flask[async]>=2.0',        # Updated: For the main LMS web framework with async support
        'Flask-SocketIO>=5.0',      # For WebRTC signaling
        'python-engineio[asyncio]>=4.3.0', # Dependency for Flask-SocketIO
        'python-socketio[asyncio]>=5.4.0', # Dependency for Flask-SocketIO
        'aiortc>=1.0.0',            # For WebRTC core functionality
        'av>=8.0.0',                # Required by aiortc for media processing
        # 'boto3>=1.26.0',          # Uncomment if you specifically need S3 storage support
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Education',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Communications :: Chat', # New classifier for live audio
    ],
    python_requires='>=3.7',
)
