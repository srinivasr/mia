import { writable } from 'svelte/store';
import { listen } from '@tauri-apps/api/event';

export const rmsLevel = writable<number>(0);
export const vadActive = writable<boolean>(false);
export const captureRunning = writable<boolean>(false);

export const audioBars = writable<number[]>(new Array(28).fill(0));

export interface AudioDeviceInfo {
    id: string;
    name: string;
    is_default: boolean;
}

export const audioDevices = writable<{
    inputs: AudioDeviceInfo[];
    outputs: AudioDeviceInfo[];
}>({ inputs: [], outputs: [] });

export const sttResult = writable<string>("");

// only wire up tauri events if we're running inside the native window
if (window.__TAURI_INTERNALS__) {
    listen<{ rms: number }>('audio://rms', (event) => {
        // the rust side sends rms in [0.0, 1.0] but the visualizer
        // expects 0-255. scale it here so the components don't have to.
        rmsLevel.set(event.payload.rms * 255);
    });

    listen<{ active: boolean }>('audio://vad', (event) => {
        vadActive.set(event.payload.active);
    });

    listen<{ text: string }>('audio://stt_result', (event) => {
        sttResult.set(event.payload.text);
    });

    listen<{ bars: number[] }>('audio://bars', (event) => {
        audioBars.set(event.payload.bars.map(v => Math.min(255, Math.round(v * 255))));
    });
}
