<script lang="ts">
  import { afterUpdate } from "svelte";

  export let messages: { time: string, sender: string, text: string }[] = [];

  let scrollContainer: HTMLDivElement;

  afterUpdate(() => {
    if (scrollContainer) {
      scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }
  });

  function getColor(sender: string, text: string): string {
    const tl = text.toLowerCase();
    if (sender === "USER" || tl.startsWith("you:")) return "var(--white)";
    if (sender === "MIA" || tl.startsWith("mia:")) return "var(--pri)";
    if (tl.startsWith("file:")) return "var(--green)";
    if (tl.includes("err")) return "var(--red)";
    return "var(--acc2)"; // default sys color
  }
</script>

<div class="log-panel" bind:this={scrollContainer}>
  {#each messages as msg}
    <div class="log-line">
      <span style="color: {getColor(msg.sender, msg.text)}">
        {msg.text}
      </span>
    </div>
  {/each}
</div>

<style>
  .log-panel {
    background-color: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 8px;
    height: 100%;
    width: 100%;
    overflow-y: auto;
    font-family: "Courier New", Courier, monospace;
    font-size: 13px;
    line-height: 1.4;
    pointer-events: auto;
    /* Custom scrollbar */
    scrollbar-width: thin;
    scrollbar-color: var(--border-b) var(--bg);
  }

  .log-panel::-webkit-scrollbar {
    width: 8px;
    background: var(--bg);
  }

  .log-panel::-webkit-scrollbar-thumb {
    background: var(--border-b);
    border-radius: 4px;
    min-height: 20px;
  }

  .log-line {
    margin-bottom: 4px;
    word-wrap: break-word;
    white-space: pre-wrap;
  }
</style>
