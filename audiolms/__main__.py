# audiolms/__main__.py

# IMPORTANT: eventlet.monkey_patch() must be called as early as possible
# before other modules that might use standard library functions are imported.
import eventlet
eventlet.monkey_patch()

import asyncio
import logging
import os
from flask import Flask, render_template_string, request, Response, redirect, url_for
from flask_socketio import SocketIO, send, emit
from werkzeug.utils import secure_filename

# Import parts of the audiolms library
from .config import settings
# Temporarily comment out recorder and storage imports as they are causing issues
# and are not strictly necessary for the core WebRTC live demo.
# from .recorder import record_audio, upload_audio_file
# from .storage import save_audio_local, save_audio_s3
from .embedder import generate_embed_code # This might be conceptual for this demo
from .live.signaling import setup_live_signaling
from .live.webrtc_manager import WebRTCManager # Access the manager instance
from .live.audio_track import MicrophoneAudioTrack # Example usage if server generates audio

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Set default logging level for demo

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'a_very_secret_key_for_demo' # Replace in production!
socketio = SocketIO(app, cors_allowed_origins="*") # Allow all origins for demo
setup_live_signaling(socketio) # Hook up WebRTC signaling handlers

# HTML for a simple demo page
DEMO_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AudioLMS Live Demo</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; margin: 20px; background-color: #f4f4f4; display: flex; justify-content: center; align-items: flex-start; min-height: 100vh; }
        .container { background-color: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); max-width: 800px; width: 100%; margin: 20px; box-sizing: border-box; }
        h1, h2, h3 { color: #333; text-align: center; margin-bottom: 20px; }
        button {
            padding: 12px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin: 5px;
            transition: background-color 0.3s ease, transform 0.2s ease;
            font-size: 16px;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        button:hover { background-color: #0056b3; transform: translateY(-2px); }
        button:active { transform: translateY(0); box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type="file"], input[type="text"] {
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 8px;
            margin-bottom: 10px;
            width: calc(100% - 22px);
            box-sizing: border-box;
            font-size: 16px;
        }
        audio { width: 100%; margin-top: 15px; border-radius: 8px; }
        #messages { border: 1px solid #ddd; padding: 15px; height: 180px; overflow-y: scroll; margin-top: 20px; background-color: #e9ecef; border-radius: 8px; font-family: monospace; font-size: 14px; color: #555; }
        #messages p { margin: 5px 0; border-bottom: 1px dashed #ccc; padding-bottom: 5px; }
        #messages p:last-child { border-bottom: none; }
        #live-status { font-weight: bold; margin-top: 15px; text-align: center; color: #007bff; font-size: 1.1em; }
        .button-group { display: flex; justify-content: center; flex-wrap: wrap; margin-top: 15px; }
        .section { margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }
        .section:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        ul { list-style: none; padding: 0; }
        li { background-color: #f9f9f9; border: 1px solid #eee; margin-bottom: 10px; padding: 10px; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AudioLMS Live & Recording Demo</h1>

        <div class="section">
            <h2>Recorded Audio Files (Conceptual)</h2>
            <form method="POST" action="/upload_recorded" enctype="multipart/form-data">
                <p>Upload a recorded audio file:</p>
                <input type="file" name="audio_file" accept="audio/*">
                <button type="submit">Upload & Save</button>
            </form>
            <!-- Removed server-side recording button as it's conceptual and causes platform issues -->
            <div id="recorded-files">
                <h3>Uploaded & Recorded Audio:</h3>
                <ul>
                    {% for audio in recorded_audios %}
                    <li>
                        <strong>{{ audio.name }}</strong><br>
                        {{ audio.embed_code | safe }}
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>

        <div class="section">
            <h2>Live Audio Stream</h2>
            <p id="live-status">Live Session Status: Not Active</p>
            <div style="text-align: center; margin-bottom: 15px;">
                <input type="text" id="sessionIdInput" placeholder="Enter Session ID (e.g., 'class101')" style="width: 70%; max-width: 300px; display: inline-block;">
            </div>
            <div class="button-group">
                <button onclick="startLiveSession('teacher')">Start Live Session (Teacher)</button>
                <button onclick="joinLiveSession('student')">Join Live Session (Student)</button>
                <button onclick="stopLiveSession()">Stop All Live</button>
            </div>
            <div id="live-audio-player">
                <audio id="remoteAudio" autoplay controls></audio>
            </div>
        </div>

        <div class="section">
            <h3>Signaling Messages:</h3>
            <div id="messages"></div>
        </div>
    </div>

    <script type="text/javascript">
        var socket = io();
        var peerConnection = null; // Our RTCPeerConnection object
        var localStream = null; // Our local microphone stream
        var currentSessionId = null;
        var userRole = null; // 'teacher' or 'student'

        function logMessage(msg) {
            var messagesDiv = document.getElementById('messages');
            var p = document.createElement('p');
            p.textContent = new Date().toLocaleTimeString() + ': ' + msg;
            messagesDiv.appendChild(p);
            messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll
        }

        socket.on('connect', function() {
            logMessage('Connected to signaling server');
            document.getElementById('live-status').textContent = 'Live Session Status: Connected to Server';
        });

        socket.on('disconnect', function() {
            logMessage('Disconnected from signaling server');
            document.getElementById('live-status').textContent = 'Live Session Status: Disconnected';
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            const remoteAudio = document.getElementById('remoteAudio');
            remoteAudio.srcObject = null;
        });

        socket.on('error', function(data) {
            logMessage('Server Error: ' + data.message);
        });

        // WebRTC Signaling Handlers
        socket.on('offer', async function(data) {
            logMessage('Received offer from server (as student/listener)');
            if (!peerConnection) {
                logMessage('Creating new PeerConnection for incoming offer...');
                await createPeerConnection(); // Ensure PC exists
            }
            await peerConnection.setRemoteDescription(new RTCSessionDescription(data));
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            socket.emit('answer', {
                sdp: peerConnection.localDescription.sdp,
                type: peerConnection.localDescription.type
            });
            logMessage('Sent answer to server.');
        });

        socket.on('answer', async function(data) {
            logMessage('Received answer from server (as teacher/speaker)');
            if (peerConnection && peerConnection.currentLocalDescription) {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data));
                logMessage('Remote description (answer) set.');
            } else {
                logMessage('Warning: PeerConnection not ready for answer.');
            }
        });

        socket.on('ice_candidate', async function(data) {
            logMessage('Received ICE candidate from server');
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(new RTCIceCandidate(data));
                    logMessage('Added ICE candidate.');
                } catch (e) {
                    logMessage('Error adding ICE candidate: ' + e);
                }
            }
        });

        // Live Session Management
        socket.on('live_session_started', function(data) {
            logMessage(`Live session ${data.session_id} started successfully!`);
            document.getElementById('live-status').textContent = `Live Session Status: Active (Session ID: ${data.session_id}, Role: Teacher)`;
        });

        socket.on('live_session_joined', function(data) {
            logMessage(`Joined live session ${data.session_id}. Teacher SID: ${data.teacher_sid}`);
            document.getElementById('live-status').textContent = `Live Session Status: Listening (Session ID: ${data.session_id}, Role: Student)`;
        });


        async function createPeerConnection() {
            if (peerConnection) {
                logMessage('Existing PeerConnection found, closing before creating new.');
                peerConnection.close();
            }
            peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' } // Google's public STUN server
                ]
            });

            // Handle ICE candidates generated by our local peer
            peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    logMessage('Gathering ICE candidate.');
                    socket.emit('ice_candidate', {
                        candidate: event.candidate.candidate,
                        sdpMid: event.candidate.sdpMid,
                        sdpMLineIndex: event.candidate.sdpMLineIndex
                    });
                }
            };

            // Handle incoming remote tracks (e.g., teacher's audio for students)
            peerConnection.ontrack = (event) => {
                logMessage(`Received remote track: ${event.track.kind}`);
                if (event.track.kind === 'audio') {
                    const remoteAudio = document.getElementById('remoteAudio');
                    if (remoteAudio.srcObject !== event.streams[0]) {
                        remoteAudio.srcObject = event.streams[0];
                        logMessage('Remote audio stream attached to player.');
                    }
                }
            };

            // Log connection state changes for debugging
            peerConnection.onconnectionstatechange = () => {
                logMessage(`PeerConnection state changed: ${peerConnection.connectionState}`);
                if (peerConnection.connectionState === 'failed' || peerConnection.connectionState === 'disconnected') {
                    logMessage('PeerConnection failed or disconnected. Attempting to clean up.');
                    stopLiveSession();
                }
            };

            logMessage('New RTCPeerConnection created.');
        }

        async function startLiveSession(role) {
            userRole = role;
            currentSessionId = document.getElementById('sessionIdInput').value;
            if (!currentSessionId) {
                logMessage('Please enter a Session ID.');
                return;
            }
            logMessage(`Attempting to start live session as ${userRole} for session ID: ${currentSessionId}`);

            try {
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
                logMessage('Microphone access granted.');

                await createPeerConnection();
                localStream.getTracks().forEach(track => {
                    peerConnection.addTrack(track, localStream);
                    logMessage(`Added local ${track.kind} track to PeerConnection.`);
                });

                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                logMessage('Created and set local offer.');

                socket.emit('offer', {
                    sdp: peerConnection.localDescription.sdp,
                    type: peerConnection.localDescription.type
                });
                logMessage('Sent offer to signaling server.');

                socket.emit('start_live_session', { session_id: currentSessionId, role: userRole });

            } catch (e) {
                logMessage('Error starting live session: ' + e.message);
                console.error('Error starting live session:', e);
            }
        }

        async function joinLiveSession(role) {
            userRole = role;
            currentSessionId = document.getElementById('sessionIdInput').value;
            if (!currentSessionId) {
                logMessage('Please enter a Session ID.');
                return;
            }
            logMessage(`Attempting to join live session as ${userRole} for session ID: ${currentSessionId}`);

            try {
                await createPeerConnection();
                // For a student joining, we create an offer to signal we are ready to receive audio.
                // The server will then add the teacher's track to our PC.
                const offer = await peerConnection.createOffer({
                    offerToReceiveAudio: true,
                    offerToReceiveVideo: false // Ensure only audio is requested
                });
                await peerConnection.setLocalDescription(offer);
                logMessage('Created and set local offer for joining.');

                socket.emit('offer', {
                    sdp: peerConnection.localDescription.sdp,
                    type: peerConnection.localDescription.type
                });
                logMessage('Sent offer to signaling server to join.');

                socket.emit('join_live_session', { session_id: currentSessionId, role: userRole });

            } catch (e) {
                logMessage('Error joining live session: ' + e.message);
                console.error('Error joining live session:', e);
            }
        }

        function stopLiveSession() {
            logMessage('Stopping live session and cleaning up.');
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            const remoteAudio = document.getElementById('remoteAudio');
            remoteAudio.srcObject = null;
            document.getElementById('live-status').textContent = 'Live Session Status: Inactive';
            currentSessionId = null;
            userRole = null;
            logMessage('Clean up complete.');
            // Optionally, emit a 'leave_session' event to the server
            // socket.emit('leave_session', { session_id: currentSessionId });
        }

        function recordServerAudio() {
            logMessage('Server-side recording not implemented in this browser demo. This button is conceptual for server-side mic capture.');
            // In a real scenario, this would trigger a Flask route that uses sounddevice on the server.
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    # For this demo, recorded_audios will be an empty list as we focus on live.
    # In a full LMS, this would fetch actual recorded files.
    recorded_audios = []
    return render_template_string(DEMO_HTML, recorded_audios=recorded_audios)

@app.route('/upload_recorded', methods=['POST'])
async def upload_recorded():
    # This is a placeholder for actual file upload handling.
    # For a full implementation, you'd save the file and process it.
    if 'audio_file' not in request.files:
        return "No audio file part", 400
    file = request.files['audio_file']
    if file.filename == '':
        return "No selected file", 400
    if file:
        filename = secure_filename(file.filename)
        # Simulate saving the file
        # save_path = os.path.join(settings.UPLOAD_FOLDER, filename)
        # file.save(save_path)
        logger.info(f"Simulated upload of {filename}")
        return redirect(url_for('index'))
    return "Upload failed", 500

def main():
    # The monkey_patching is now done at the very top of the file.
    # This function now just runs the SocketIO app.
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, port=5000)

if __name__ == '__main__':
    # Ensure the upload folder exists if you were to implement actual file saving
    # os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
    main()
