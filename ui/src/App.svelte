<script lang="ts">
  import ThreeOrb from "./lib/components/ThreeOrb.svelte";
  import MetricsPanel from "./lib/components/MetricsPanel.svelte";
  import LogPanel from "./lib/components/LogPanel.svelte";
  import FileDropZone from "./lib/components/FileDropZone.svelte";
  import StatusText from "./lib/components/StatusText.svelte";
  import SetupScreen from "./lib/components/SetupScreen.svelte";
  import LoadingScreen from "./lib/components/LoadingScreen.svelte";
  import TimePanel from "./lib/components/TimePanel.svelte";
  import WeatherPanel from "./lib/components/WeatherPanel.svelte";
  import ModulesPanel from "./lib/components/ModulesPanel.svelte";
  import CameraFeedPanel from "./lib/components/CameraFeedPanel.svelte";
  import ChatPanel from "./lib/components/ChatPanel.svelte";

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

    <ThreeOrb />

    <div class="hud-layout">
      <div class="left-panel">
        <TimePanel />
        <WeatherPanel />
        <MetricsPanel />
        <ModulesPanel />
      </div>

      <div class="center-top">
        <div class="core-brackets">
          <div class="c-bracket tl"></div><div class="c-bracket tr"></div>
          <div class="c-bracket bl"></div><div class="c-bracket br"></div>
        </div>
        <div class="core-title">M.I.A</div>
      </div>

      <div class="center-bottom">
        <StatusText state={$currentState} />
      </div>

      <div class="right-panel">
        <CameraFeedPanel />
        <LogPanel 
          {messages} 
          {ws} 
          state={$currentState}
          onUserMessage={(text) => {
            const now = new Date().toTimeString().split(" ")[0];
            messages = [...messages, { time: now, sender: "USER", text }];
          }}
        />
        <ChatPanel on:send={(e) => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "text_command", text: e.detail }));
            const now = new Date().toTimeString().split(" ")[0];
            messages = [...messages, { time: now, sender: "USER", text: e.detail }];
          }
        }} />
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
    gap: 24px;
    width: clamp(200px, 20vw, 320px);
    height: 100%;
    animation: bootSlideLeft 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }

  .center-bottom {
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    pointer-events: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    opacity: 0;
    animation: bootFadeUp 1.2s ease-out forwards;
    animation-delay: 0.4s;
  }

  .center-top {
    position: absolute;
    top: 40px;
    left: 50%;
    transform: translateX(-50%);
    pointer-events: auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .core-title {
    font-size: 2rem;
    letter-spacing: 6px;
    color: var(--text);
    font-weight: 300;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
  }


  .core-brackets {
    position: absolute;
    width: 140%;
    height: 140%;
    top: -20%;
    left: -20%;
    pointer-events: none;
  }
  
  .c-bracket {
    position: absolute;
    width: 12px; height: 12px;
    border: 1px solid var(--text-dim);
  }
  .c-bracket.tl { top: 0; left: 0; border-right: none; border-bottom: none; }
  .c-bracket.tr { top: 0; right: 0; border-left: none; border-bottom: none; }
  .c-bracket.bl { bottom: 0; left: 0; border-right: none; border-top: none; }
  .c-bracket.br { bottom: 0; right: 0; border-left: none; border-top: none; }



  .right-panel {
    display: flex;
    flex-direction: column;
    width: clamp(300px, 30vw, 480px);
    height: 100%;
    pointer-events: none;
    opacity: 0;
    animation: bootSlideRight 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    animation-delay: 0.2s;
  }

  @keyframes bootSlideLeft {
    0% { transform: translateX(-60px); opacity: 0; }
    100% { transform: translateX(0); opacity: 1; }
  }

  @keyframes bootSlideRight {
    0% { transform: translateX(60px); opacity: 0; }
    100% { transform: translateX(0); opacity: 1; }
  }

  @keyframes bootFadeUp {
    0% { transform: translate(-50%, 30px); opacity: 0; }
    100% { transform: translate(-50%, 0); opacity: 1; }
  }

  :global(.right-panel > .scifi-panel) {
    margin-bottom: 16px;
  }

  :global(.right-panel > .scifi-panel:last-child) {
    margin-bottom: 0;
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
