# MIA

A realtime multimodal AI runtime platform.

---

## Overview

MIA is a low-latency, event-driven runtime system for voice and multimodal AI applications. It implements a streaming-first architecture that natively integrates with desktop environments and handles full-duplex communication pipelines.

Key technical specifications:
- Target end-to-end latency: < 900ms
- Architecture: Slot-Hook event-driven orchestration
- Modalities: Voice, Text, Image, Screen Context

## Architecture

The project is structured around a strict separation of concerns to maximize modularity and performance:

| Component | Responsibility | Technology Stack |
|---|---|---|
| **Frontend** | Visualization and UI overlay | Svelte, Tailwind |
| **Desktop Runtime** | Native OS bindings, Audio I/O, Hotkeys | Tauri, Rust |
| **Orchestration** | Agentic logic, API integration, Tools | Python 3.11+, AsyncIO |

### Data Flow

```text
┌──────────────────────────────────────────────────┐
│                    SVELTE UI                     │
│               Visualization Layer                │
└───────────────────────┬──────────────────────────┘
                        │
                  WebSocket Events
                        │
┌───────────────────────▼──────────────────────────┐
│               TAURI RUNTIME (Rust)               │
│          Audio Capture & Playback, IPC           │
└───────────────────────┬──────────────────────────┘
                        │
                  IPC / gRPC / WS
                        │
┌───────────────────────▼──────────────────────────┐
│                MIA BRAIN (Python)                │
│    Orchestrator, STT/LLM/TTS, Tool Execution     │
└──────────────────────────────────────────────────┘
```

## Core Systems

### Voice Pipeline
A streaming STT → LLM → TTS full-duplex pipeline that handles instantaneous interruption, barge-in detection, and echo cancellation natively.

### Event-Driven Orchestration
The runtime uses a Slot-Hook design pattern.
- **Slots**: Interchangeable capability interfaces (e.g., LLM Slot, TTS Slot).
- **Hooks**: Lifecycle extensions allowing side-effects without mutating core logic (e.g., `before_llm`, `on_interrupt`).

## Repository Structure

```text
mia/
├── brain/         # Python orchestrator and model integrations
├── ui/            # Rust/Svelte desktop client
├── mia.config.toml# Global runtime configuration
└── run.sh         # Launch script
```

## Quick Start

Requirements: Node.js, Rust/Cargo, Python 3.11+.

```bash
git clone <repo-url> mia
cd mia
./run.sh
```
