<script lang="ts">
  import ThreeOrb from "./lib/components/ThreeOrb.svelte";
  import MetricsPanel from "./lib/components/MetricsPanel.svelte";
  import LogPanel from "./lib/components/LogPanel.svelte";
  import FileDropZone from "./lib/components/FileDropZone.svelte";
  import StatusText from "./lib/components/StatusText.svelte";
  import SetupScreen from "./lib/components/SetupScreen.svelte";
  import LoadingScreen from "./lib/components/LoadingScreen.svelte";

  import { onMount } from "svelte";
  import { open } from "@tauri-apps/plugin-shell";
  import {
    currentState,
    transcript,
    latencyMs,
    isConnected,
  } from "./lib/stores/miaState";
  import { wizardComplete, flashOverlay } from "./lib/stores/setupStore";

  let ws: WebSocket | null = null;
  let reconnectInterval: ReturnType<typeof setInterval>;

  interface Message {
    time: string;
    sender: string;
    text: string;
  }

  let messages: Message[] = [
    {
      time: new Date().toTimeString().split(" ")[0],
      sender: "SYSTEM",
      text: "M.I.A. PROTOCOL INITIALIZED.",
    },
  ];

  onMount(() => {
    window.onerror = function (msg, url, lineNo, columnNo, error) {
      const now = new Date().toTimeString().split(" ")[0];
      messages = [
        ...messages,
        { time: now, sender: "ERR", text: `[ERR] ${msg}` },
      ];
      return false;
    };
    const originalError = console.error;
    console.error = function (...args) {
      if (args[0] && args[0].toString().includes("WebGL")) {
        const now = new Date().toTimeString().split(" ")[0];
        messages = [
          ...messages,
          { time: now, sender: "ERR", text: `[ERR] WebGL: ${args.join(" ")}` },
        ];
      }
      originalError.apply(console, args);
    };

    connectWs();

    reconnectInterval = setInterval(() => {
      if (!ws || ws.readyState === WebSocket.CLOSED) {
        connectWs();
      }
    }, 3000);

    return () => {
      clearInterval(reconnectInterval);
      if (ws) ws.close();
    };
  });

  transcript.subscribe((value) => {
    // If the transcript changes directly without a log message, we handle it if needed
  });

  function connectWs() {
    try {
      ws = new WebSocket("ws://127.0.0.1:8765");

      ws.onopen = () => {
        isConnected.set(true);
        latencyMs.set(15);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "state" && msg.state) {
            const stateStr =
              msg.state.charAt(0).toUpperCase() +
              msg.state.slice(1).toLowerCase();
            currentState.set(stateStr);
          } else if (msg.type === "log" && msg.text) {
            let txt = msg.text;

            if (txt.includes("You:")) {
              // USER messages added locally via onUserMessage callback
            } else {
              let sender = "SYS";
              if (txt.includes("MIA:")) {
                sender = "MIA";
                txt = txt.split("MIA:")[1].trim();
                transcript.set(txt);
              }
              const now = new Date().toTimeString().split(" ")[0];
              messages = [...messages, { time: now, sender, text: txt }];
            }
          } else if (msg.type === "open_url" && msg.url) {
            open(msg.url);
          } else if (msg.type === "transcript" && msg.text) {
            transcript.set(msg.text);
          }
        } catch (e) {
          console.error("WS Parse Error", e);
        }
      };

      ws.onclose = () => {
        isConnected.set(false);
        currentState.set("Error");
      };

      ws.onerror = (e) => {
        isConnected.set(false);
        currentState.set("Error");
      };
    } catch (e) {
      console.error("WS error", e);
    }
  }
</script>

<main data-tauri-drag-region>
  {#if $wizardComplete}
    <div class="grid-background"></div>

    <!-- Central Orb Visualization -->
    <ThreeOrb />

    <!-- Layout Container -->
    <div class="hud-layout">
      <!-- Left Panel: Metrics -->
      <div class="left-panel">
        <MetricsPanel />
      </div>

      <!-- Center Bottom: Status Text & Waveform -->
      <div class="center-bottom">
        <StatusText state={$currentState} />
      </div>

      <!-- Right Panel: Terminal Chat and File Drop -->
      <div class="right-panel">
        <div class="log-container">
          <LogPanel
            {messages}
            {ws}
            state={$currentState}
            onUserMessage={(text) => {
              const now = new Date().toTimeString().split(" ")[0];
              messages = [...messages, { time: now, sender: "USER", text }];
            }}
          />
        </div>
        <div class="drop-container">
          <FileDropZone {ws} />
        </div>
      </div>
    </div>
  {:else if $isConnected}
    <SetupScreen {ws} />
  {:else}
    <LoadingScreen />
  {/if}

  {#if $flashOverlay}
    <div class="flash-overlay"></div>
  {/if}
</main>

<style>
  main {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative;
    background-color: var(--bg);
  }

  .grid-background {
    position: absolute;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 1;
    background-image: radial-gradient(
      circle at center,
      var(--pri-gho) 1.5px,
      transparent 1.5px
    );
    background-size: 48px 48px;
    background-position: center;
  }

  .hud-layout {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 20;
    pointer-events: none; /* Let clicks pass through to drag region / orb */
    display: flex;
    justify-content: space-between;
    padding: 24px;
  }

  .left-panel {
    display: flex;
    flex-direction: column;
    justify-content: center;
    width: clamp(200px, 20vw, 320px);
    height: 100%;
  }

  .center-bottom {
    position: absolute;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    pointer-events: auto;
  }

  .right-panel {
    display: flex;
    flex-direction: column;
    width: clamp(300px, 30vw, 480px);
    height: 100%;
    pointer-events: none;
  }

  .right-panel > * {
    pointer-events: auto;
  }

  .log-container {
    flex: 1;
    margin-bottom: 16px;
    overflow: hidden;
  }

  .drop-container {
    height: 100px;
    flex-shrink: 0;
  }

  .flash-overlay {
    position: fixed;
    inset: 0;
    background: white;
    z-index: 99999;
    animation: flashIn 0.3s ease-out forwards;
    pointer-events: none;
  }

  @keyframes flashIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
</style>
