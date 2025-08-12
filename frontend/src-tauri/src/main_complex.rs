// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, State};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Clone)]
struct ServerInfo {
    url: String,
    port: u16,
    status: String,
}

type ServerState = Arc<Mutex<Option<ServerInfo>>>;

#[tauri::command]
async fn start_whisper_server(
    app: tauri::AppHandle,
    state: State<'_, ServerState>,
) -> Result<ServerInfo, String> {
    let shell = app.shell();
    
    // Use the simple executable name for now
    let executable_name = "whisper-gui-core-simple";
    
    // Start the process using Command
    use std::env;
    use std::path::PathBuf;
    
    // Get the executable path relative to the app bundle
    let current_exe = env::current_exe().map_err(|e| format!("Failed to get current exe: {}", e))?;
    let app_dir = current_exe.parent().unwrap();
    let executable_path = app_dir.join(executable_name);
    
    println!("Trying to start: {:?}", executable_path);
    
    let (mut rx, child) = shell
        .command(&executable_path)
        .args(&["--server.port", "0"]) // Use port 0 for auto-assignment
        .spawn()
        .map_err(|e| format!("Failed to spawn process: {}", e))?;
    
    // Listen for output to get the server URL
    let mut server_url = String::new();
    let mut port = 0u16;
    
    // Wait for server startup message
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(line) => {
                let line_str = String::from_utf8_lossy(&line);
                
                // Look for Gradio server URL (format: "Running on http://127.0.0.1:PORT")
                if let Some(url_start) = line_str.find("Running on ") {
                    let url_part = &line_str[url_start + 11..];
                    if let Some(url_end) = url_part.find('\n') {
                        server_url = url_part[..url_end].trim().to_string();
                        
                        // Extract port number
                        if let Some(port_start) = server_url.rfind(':') {
                            if let Ok(parsed_port) = server_url[port_start + 1..].parse::<u16>() {
                                port = parsed_port;
                            }
                        }
                        break;
                    }
                }
                
                println!("Server stdout: {}", line_str);
            }
            CommandEvent::Stderr(line) => {
                let line_str = String::from_utf8_lossy(&line);
                println!("Server stderr: {}", line_str);
                
                // Check for error conditions
                if line_str.contains("error") || line_str.contains("Error") {
                    return Err(format!("Server startup error: {}", line_str));
                }
            }
            CommandEvent::Terminated(payload) => {
                return Err(format!("Server terminated unexpectedly: {:?}", payload));
            }
            _ => {}
        }
    }
    
    if server_url.is_empty() {
        return Err("Failed to get server URL from output".to_string());
    }
    
    let server_info = ServerInfo {
        url: server_url.clone(),
        port,
        status: "running".to_string(),
    };
    
    // Store server info in state
    {
        let mut state_guard = state.lock().unwrap();
        *state_guard = Some(server_info.clone());
    }
    
    println!("Whisper server started at: {}", server_url);
    Ok(server_info)
}

#[tauri::command]
async fn get_server_info(state: State<'_, ServerState>) -> Result<Option<ServerInfo>, String> {
    let state_guard = state.lock().unwrap();
    Ok(state_guard.clone())
}

#[tauri::command]
async fn open_whisper_gui(app: tauri::AppHandle, state: State<'_, ServerState>) -> Result<(), String> {
    let server_info = {
        let state_guard = state.lock().unwrap();
        state_guard.clone()
    };
    
    if let Some(info) = server_info {
        // Get the main window
        if let Some(window) = app.get_webview_window("main") {
            // Navigate to the Whisper GUI URL
            window
                .navigate(tauri::Url::parse(&info.url).map_err(|e| format!("Invalid URL: {}", e))?)
                .map_err(|e| format!("Failed to navigate: {}", e))?;
        }
        Ok(())
    } else {
        Err("Whisper server is not running".to_string())
    }
}

fn main() {
    let server_state: ServerState = Arc::new(Mutex::new(None));
    
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(server_state)
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