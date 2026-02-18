# System Requirements

**Covers:** REQ-DEP-004

## Minimum Hardware

| Component | Development | Production |
|-----------|------------|------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| GPU | Optional (CUDA 12.x) | NVIDIA GPU with 16+ GB VRAM |
| Disk | 20 GB | 100 GB SSD |
| Network | Broadband | Low-latency, stable |

## Software Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Runtime |
| uv | Latest | Package management |
| Git | 2.x | Version control |
| Docker | 24+ | Containerization |
| docker-compose | 2.x | Multi-container orchestration |
| CUDA Toolkit | 12.x | GPU acceleration (if using GPU) |
| NVIDIA Drivers | 535+ | GPU support (if using GPU) |

## OS Package Dependencies

### Ubuntu / Debian

```bash
# Audio processing (WebRTC, STT/TTS)
sudo apt-get install -y \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libsrtp2-dev \
    libvpx-dev \
    libopus-dev \
    pkg-config

# Image processing
sudo apt-get install -y \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev
```

### macOS (Homebrew)

```bash
brew install opus libvpx srtp ffmpeg pkg-config
```

## Network Requirements

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| FastAPI | 8000 | HTTP | API server |
| WebRTC | 3478 | UDP | STUN/TURN for voice + camera |
| MLflow | 5000 | HTTP | Experiment tracking |
| ChromaDB | 8001 | HTTP | Vector store (if remote) |

## Environment Variables

All required environment variables are documented in `.env.example`.
Copy to `.env` and fill in real values before running.
