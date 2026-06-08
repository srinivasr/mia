<script lang="ts">
  import SciFiPanel from "./SciFiPanel.svelte";
  
  const modules = [
    { name: "VOICE", online: true },
    { name: "VISION", online: true },
    { name: "MEMORY", online: true },
    { name: "WEB", online: true },
    { name: "AUTOMATION", online: true },
    { name: "CODING", online: true }
  ];
</script>

<SciFiPanel title="MODULES">
  <div class="module-list">
    {#each modules as mod}
      <div class="module-item">
        <span class="mod-icon"></span>
        <span class="mod-name">{mod.name}</span>
        <span class="mod-status" class:online={mod.online}>{mod.online ? "ONLINE" : "OFFLINE"}</span>
        <span class="mod-dot" class:online={mod.online} style="animation-delay: {Math.random() * 2}s"></span>
      </div>
    {/each}
  </div>
</SciFiPanel>

<style>
  .module-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .module-item {
    display: flex;
    align-items: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-dim);
  }
  .mod-icon {
    width: 16px;
    height: 16px;
    margin-right: 12px;
    background: var(--pri-gho);
    border-radius: 4px;
  }
  .mod-name {
    flex: 1;
    color: var(--text);
    font-weight: 500;
  }
  .mod-status {
    margin-right: 12px;
    font-weight: 600;
  }
  .mod-status.online {
    color: var(--green);
  }
  .mod-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #555;
  }
  .mod-dot.online {
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    animation: pulse 2s infinite ease-in-out;
  }
  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; box-shadow: 0 0 6px var(--green); }
    50% { transform: scale(1.3); opacity: 0.6; box-shadow: 0 0 12px var(--green); }
  }
</style>
