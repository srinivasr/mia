<script lang="ts">
  import SciFiPanel from "./SciFiPanel.svelte";
  import { onMount } from "svelte";

  let temperature: string = "--";
  let condition: string = "LOADING";
  let humidity: string = "--";
  let wind: string = "--";
  let location: string = "SEARCHING...";

  onMount(async () => {
    try {
      const res = await fetch("https://wttr.in/?format=j1");
      const data = await res.json();
      const current = data?.current_condition?.[0];
      if (current) {
        temperature = current.temp_C;
        condition = current.weatherDesc?.[0]?.value?.toUpperCase() || "UNKNOWN";
        humidity = current.humidity;
        wind = current.windspeedKmph;
      }
      
      const area = data?.nearest_area?.[0];
      if (area && area.areaName?.[0]?.value) {
        location = area.areaName[0].value.toUpperCase();
      }
    } catch (err) {
      console.error("Failed to fetch weather:", err);
      temperature = "--";
      condition = "UNAVAILABLE";
      humidity = "--";
      wind = "--";
      location = "UNKNOWN";
    }
  });
</script>

<SciFiPanel title="WEATHER">
  <div class="weather-layout">
    <div class="main-temp">
      <span class="temp-val">{temperature}</span><span class="temp-unit">°C</span>
    </div>
    <div class="weather-details">
      <div class="w-row"><span class="w-label">LOC</span> <span class="w-val">{location}</span></div>
      <div class="w-row"><span class="w-label">COND</span> <span class="w-val">{condition}</span></div>
      <div class="w-row"><span class="w-label">HUMIDITY</span> <span class="w-val">{humidity}%</span></div>
      <div class="w-row"><span class="w-label">WIND</span> <span class="w-val">{wind} KM/H</span></div>
    </div>
  </div>
</SciFiPanel>

<style>
  .weather-layout {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .main-temp {
    display: flex;
    align-items: baseline;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
  }
  .temp-val {
    font-size: 2.5rem;
    font-weight: 300;
  }
  .temp-unit {
    font-size: 1rem;
    color: var(--pri);
    margin-left: 4px;
  }
  .weather-details {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
  }
  .w-row {
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding-bottom: 2px;
  }
  .w-label {
    color: var(--text-dim);
  }
  .w-val {
    color: var(--text);
  }
</style>
