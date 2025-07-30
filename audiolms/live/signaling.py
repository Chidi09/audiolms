# audiolms/live/signaling.py
import json
import logging
from flask import request # Import request to get sid
from flask_socketio import SocketIO, emit
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaRelay # Useful if you have multiple listeners for one teacher's stream
import asyncio

from ..config import settings # Import settings for STUN servers
from .webrtc_manager import WebRTCManager
from .audio_track import MicrophoneAudioTrack # This will be the source for the teacher (conceptual)


logger = logging.getLogger(__name__)

# Initialize the WebRTCManager globally for the signaling module
webrtc_manager = WebRTCManager()

def setup_live_signaling(socketio: SocketIO):
    """
    Sets up SocketIO event handlers for WebRTC signaling.
    Call this function from your main Flask app with your SocketIO instance.
    """
    @socketio.on('connect')
    async def handle_connect():
        sid = request.sid
        logger.info(f"Socket connected: {sid}")
        # Add a new peer connection for the connecting client
        # Use STUN servers from config.py
        await webrtc_manager.add_peer_connection_for_sid(sid, RTCConfiguration(iceServers=settings.DEFAULT_STUN_SERVERS))
        logger.info(f"New peer connection created for SID: {sid}")

    @socketio.on('disconnect')
    async def handle_disconnect():
        sid = request.sid
        logger.info(f"Socket disconnected: {sid}")
        # Close and remove the peer connection associated with the disconnected SID
        await webrtc_manager.close_peer_connection(sid)
        logger.info(f"Peer connection closed for SID: {sid}")

    @socketio.on('offer')
    async def handle_offer(message):
        sid = request.sid
        offer_sdp = message['sdp']
        offer_type = message['type']
        
        pc = webrtc_manager.get_peer_connection(sid)
        if not pc:
            logger.error(f"No PeerConnection found for SID {sid} when receiving offer.")
            return

        # Define connection state change handler for the current PeerConnection
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state for SID {sid} is {pc.connectionState}")
            if pc.connectionState == "failed":
                logger.warning(f"PeerConnection for SID {sid} failed. Closing.")
                await pc.close()
                await webrtc_manager.close_peer_connection(sid)
            elif pc.connectionState == "closed":
                logger.info(f"PeerConnection for SID {sid} closed.")
        
        # Define track handler for the current PeerConnection
        @pc.on("track")
        async def on_track(track):
            logger.info(f"Track {track.kind} received from SID: {sid}")
            if track.kind == "audio":
                # This is typically the teacher's audio coming from their browser.
                # Store this track in the WebRTCManager, associated with the teacher's SID.
                webrtc_manager.set_teacher_audio_track(sid, track)
                logger.info(f"Teacher {sid} audio track received and stored.")
                
                # If this is a teacher's track, we need to fan it out to students
                # who have joined the same session.
                session_id = None
                for sess_id, data in webrtc_manager._live_sessions.items():
                    if data['teacher_sid'] == sid:
                        session_id = sess_id
                        break
                
                if session_id:
                    # Iterate through all other connected clients (students) in this session
                    # and add the teacher's track to their peer connections.
                    # This assumes a server-side media relay/SFU approach.
                    # For a simple demo, students will initiate connection to receive.
                    # The `join_live_session` logic will handle adding the track.
                    pass # Fan-out logic is handled when students join and request audio.

        # Define ICE candidate handler for the current PeerConnection
        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate:
                logger.info(f"Sending ICE candidate for SID {sid}: {candidate.sdpMid} {candidate.sdpMLineIndex}")
                # Emit the ICE candidate to the specific client (room=sid)
                emit('ice_candidate', {
                    'candidate': candidate.candidate,
                    'sdpMid': candidate.sdpMid,
                    'sdpMLineIndex': candidate.sdpMLineIndex
                }, room=sid)

        try:
            # Create an RTCSessionDescription object from the received offer
            offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
            # Set the remote description (the offer from the client)
            await pc.setRemoteDescription(offer)
            
            # Create an answer to the offer
            answer = await pc.createAnswer()
            # Set the local description (our answer)
            await pc.setLocalDescription(answer)

            logger.info(f"Sending answer to SID {sid}")
            # Emit the answer back to the client
            emit('answer', {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}, room=sid)

        except Exception as e:
            logger.error(f"Error handling offer for SID {sid}: {e}")

    @socketio.on('answer')
    async def handle_answer(message):
        sid = request.sid
        answer_sdp = message['sdp']
        answer_type = message['type']

        pc = webrtc_manager.get_peer_connection(sid)
        if not pc:
            logger.error(f"No PeerConnection found for SID {sid} when receiving answer.")
            return

        try:
            # Create an RTCSessionDescription object from the received answer
            answer = RTCSessionDescription(sdp=answer_sdp, type=answer_type)
            # Set the remote description (the answer from the client)
            await pc.setRemoteDescription(answer)
            logger.info(f"Answer set for SID {sid}")
        except Exception as e:
            logger.error(f"Error handling answer for SID {sid}: {e}")

    @socketio.on('ice_candidate')
    async def handle_ice_candidate(message):
        sid = request.sid
        
        pc = webrtc_manager.get_peer_connection(sid)
        if not pc:
            logger.error(f"No PeerConnection found for SID {sid} when receiving ICE candidate.")
            return

        try:
            # Create an RTCIceCandidate object from the received data
            candidate = RTCIceCandidate(
                candidate=message['candidate'],
                sdpMid=message['sdpMid'],
                sdpMLineIndex=message['sdpMLineIndex']
            )
            # Add the ICE candidate to the PeerConnection
            await pc.addIceCandidate(candidate)
            logger.info(f"ICE candidate added for SID {sid}")
        except Exception as e:
            logger.error(f"Error adding ICE candidate for SID {sid}: {e}")

    # --- Live Room Management Events ---
    @socketio.on('start_live_session')
    async def start_live_session(data):
        """
        Handles a teacher initiating a live session.
        The teacher's browser will send an offer with their audio stream.
        """
        sid = request.sid
        session_id = data.get('session_id')
        user_role = data.get('role', 'teacher')

        if user_role != 'teacher':
            emit('error', {'message': 'Only teachers can start live sessions.'}, room=sid)
            return

        logger.info(f"Teacher {sid} attempting to start live session {session_id}")
        pc = webrtc_manager.get_peer_connection(sid)
        if not pc:
            logger.error(f"No PeerConnection for teacher {sid} to start session.")
            emit('error', {'message': 'No active WebRTC connection found for you.'}, room=sid)
            return

        # Activate the live session in the manager
        webrtc_manager.activate_live_session(session_id, teacher_sid=sid)
        emit('live_session_started', {'session_id': session_id, 'status': 'success'}, room=sid)
        logger.info(f"Live session {session_id} started by teacher {sid}")

    @socketio.on('join_live_session')
    async def join_live_session(data):
        """
        Handles a student joining a live session.
        The student's browser will send an offer requesting to receive audio.
        The server will then add the teacher's audio track to the student's PeerConnection.
        """
        sid = request.sid
        session_id = data.get('session_id')
        
        teacher_sid = webrtc_manager.get_live_session_teacher(session_id)
        if not teacher_sid:
            emit('error', {'message': f'Live session {session_id} not active or no teacher found.'}, room=sid)
            logger.warning(f"Student {sid} tried to join non-existent/inactive session {session_id}.")
            return

        student_pc = webrtc_manager.get_peer_connection(sid)
        teacher_audio_track = webrtc_manager.get_teacher_audio_track(teacher_sid)

        if not student_pc:
             logger.error(f"Missing PeerConnection for student {sid} to join session {session_id}.")
             emit('error', {'message': 'No active WebRTC connection found for you.'}, room=sid)
             return

        if teacher_audio_track:
            logger.info(f"Adding teacher {teacher_sid} audio track to student {sid}'s PC.")
            # Use MediaRelay to subscribe to the teacher's track and add it to the student's PC.
            # This allows multiple students to receive the same teacher's stream.
            student_pc.addTrack(MediaRelay().subscribe(teacher_audio_track))
            logger.info(f"Teacher's audio track added to student {sid}'s PeerConnection.")
        else:
            logger.warning(f"Teacher {teacher_sid} audio track not available yet for student {sid}. Student will connect but might not receive audio immediately.")
            # The student's browser will still send its offer, and once the teacher's track
            # becomes available (via on_track on teacher's PC), it can be added.

        emit('live_session_joined', {'session_id': session_id, 'teacher_sid': teacher_sid}, room=sid)
        logger.info(f"Student {sid} joined live session {session_id}")

    @socketio.on('leave_session')
    async def handle_leave_session(data):
        """
        Handles a client explicitly leaving a live session.
        """
        sid = request.sid
        session_id = data.get('session_id')
        logger.info(f"Client {sid} leaving session {session_id}")
        # Additional logic to remove client from session tracking if needed
        # For now, we rely on disconnect to clean up PC.
        emit('session_left', {'session_id': session_id, 'status': 'success'}, room=sid)
