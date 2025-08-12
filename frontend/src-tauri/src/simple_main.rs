// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Clone)]
struct ServerInfo {
    url: String,
    port: u16,
    status: String,
}

#[tauri::command]
async fn start_whisper_server() -> Result<ServerInfo, String> {
    // For testing, return a mock server info
    Ok(ServerInfo {
        url: "http://localhost:7860".to_string(),
        port: 7860,
        status: "running".to_string(),
    })
}

#[tauri::command]
async fn get_server_info() -> Result<Option<ServerInfo>, String> {
    Ok(None)
}

#[tauri::command]
async fn open_whisper_gui(app: tauri::AppHandle) -> Result<(), String> {
    // For testing, just return success
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            start_whisper_server,
            get_server_info,
            open_whisper_gui
        ])
        .setup(|app| {
            #[cfg(desktop)]
            {
                use tauri::Manager;
                let window = app.get_webview_window("main").unwrap();
                
                // Set window title
                window.set_title("Web Whisper - Speech to Text").unwrap();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}