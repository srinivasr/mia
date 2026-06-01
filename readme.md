<p align="center">
  <h1 align="center">MIA_N_MIA</h1>
  <p align="center">
    Realtime Multimodal AI Runtime Platform
  </p>
</p>

---

<p align="center">
  <img src="https://img.shields.io/badge/Realtime-AI_Runtime-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Tauri-Rust-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Python-Orchestrator-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Svelte-Frontend-ff3e00?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Streaming-First-purple?style=for-the-badge"/>
</p>

---

## Overview

MIA_N_MIA is a realtime multimodal AI runtime system designed for:

* low-latency voice interaction
* native desktop integration
* streaming-first AI pipelines
* event-driven orchestration
* slot-hook extensibility
* multimodal intelligence
* future autonomous agent systems

Unlike traditional assistant applications, MIA_N_MIA is architected as a modular AI runtime platform.

---

# Core Philosophy

```text
Frontend
    = Visualization Layer

Rust Runtime
    = Native Realtime Infrastructure

Python Brain
    = Orchestration Intelligence
```

This separation allows:

* low latency execution
* modular scalability
* runtime extensibility
* provider abstraction
* native OS integration
* future AI operating system capabilities

---

# Core Features

## Realtime Voice Runtime

* Streaming STT → LLM → TTS pipeline
* Full interruption support
* Barge-in detection
* Stream cancellation propagation
* Realtime waveform rendering
* Echo cancellation support
* Low-latency audio runtime

---

## Native Desktop Runtime

Built using:

* Tauri
* Rust
* Native system APIs

Capabilities:

* global hotkeys
* transparent desktop window
* GPU-aware execution
* native audio pipelines
* system-level integrations

---

## Event-Driven Runtime

The runtime is fully event-driven.

Example runtime events:

```text
VOICE_STARTED
TRANSCRIPT_READY
TOKEN_GENERATED
TTS_STARTED
PLAYBACK_INTERRUPTED
TOOL_EXECUTED
ERROR_OCCURRED
```

Benefits:

* loose coupling
* scalability
* observability
* plugin systems
* modular orchestration

---

# Slot-Hook Architecture

MIA_N_MIA uses a dedicated slot-hook runtime architecture.

---

## Slots

Slots define capability boundaries.

Examples:

```text
LLM Slot
TTS Slot
STT Slot
Tool Slot
Memory Slot
Vision Slot
```

Dynamic provider registration:

```python
llm_slot.register(openai_provider)
llm_slot.register(local_provider)
```

---

## Hooks

Hooks extend lifecycle behavior.

Examples:

```text
before_llm
after_llm
before_tool
after_tool
on_interrupt
```

Hooks enable:

* memory injection
* analytics
* tracing
* moderation
* runtime extensions

without modifying orchestration logic.

---

# Multimodal Runtime

MIA_N_MIA is multimodal-native.

Supported architecture:

* voice
* text
* image
* screen context
* OCR
* PDF parsing
* future video pipelines

Planned capabilities:

* screenshot understanding
* screen-aware assistance
* visual grounding
* document reasoning

---

# Streaming-First Design

Pipeline:

```text
Mic Input
   ↓
Voice Activity Detection
   ↓
Speech-to-Text Stream
   ↓
LLM Token Stream
   ↓
TTS Audio Stream
   ↓
Realtime Playback
```

Target latency:

```text
< 900ms end-to-end voice latency
```

---

# Tech Stack

| Layer            | Technology                  |
| ---------------- | --------------------------- |
| Frontend         | Svelte + Tailwind           |
| Desktop Runtime  | Tauri                       |
| Systems Layer    | Rust                        |
| AI Orchestration | Python                      |
| Communication    | WebSockets + gRPC           |
| STT              | Whisper / Deepgram          |
| LLM              | OpenAI / Gemini / Ollama    |
| TTS              | Kokoro / Piper / ElmianLabs |
| Streaming        | AsyncIO + WebSockets        |
| Observability    | Structured Tracing          |
| Future Memory    | Vector Retrieval            |

---

# Architecture

```text
┌──────────────────────────────┐
│         SVELTE UI            │
│ Orb · Chat · Waveform · UI   │
└──────────────┬───────────────┘
               │
         WebSocket Events
               │
┌──────────────▼───────────────┐
│     TAURI RUNTIME (Rust)     │
│ Audio · Playback · Hotkeys   │
│ Native APIs · Streaming      │
└──────────────┬───────────────┘
               │
              gRPC
               │
┌──────────────▼───────────────┐
│      MIA BRAIN (Python)      │
│ Orchestrator · LLM · STT     │
│ TTS · Tools · Memory         │
└──────────────────────────────┘
```

---

# Repository Structure

For optimal developer experience, the project is structured into two clean top-level directories:

* **`ui/`**: Contains all Frontend (Svelte/Vite/Node) and Desktop (Tauri/Rust) code.
* **`brain/`**: Contains all Python AI Orchestration, Tools, and Memory logic.

```text
mia_n_eve/
├── brain/         # Python logic
├── ui/            # Svelte + Rust Tauri app
├── .env           
├── run.sh
└── readme.md
```

---

# Runtime Systems

## Event Bus

Central communication system between runtime modules.

---

## FSM (Finite State Machine)

Controls assistant behavior states:

```text
IDLE
LISTENING
PROCESSING
SPEAKING
INTERRUPTED
ERROR
```

---

## Stream Controller

Handles:

* interruptions
* retries
* backpressure
* cancellation
* stream ownership

---

## Capability System

Controls runtime permissions:

```text
filesystem_access
browser_access
network_access
camera_access
shell_execution
```

---

## Tool Runtime

Sandboxed execution layer for:

* filesystem tools
* shell tools
* browser tools
* future MCP-style integrations

