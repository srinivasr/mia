// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::sync::Mutex;
use sysinfo::System;

#[derive(Serialize, Clone)]
struct SystemStats {
    cpu_percent: f32,
    ram_percent: f32,
    ram_used_gb: f32,
    ram_total_gb: f32,
    uptime_seconds: u64,
    gpu_percent: Option<f32>,
    vram_percent: Option<f32>,
    vram_used_gb: Option<f32>,
    vram_total_gb: Option<f32>,
    gpu_name: Option<String>,
}

#[tauri::command]
fn get_system_stats(sys_state: tauri::State<'_, Mutex<System>>) -> SystemStats {
    let mut sys = sys_state.lock().unwrap();
    sys.refresh_cpu();
    sys.refresh_memory();
    
    let cpu_percent = sys.global_cpu_info().cpu_usage();
    
    let total_mem = sys.total_memory() as f32; // in bytes
    let used_mem = sys.used_memory() as f32;
    let ram_percent = if total_mem > 0.0 { (used_mem / total_mem) * 100.0 } else { 0.0 };
    let ram_used_gb = used_mem / (1024.0 * 1024.0 * 1024.0);
    let ram_total_gb = total_mem / (1024.0 * 1024.0 * 1024.0);
    let uptime_seconds = System::uptime();

    // Try to get GPU stats via nvidia-smi
    let mut gpu_percent = None;
    let mut vram_percent = None;
    let mut vram_used_gb = None;
    let mut vram_total_gb = None;
    let mut gpu_name = None;

    if let Ok(output) = std::process::Command::new("nvidia-smi")
        .args(&["--query-gpu=utilization.gpu,memory.used,memory.total,name", "--format=csv,noheader,nounits"])
        .output() 
    {
        if output.status.success() {
            if let Ok(stdout) = String::from_utf8(output.stdout) {
                let parts: Vec<&str> = stdout.trim().split(", ").collect();
                if parts.len() >= 4 {
                    if let Ok(gpu) = parts[0].parse::<f32>() { gpu_percent = Some(gpu); }
                    if let (Ok(used), Ok(total)) = (parts[1].parse::<f32>(), parts[2].parse::<f32>()) {
                        vram_used_gb = Some(used / 1024.0);
                        vram_total_gb = Some(total / 1024.0);
                        if total > 0.0 {
                            vram_percent = Some((used / total) * 100.0);
                        }
                    }
                    gpu_name = Some(parts[3].to_string());
                }
            }
        }
    }

    SystemStats {
        cpu_percent,
        ram_percent,
        ram_used_gb,
        ram_total_gb,
        uptime_seconds,
        gpu_percent,
        vram_percent,
        vram_used_gb,
        vram_total_gb,
        gpu_name,
    }
}

#[tauri::command]
fn open_url(url: String) {
    let _ = std::process::Command::new("xdg-open").arg(&url).spawn();
}

fn main() {
    // Enable GPU-accelerated compositing for smooth animations.
    std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "0");
    std::env::set_var("WEBKIT_FORCE_COMPOSITING_MODE", "1");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(Mutex::new(System::new_all()))
        .invoke_handler(tauri::generate_handler![get_system_stats, open_url])
        .setup(|_app| {
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
