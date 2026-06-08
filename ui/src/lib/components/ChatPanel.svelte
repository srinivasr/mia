<script lang="ts">
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();
  let inputText = "";

  const suggestions = [
    "/help",
    "/status",
    "/clear"
  ];

  function handleSend() {
    if (inputText.trim()) {
      dispatch("send", inputText);
      inputText = "";
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") handleSend();
  }
</script>

<div class="chat-panel">
  <div class="suggestions">
    {#each suggestions as sug}
      <button class="chip" on:click={() => { inputText = sug; handleSend(); }}>{sug}</button>
    {/each}
  </div>
  
  <div class="input-area">
    <div class="mic-icon">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
      </svg>
    </div>
    <input 
      type="text" 
      placeholder="Type a message..." 
      bind:value={inputText}
      on:keydown={handleKeydown}
    />
    <button class="send-btn" aria-label="Send Message" on:click={handleSend}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    </button>
  </div>
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .suggestions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .chip {
    background: transparent;
    border: 1px solid rgba(0, 230, 255, 0.2);
    color: var(--text-dim);
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    cursor: pointer;
    transition: all 0.2s;
  }
  .chip:hover {
    border-color: var(--pri);
    color: var(--pri);
  }
  .input-area {
    display: flex;
    align-items: center;
    background: rgba(3, 9, 20, 0.6);
    border: 1px solid rgba(0, 230, 255, 0.2);
    border-radius: 4px;
    padding: 8px 12px;
  }
  .mic-icon {
    color: var(--green);
    margin-right: 12px;
    display: flex;
    align-items: center;
  }
  input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    outline: none;
  }
  input::placeholder {
    color: rgba(255, 255, 255, 0.2);
  }
  .send-btn {
    background: transparent;
    border: none;
    color: var(--pri);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
  }
  .send-btn:hover {
    color: var(--pri-dim);
  }
</style>
