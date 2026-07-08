<script lang="ts">
  import { onDestroy } from "svelte";
  import { get } from "svelte/store";
  import {
    setupStep,
    apiKey,
    apiKeyError,
    configStatus,
    wizardComplete,
    flashOverlay,
    type CheckResult,
    type CheckErrors,
  } from "../stores/setupStore";

  export let ws: WebSocket | null = null;

  let currentWs: WebSocket | null = null;

  let launchReady = false;
  let launchLine = 0;
  let flashTriggered = false;
  let launchTimers: ReturnType<typeof setTimeout>[] = [];
  let requireWakeWord = true;

  function startLaunchSequence() {
    launchLine = 1;
    launchTimers = [
      setTimeout(() => {
        launchLine = 2;
      }, 1500),
      setTimeout(() => {
        launchLine = 3;
      }, 3000),
    ];
  }

  function triggerFlash() {
    flashOverlay.set(true);
    setTimeout(() => {
      wizardComplete.set(true);
      setTimeout(() => flashOverlay.set(false), 300);
    }, 300);
  }

  $: if (
    $setupStep === "launching" &&
    launchReady &&
    launchLine >= 3 &&
    !flashTriggered
  ) {
    flashTriggered = true;
    triggerFlash();
  }

  function send(msg: Record<string, unknown>) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }

  function allChecksDone(c: CheckResult): boolean {
    return (
      c.mic !== null &&
      c.mic !== "listening" &&
      c.speakers !== null &&
      c.internet === true &&
      c.gemini === true
    );
  }

  function allChecksHaveResult(c: CheckResult): boolean {
    return (
      c.mic !== null &&
      c.mic !== "listening" &&
      c.speakers !== null &&
      c.internet !== null &&
      c.gemini !== null
    );
  }

  function criticalChecksPassed(c: CheckResult): boolean {
    return c.internet === true && c.gemini === true;
  }

  function handleBridgeMessage(event: MessageEvent) {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "config") {
        configStatus.set({
          configured: !!msg.configured,
          key_valid: msg.key_valid ?? null,
          checks: msg.checks ?? {
            mic: null,
            speakers: null,
            internet: null,
            gemini: null,
          },
          check_errors: msg.check_errors ?? {},
        });
        if (msg.configured && msg.key_valid) {
          // Key exists — skip API step, go straight to checks
          setupStep.set("checks");
          send({ type: "run_checks" });
        } else {
          apiKey.set("");
          setupStep.set("api_key");
        }
      } else if (msg.type === "config_update") {
        if (msg.key_valid !== undefined) {
          configStatus.update((s) => ({ ...s, key_valid: msg.key_valid }));
          if (msg.key_valid) {
            apiKeyError.set("");
            configStatus.update((s) => ({ ...s, configured: true }));
            setupStep.set("checks");
            send({ type: "run_checks" });
          } else {
            apiKeyError.set("Invalid API key. Please check and try again.");
          }
        }
        if (msg.checks) {
          configStatus.update((s) => ({
            ...s,
            checks: { ...s.checks, ...msg.checks },
          }));
        }
        if (msg.errors) {
          configStatus.update((s) => ({
            ...s,
            check_errors: { ...s.check_errors, ...msg.errors },
          }));
        }
        if (msg.launch_ready) {
          launchReady = true;
        }
        if (msg.config_done) {
          setupStep.set("launching");
        }
      }
    } catch {}
  }

  function handleKeySubmit() {
    const key = get(apiKey);
    if (!key || key.length < 16) {
      apiKeyError.set("Key must be at least 16 characters.");
      return;
    }
    apiKeyError.set("");
    send({ type: "set_api_key", key: key.trim() });
  }

  function finishSetup() {
    send({ type: "config_done", require_wake_word: requireWakeWord });
  }

  function goBackToApiKey() {
    setupStep.set("api_key");
    configStatus.update((s) => ({
      ...s,
      checks: { mic: null, speakers: null, internet: null, gemini: null },
      check_errors: {},
    }));
  }

  function retryChecks() {
    setupStep.set("checks");
    configStatus.update((s) => ({
      ...s,
      checks: { mic: null, speakers: null, internet: null, gemini: null },
      check_errors: {},
    }));
    send({ type: "run_checks" });
  }

  $: if (ws && ws !== currentWs) {
    if (currentWs) {
      currentWs.removeEventListener("message", handleBridgeMessage);
    }
    currentWs = ws;
    ws.addEventListener("message", handleBridgeMessage);
    send({ type: "get_config" });
  }

  $: if ($setupStep === "launching") {
    startLaunchSequence();
  }

  onDestroy(() => {
    if (currentWs) {
      currentWs.removeEventListener("message", handleBridgeMessage);
    }
    launchTimers.forEach(clearTimeout);
  });

  const checkLabels: Record<keyof CheckResult, string> = {
    mic: "Microphone",
    speakers: "Speakers",
    internet: "Internet",
    gemini: "Gemini API",
  };
</script>

<div class="setup-screen">
  <div class="setup-container">
    <header>
      <h1>I NEED YOUR HELP🥵</h1>
      <p class="subtitle">Configure your AI assistant</p>
    </header>

    {#if $setupStep === "loading"}
      <div class="step loading-step">
        <div class="orb-pulse"></div>
        <h2>Connecting to Mia...</h2>
      </div>
    {:else if $setupStep === "api_key"}
      <div class="step">
        <h2>Step 1: API Key</h2>
        <p>Enter your Gemini API key to get started.</p>
        <div class="input-group">
          <input
            type="password"
            bind:value={$apiKey}
            placeholder="AIzaSy..."
            on:keydown={(e) => e.key === "Enter" && handleKeySubmit()}
          />
          {#if $apiKeyError}
            <p class="error">{$apiKeyError}</p>
          {/if}
          <button
            on:click={handleKeySubmit}
            disabled={!$apiKey || $apiKey.length < 16}
          >
            CONNECT
          </button>
        </div>
        <p class="hint">Get your key at <span>aistudio.google.com</span></p>
      </div>
    {:else if $setupStep === "checks"}
      <div class="step">
        <h2>Step 2: Hardware & Connectivity</h2>
        <p>Verifying your system...</p>
        {#if $configStatus.checks.mic === "listening"}
          <div class="mic-test">
            <div class="mic-pulse"></div>
            <p class="mic-prompt">Say hello to test your microphone...</p>
          </div>
        {/if}
        <div class="checks">
          {#each Object.entries(checkLabels) as [check, label]}
            <div class="check-item">
              <span class="check-label">{label}</span>
              <span class="check-status">
                {#if $configStatus.checks[check as keyof CheckResult] === true}
                  <span class="ok">✓</span>
                {:else if $configStatus.checks[check as keyof CheckResult] === false}
                  <span class="fail">✗</span>
                {:else if $configStatus.checks[check as keyof CheckResult] === "listening"}
                  <span class="recording">◉</span>
                {:else}
                  <span class="pending">◈</span>
                {/if}
              </span>
            </div>
            {#if $configStatus.checks[check as keyof CheckResult] === false && $configStatus.check_errors[check as keyof CheckErrors]}
              <div class="check-error">
                {$configStatus.check_errors[check as keyof CheckErrors]}
              </div>
            {/if}
          {/each}
        </div>
        <div class="settings" style="margin-top: 16px; margin-bottom: 24px;">
          <label class="wake-word-label">
            <input type="checkbox" bind:checked={requireWakeWord} />
            Require Wake Word (Mia)
          </label>
        </div>
        {#if allChecksDone($configStatus.checks)}
          <button on:click={finishSetup} class="continue-btn">
            LAUNCH MIA😘
          </button>
        {:else if allChecksHaveResult($configStatus.checks) && !criticalChecksPassed($configStatus.checks)}
          <div class="critical-fail">
            <p>
              Internet connection and a valid Gemini API key are required for
              Mia to function.
            </p>
          </div>
          <div class="checks-actions">
            <button on:click={goBackToApiKey} class="back-btn">BACK</button>
            <button on:click={retryChecks} class="retry-btn">
              RETRY CHECKS
            </button>
          </div>
        {:else}
          <button on:click={goBackToApiKey} class="back-btn centered">
            BACK
          </button>
        {/if}
      </div>
    {:else if $setupStep === "launching"}
      <div class="step launching-step">
        <div class="launch-orb"></div>
        <div class="status-lines">
          {#if launchLine >= 1}
            <p class="status-line">&gt; ESTABLISHING LINK...</p>
          {/if}
          {#if launchLine >= 2}
            <p class="status-line">&gt; CALIBRATING...</p>
          {/if}
          {#if launchLine >= 3}
            <p class="status-line online">&gt; MIA IS ONLINE</p>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .setup-screen {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg, #0a0a0f);
    z-index: 9998;
  }

  .setup-container {
    width: 420px;
    max-width: 90vw;
    padding: 40px;
    border: 1px solid var(--border-b, #1a1a2e);
    border-radius: 12px;
    background: rgba(10, 10, 15, 0.95);
  }

  header {
    text-align: center;
    margin-bottom: 32px;
  }

  h1 {
    font-family: "Courier New", monospace;
    font-size: 1.8rem;
    font-weight: 300;
    letter-spacing: 0.4em;
    color: var(--pri, #4ae5ff);
    margin-bottom: 4px;
  }

  .subtitle {
    font-size: 0.8rem;
    opacity: 0.5;
    font-family: "Courier New", monospace;
  }

  .step h2 {
    font-family: "Courier New", monospace;
    font-size: 1rem;
    font-weight: 400;
    color: var(--txt, #c0c0d0);
    margin-bottom: 8px;
  }

  .step p {
    font-size: 0.85rem;
    color: var(--muted-c, #666);
    margin-bottom: 16px;
    font-family: "Courier New", monospace;
  }

  .loading-step {
    text-align: center;
    padding: 40px 0;
  }

  .loading-step h2 {
    margin-top: 16px;
    color: var(--pri, #4ae5ff);
  }

  .orb-pulse {
    width: 60px;
    height: 60px;
    margin: 0 auto;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      var(--pri-gho, rgba(74, 229, 255, 0.3)) 0%,
      transparent 70%
    );
    animation: pulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 40px var(--pri-gho, rgba(74, 229, 255, 0.2));
  }

  @keyframes pulse {
    0%,
    100% {
      transform: scale(0.8);
      opacity: 0.6;
    }
    50% {
      transform: scale(1.2);
      opacity: 1;
    }
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  input {
    width: 100%;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-b, #1a1a2e);
    border-radius: 6px;
    color: var(--txt, #c0c0d0);
    font-family: "Courier New", monospace;
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
    box-sizing: border-box;
  }

  input:focus {
    border-color: var(--pri, #4ae5ff);
  }

  button {
    padding: 12px 24px;
    background: transparent;
    border: 1px solid var(--pri, #4ae5ff);
    color: var(--pri, #4ae5ff);
    font-family: "Courier New", monospace;
    font-size: 0.85rem;
    letter-spacing: 0.15em;
    cursor: pointer;
    transition: all 0.2s;
    border-radius: 6px;
  }

  button:hover:not(:disabled) {
    background: var(--pri, #4ae5ff);
    color: var(--bg, #0a0a0f);
  }

  button:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .error {
    color: #ff3333;
    font-size: 0.8rem;
  }

  .hint {
    margin-top: 12px;
    font-size: 0.75rem;
  }

  .hint span {
    color: var(--pri, #4ae5ff);
  }

  .mic-test {
    text-align: center;
    padding: 16px 0;
  }

  .mic-pulse {
    width: 48px;
    height: 48px;
    margin: 0 auto 12px;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      var(--green, #4ade80) 0%,
      transparent 70%
    );
    animation: mic-pulse 0.8s ease-in-out infinite;
    box-shadow: 0 0 30px var(--green-d, #16a34a);
  }

  @keyframes mic-pulse {
    0%,
    100% {
      transform: scale(0.9);
      opacity: 0.7;
    }
    50% {
      transform: scale(1.3);
      opacity: 1;
    }
  }

  .mic-prompt {
    color: var(--green, #4ade80) !important;
    font-size: 0.9rem !important;
    animation: blink 1.5s step-end infinite;
  }

  @keyframes blink {
    50% {
      opacity: 0.4;
    }
  }

  .checks {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin: 16px 0;
  }

  .check-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 4px;
    font-family: "Courier New", monospace;
    font-size: 0.85rem;
  }

  .check-error {
    padding: 4px 12px 8px 12px;
    margin-bottom: 6px;
    font-family: "Courier New", monospace;
    font-size: 0.75rem;
    color: #ff6666;
    border-left: 2px solid #ff3333;
    margin-left: 12px;
  }

  .check-label {
    color: var(--txt, #c0c0d0);
  }

  .check-status {
    font-size: 1.1rem;
  }

  .ok {
    color: #00ff88;
  }
  .fail {
    color: #ff3333;
  }
  .recording {
    color: #ff3333;
    animation: blink 0.6s step-end infinite;
  }
  .pending {
    color: var(--pri, #4ae5ff);
  }

  .continue-btn {
    display: block;
    margin: 24px auto 0;
    padding: 14px 48px;
  }

  .critical-fail {
    margin-top: 16px;
    text-align: center;
  }

  .critical-fail p {
    color: #ff6666 !important;
    font-size: 0.8rem !important;
  }

  .checks-actions {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin-top: 16px;
  }

  .checks-actions button {
    flex: 1;
  }

  .retry-btn,
  .back-btn {
    display: block;
    padding: 12px 24px;
    border-color: var(--muted-c, #8e8e9c);
    color: var(--muted-c, #8e8e9c);
    font-size: 0.8rem;
  }

  .retry-btn:hover,
  .back-btn:hover {
    background: var(--muted-c, #8e8e9c);
    color: var(--bg, #0a0a0f);
  }

  .retry-btn:hover,
  .continue-btn:hover {
    background: #000;
    color: #fff;
    border-color: #fff;
  }

  .wake-word-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: "Courier New", monospace;
    font-size: 0.85rem;
    color: var(--txt, #c0c0d0);
    cursor: pointer;
  }

  .wake-word-label input {
    width: auto;
    margin: 0;
    cursor: pointer;
  }

  .back-btn.centered {
    display: block;
    margin: 16px auto 0;
    padding: 12px 48px;
  }

  .launching-step {
    text-align: center;
    padding: 60px 0;
  }

  .launch-orb {
    width: 80px;
    height: 80px;
    margin: 0 auto 32px;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      var(--pri-gho, rgba(74, 229, 255, 0.3)) 0%,
      transparent 70%
    );
    animation: pulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 60px var(--pri-gho, rgba(74, 229, 255, 0.2));
  }

  .status-lines {
    text-align: left;
    max-width: 260px;
    margin: 0 auto;
  }

  .status-line {
    font-family: "Courier New", monospace;
    font-size: 0.85rem;
    color: var(--muted-c, #666);
    margin: 8px 0;
    opacity: 0;
    animation: lineFadeIn 0.5s ease forwards;
  }

  .status-line.online {
    color: var(--green, #4ade80) !important;
  }

  @keyframes lineFadeIn {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
