# audiolms/live/webrtc_manager.py
from aiortc import RTCPeerConnection, RTCConfiguration
from aiortc.contrib.media import MediaRelay, MediaStreamTrack # MediaStreamTrack for type hinting
import asyncio
import logging

logger = logging.getLogger(__name__)

class WebRTCManager:
    """
    Manages RTCPeerConnection objects for active WebRTC sessions.
    Provides methods to create, retrieve, and close connections,
    and manage active live sessions (e.g., classes).
    """
    def __init__(self):
        # Stores active RTCPeerConnection objects: sid -> RTCPeerConnection
        self._peer_connections = {}
        # Stores active live session data: session_id -> {'teacher_sid': str, 'teacher_audio_track': MediaStreamTrack}
        self._live_sessions = {}
        # Lock to ensure thread-safe access to _peer_connections and _live_sessions
        self._peer_connection_lock = asyncio.Lock()

    async def add_peer_connection_for_sid(self, sid: str, config: RTCConfiguration = None) -> RTCPeerConnection:
        """
        Adds a new RTCPeerConnection for a given SocketIO SID if one doesn't already exist.
        Returns the created or existing RTCPeerConnection.
        """
        async with self._peer_connection_lock:
            if sid not in self._peer_connections:
                pc = RTCPeerConnection(config)
                self._peer_connections[sid] = pc
                logger.info(f"Created new RTCPeerConnection for SID: {sid}")
                return pc
            else:
                logger.warning(f"RTCPeerConnection already exists for SID: {sid}. Returning existing one.")
                return self._peer_connections[sid]

    def get_peer_connection(self, sid: str) -> RTCPeerConnection | None:
        """
        Retrieves an RTCPeerConnection by SocketIO SID.
        Returns None if no connection is found for the SID.
        """
        return self._peer_connections.get(sid)

    async def close_peer_connection(self, sid: str):
        """
        Closes and removes an RTCPeerConnection by SocketIO SID.
        Also cleans up any associated live session data if the disconnected peer was a teacher.
        """
        async with self._peer_connection_lock:
            pc = self._peer_connections.pop(sid, None)
            if pc:
                logger.info(f"Closing RTCPeerConnection for SID: {sid}")
                await pc.close()
                
                # Clean up any associated live session data if this SID was a teacher
                # Iterate over a copy of items to allow modification during iteration
                for session_id, data in list(self._live_sessions.items()):
                    if data.get('teacher_sid') == sid:
                        self._live_sessions.pop(session_id)
                        logger.info(f"Closed live session {session_id} due to teacher {sid} disconnect.")
                        # TODO: In a real app, you would notify all students in this session
                        # that the teacher has disconnected. This could involve emitting a SocketIO event.
            else:
                logger.warning(f"No RTCPeerConnection found for SID {sid} to close.")

    def activate_live_session(self, session_id: str, teacher_sid: str):
        """
        Activates a live session, associating a teacher SID with it.
        This marks a session as active and designates a teacher.
        """
        if session_id not in self._live_sessions:
            self._live_sessions[session_id] = {
                'teacher_sid': teacher_sid,
                'teacher_audio_track': None # This will be set when the teacher's track is received
            }
            logger.info(f"Live session '{session_id}' activated by teacher {teacher_sid}")
        else:
            logger.warning(f"Live session '{session_id}' already active. Teacher SID: {self._live_sessions[session_id]['teacher_sid']}")

    def get_live_session_teacher(self, session_id: str) -> str | None:
        """
        Returns the teacher's SID for a given live session.
        Returns None if the session is not active or no teacher is assigned.
        """
        session_data = self._live_sessions.get(session_id)
        return session_data['teacher_sid'] if session_data else None

    def set_teacher_audio_track(self, teacher_sid: str, track: MediaStreamTrack):
        """
        Sets the audio track for a teacher in an active session.
        This track is typically received from the teacher's browser.
        """
        found = False
        for session_id, data in self._live_sessions.items():
            if data.get('teacher_sid') == teacher_sid:
                data['teacher_audio_track'] = track
                logger.info(f"Teacher {teacher_sid} audio track set for session {session_id}.")
                found = True
                break
        if not found:
            logger.warning(f"Could not find active session for teacher SID {teacher_sid} to set audio track.")

    def get_teacher_audio_track(self, teacher_sid: str) -> MediaStreamTrack | None:
        """
        Retrieves the audio track for a teacher in an active session.
        Returns None if the teacher's track is not found or not yet set.
        """
        for session_id, data in self._live_sessions.items():
            if data.get('teacher_sid') == teacher_sid:
                return data['teacher_audio_track']
        return None
