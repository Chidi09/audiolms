audiolms
A Python plugin for managing audio in Learning Management Systems (LMS).

This project provides core functionalities for handling audio within an LMS environment, including:

Offline microphone recording (conceptual in this demo)

Storage management for audio files

Embedding audio playback

Live audio streaming using WebRTC with Flask-SocketIO

Installation
To install the audiolms package, navigate to the root directory of the project (where setup.py is located) and run:

pip install .

Usage
Running the Live Audio Demo
To run the live audio streaming demo, execute the following command from your terminal after installation:

python -m audiolms

Then, open http://127.0.0.1:5000 in your web browser. You can open multiple tabs to simulate a teacher and students joining a live session.

Project Structure
audiolms/
├── audiolms/
│   ├── __init__.py
│   ├── config.py
│   ├── recorder.py
│   ├── storage.py
│   ├── embedder.py
│   ├── models.py
│   ├── live/
│   │   ├── __init__.py
│   │   ├── signaling.py
│   │   ├── webrtc_manager.py
│   │   └── audio_track.py
│   └── __main__.py
└── setup.py
└── README.md

Contributing
Feel free to contribute to this project by opening issues or submitting pull requests.

License
This project is licensed under the MIT License.# audiolms
