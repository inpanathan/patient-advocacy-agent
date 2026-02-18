"""WebRTC server for camera and audio streaming.

Provides the real-time communication interface for voice-only
patient interaction and permission-gated image capture.

TODO: Requires aiortc for real WebRTC implementation.
      This is a stub/interface that defines the expected API.

Covers: Phase 4 voice pipeline
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WebRTCConfig:
    """WebRTC server configuration."""

    stun_server: str = "stun:stun.l.google.com:19302"
    audio_codec: str = "opus"
    video_codec: str = "vp8"
    max_audio_bitrate: int = 32000
    max_video_bitrate: int = 500000


class WebRTCServer:
    """WebRTC server stub.

    In production, this integrates with aiortc to handle
    real-time audio/video streaming from patient devices.

    For development, this provides the interface without
    actual WebRTC connections.
    """

    def __init__(self, config: WebRTCConfig | None = None) -> None:
        self.config = config or WebRTCConfig()
        self._active_connections: dict[str, dict] = {}
        logger.info("webrtc_server_initialized", config=self.config)

    async def handle_offer(self, session_id: str, sdp_offer: str) -> str:
        """Handle WebRTC SDP offer and return answer.

        Args:
            session_id: Patient session ID.
            sdp_offer: SDP offer from client.

        Returns:
            SDP answer string.
        """
        logger.info("webrtc_offer_received", session_id=session_id)
        # Stub: return a mock SDP answer
        self._active_connections[session_id] = {"status": "connected"}
        return "v=0\r\no=- 0 0 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\n"

    async def get_audio_chunk(self, session_id: str) -> bytes:
        """Get the latest audio chunk from a session.

        Args:
            session_id: Patient session ID.

        Returns:
            Raw audio bytes.
        """
        # Stub: return empty audio
        return b"\x00" * 320

    async def capture_image(self, session_id: str) -> bytes:
        """Capture a single image frame from the video stream.

        This should only be called AFTER the patient has given consent.

        Args:
            session_id: Patient session ID.

        Returns:
            JPEG image bytes.
        """
        logger.info("image_captured", session_id=session_id)
        # Stub: return a minimal JPEG header
        return b"\xff\xd8\xff\xe0"

    async def disconnect(self, session_id: str) -> None:
        """Disconnect a WebRTC session."""
        self._active_connections.pop(session_id, None)
        logger.info("webrtc_disconnected", session_id=session_id)

    @property
    def active_connections(self) -> int:
        return len(self._active_connections)
