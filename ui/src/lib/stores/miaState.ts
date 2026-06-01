import { writable } from 'svelte/store';

export type MiaState = 
    | 'Idle' 
    | 'Listening' 
    | 'Thinking' 
    | 'Speaking' 
    | 'Searching' 
    | 'ExecutingTool' 
    | 'Interrupted' 
    | 'VisionAnalyzing' 
    | 'Disconnected' 
    | 'Error';

export const currentState = writable<MiaState>('Idle');
export const transcript = writable<string>('');
export const latencyMs = writable<number>(0);
export const isConnected = writable<boolean>(false);
