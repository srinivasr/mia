<script lang="ts">
  import { afterUpdate, onMount, onDestroy } from "svelte";
  import { rmsLevel } from "../stores/audioStore";
  import { currentState } from "../stores/miaState";

  export let messages: { time: string; sender: string; text: string }[] = [];
  export let ws: WebSocket | null = null;
  export let state: string = "INITIALISING";
  export let onUserMessage: (text: string) => void = () => {};

  let scrollContainer: HTMLDivElement;
  let inputValue = "";
  let micMuted = false;

  let showDevices = false;

  const suggestions = [
    "What can you do?",
    "Tell me about yourself",
    "Check my system",
    "Open my projects",
    "What's going on in the world?",
  ];

  afterUpdate(() => {
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  });

  function getColor(sender: string): string {
    if (sender === "USER") return "#ffcc00";
    if (sender === "MIA") return "var(--pri)";
    if (sender === "ERR") return "var(--red)";
    return "#555";
  }

  function getStatusLabel(s: string): string {
    if (s === "Listening") return "LISTENING";
    if (s === "Thinking") return "THINKING";
    if (s === "Speaking") return "SPEAKING";
    if (s === "Error") return "ERROR";
    return "STANDBY";
  }

  function handleSend(text?: string) {
    const t = text ?? inputValue.trim();
    if (!t || !ws || ws.readyState !== WebSocket.OPEN) return;
    onUserMessage(t);
    ws.send(JSON.stringify({ type: "text_command", text: t }));
    inputValue = "";
  }

  function toggleMic() {
    micMuted = !micMuted;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "mute", muted: micMuted }));
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") handleSend();
  }
</script>

<div class="terminal">
  <div class="term-header">
    <div class="traffic-lights">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>
    <span class="term-title">M.I.A. TERMINAL — <span class="state-label">{state.toUpperCase()}</span></span>
    <button class="gear-btn" aria-label="Settings" on:click={() => (showDevices = !showDevices)}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
    </button>
  </div>

  <div class="term-body" bind:this={scrollContainer}>
    {#each messages as msg}
      <div class="log-line" style="color: {getColor(msg.sender)}">
        <span class="log-time">{msg.time}</span>
        <span class="log-sender">{msg.sender.padEnd(4)}</span>
        <span class="log-sep">▸</span>
        <span class="log-text">{msg.text}</span>
      </div>
    {/each}
  </div>

  <div class="suggestions-row">
    {#each suggestions as s}
      <button class="suggestion-chip" on:click={() => handleSend(s)}>
        {s}
      </button>
    {/each}
  </div>

  <div class="term-input-row">
    <button
      class="mic-btn"
      class:active={!micMuted}
      class:recording={!micMuted && state === "Listening"}
      aria-label={micMuted ? "Unmute microphone" : "Mute microphone"}
      on:click={toggleMic}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><line x1="12" y1="19" x2="12" y2="22"/>
      </svg>
    </button>
    <span class="prompt">&gt;</span>
    <input
      type="text"
      bind:value={inputValue}
      on:keydown={handleKeydown}
      placeholder="Type a message..."
      class="term-input"
    />
  </div>

  <div class="term-status">
    <span class="status-dot" class:alive={state !== "Error" && state !== ""}></span>
    <span class="status-text">{getStatusLabel(state)}</span>
    <div class="rms-bar-track">
      <div
        class="rms-bar-fill"
        style="width: {state === 'Speaking' ? Math.min(100, ($rmsLevel || 0) * 100 + 40) : state === 'Listening' ? Math.min(60, ($rmsLevel || 0) * 60 + 10) : 0}%"
      ></div>
    </div>
  </div>
</div>

<style>
  .terminal {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #0a0a0a;
    border-left: 1px solid #1a1a1a;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    overflow: hidden;
  }

  .term-header {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid #1a1a1a;
    flex-shrink: 0;
    gap: 12px;
  }

  .traffic-lights {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .dot.red { background: #ff5f56; }
  .dot.yellow { background: #ffbd2e; }
  .dot.green { background: #27c93f; }

  .term-title {
    flex: 1;
    text-align: center;
    font-size: 0.65rem;
    color: #555;
    letter-spacing: 0.5px;
  }

  .state-label {
    color: var(--pri);
  }

  .gear-btn {
    background: none;
    border: none;
    color: #333;
    cursor: pointer;
    padding: 2px;
    flex-shrink: 0;
  }

  .gear-btn:hover {
    color: #666;
  }

  .term-body {
    flex: 1;
    overflow-y: auto;
    padding: 8px 12px;
    scrollbar-width: thin;
    scrollbar-color: #1a1a1a transparent;
  }

  .term-body::-webkit-scrollbar {
    width: 6px;
  }

  .term-body::-webkit-scrollbar-thumb {
    background: #1a1a1a;
    border-radius: 3px;
  }

  .log-line {
    font-size: 0.75rem;
    line-height: 1.6;
    animation: fadeIn 0.15s ease;
    display: flex;
    gap: 6px;
  }

  .log-time {
    color: #444;
    flex-shrink: 0;
  }

  .log-sender {
    flex-shrink: 0;
  }

  .log-sep {
    color: #444;
    flex-shrink: 0;
  }

  .log-text {
    flex: 1;
    word-wrap: break-word;
    white-space: pre-wrap;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .suggestions-row {
    display: flex;
    gap: 8px;
    padding: 6px 12px 4px;
    overflow-x: auto;
    flex-shrink: 0;
    scrollbar-width: none;
  }

  .suggestions-row::-webkit-scrollbar {
    display: none;
  }

  .suggestion-chip {
    flex-shrink: 0;
    padding: 6px 14px;
    border-radius: 14px;
    font-size: 0.75rem;
    font-weight: 500;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    background: #1a1a2a;
    color: #99aabb;
    border: 1px solid #2a2a3a;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s;
    letter-spacing: 0.3px;
  }

  .suggestion-chip:hover {
    color: #c8d8e8;
    border-color: var(--pri);
    background: #1e1e32;
    box-shadow: 0 0 12px rgba(74, 229, 255, 0.08);
  }

  .term-input-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-top: 1px solid #1a1a1a;
    flex-shrink: 0;
  }

  .mic-btn {
    background: none;
    border: 1px solid #222;
    color: #555;
    border-radius: 4px;
    padding: 4px 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    transition: all 0.15s;
    flex-shrink: 0;
  }

  .mic-btn:hover {
    color: #888;
    border-color: #444;
  }

  .mic-btn.active {
    color: #2a5;
    border-color: #2a5;
  }

  .mic-btn.recording {
    color: #2a5;
    border-color: #2a5;
    box-shadow: 0 0 10px rgba(34, 170, 85, 0.2);
    background: rgba(34, 170, 85, 0.08);
  }

  .prompt {
    color: #2a5;
    font-size: 0.85rem;
    flex-shrink: 0;
  }

  .term-input {
    flex: 1;
    background: transparent;
    border: none;
    color: #c0c0c0;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 0.75rem;
    outline: none;
    caret-color: #c0c0c0;
  }

  .term-input::placeholder {
    color: #333;
  }

  .term-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    border-top: 1px solid #1a1a1a;
    flex-shrink: 0;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #333;
    flex-shrink: 0;
  }

  .status-dot.alive {
    background: #2a5;
    box-shadow: 0 0 6px rgba(34, 170, 85, 0.4);
  }

  .status-text {
    font-size: 0.6rem;
    color: #555;
    letter-spacing: 1px;
    text-transform: uppercase;
    flex-shrink: 0;
  }

  .rms-bar-track {
    flex: 1;
    height: 2px;
    background: #1a1a1a;
    border-radius: 1px;
    overflow: hidden;
  }

  .rms-bar-fill {
    height: 100%;
    background: #2a5;
    border-radius: 1px;
    transition: width 0.05s linear;
  }
</style>
