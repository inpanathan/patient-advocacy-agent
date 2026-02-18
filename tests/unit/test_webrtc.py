"""Tests for WebRTC server stub."""

from __future__ import annotations

import pytest

from src.pipelines.webrtc_server import WebRTCConfig, WebRTCServer


class TestWebRTCServer:
    """Test WebRTC server stub."""

    @pytest.mark.asyncio
    async def test_handle_offer(self):
        """Server handles SDP offer and returns answer."""
        server = WebRTCServer()
        answer = await server.handle_offer("session-1", "v=0\r\n")
        assert answer  # non-empty SDP answer
        assert server.active_connections == 1

    @pytest.mark.asyncio
    async def test_get_audio_chunk(self):
        """Server returns audio chunk."""
        server = WebRTCServer()
        audio = await server.get_audio_chunk("session-1")
        assert isinstance(audio, bytes)
        assert len(audio) > 0

    @pytest.mark.asyncio
    async def test_capture_image(self):
        """Server captures an image frame."""
        server = WebRTCServer()
        image = await server.capture_image("session-1")
        assert isinstance(image, bytes)
        assert len(image) > 0

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Server disconnects a session."""
        server = WebRTCServer()
        await server.handle_offer("session-1", "sdp")
        assert server.active_connections == 1
        await server.disconnect("session-1")
        assert server.active_connections == 0

    def test_custom_config(self):
        """Server accepts custom configuration."""
        config = WebRTCConfig(audio_codec="opus", max_audio_bitrate=64000)
        server = WebRTCServer(config)
        assert server.config.max_audio_bitrate == 64000
