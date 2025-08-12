// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, State, Emitter};
use tauri_plugin_shell::ShellExt;
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use std::env;
use std::path::PathBuf;
use std::process::Command;
use std::net::{TcpListener, SocketAddrV4, Ipv4Addr};
use std::io::{BufRead, BufReader};

#[derive(Debug, Deserialize, Serialize, Clone)]
struct ServerInfo {
    url: String,
    port: u16,
    status: String,
}

type ServerState = Arc<Mutex<Option<ServerInfo>>>;
type ProcessState = Arc<Mutex<Option<u32>>>; // Store process ID

#[tauri::command]
async fn start_whisper_server(
    app: tauri::AppHandle,
    state: State<'_, ServerState>,
    process_state: State<'_, ProcessState>,
) -> Result<ServerInfo, String> {
    // First check if server is already running
    let client = reqwest::Client::new();
    let default_url = "http://127.0.0.1:7860";
    
    if let Ok(response) = client.get(default_url).send().await {
        if response.status().is_success() {
            println!("Found existing server at {}", default_url);
            let server_info = ServerInfo {
                url: default_url.to_string(),
                port: 7860,
                status: "running".to_string(),
            };
            
            // Store server info in state
            {
                let mut state_guard = state.lock().unwrap();
                *state_guard = Some(server_info.clone());
            }
            
            return Ok(server_info);
        }
    }
    let _shell = app.shell(); // Keep for potential future use
    let app_handle = app.clone();
    
    // Resolve app binary directory (works in dev and bundled app)
    let current_exe = env::current_exe().map_err(|e| format!("Failed to get current exe: {}", e))?;
    let app_dir = current_exe.parent().unwrap();
    
    // Look for Python backend - try multiple possible locations
    let backend_dir = if let Some(parent) = app_dir.parent() {
        if let Some(grandparent) = parent.parent() {
            let candidate1 = grandparent.join("backend");
            let candidate2 = grandparent.join("../backend");
            let candidate3 = PathBuf::from("/Users/ktsutsum/Documents/claude/web-whisper/backend");
            
            if candidate1.join("main.py").exists() {
                candidate1
            } else if candidate2.join("main.py").exists() {
                candidate2
            } else {
                candidate3
            }
        } else {
            PathBuf::from("/Users/ktsutsum/Documents/claude/web-whisper/backend")
        }
    } else {
        PathBuf::from("/Users/ktsutsum/Documents/claude/web-whisper/backend")
    };
    
    let main_py = backend_dir.join("main.py");
    
    println!("Backend directory: {:?}", backend_dir);
    println!("Main.py path: {:?}", main_py);
    
    println!("Trying to start Python server: {:?}", main_py);

    // Choose a port: prefer 7860 if free, otherwise allocate a free port
    let desired_port: u16 = 7860;
    let chosen_port: u16 = match TcpListener::bind(SocketAddrV4::new(Ipv4Addr::LOCALHOST, desired_port)) {
        Ok(listener) => {
            let port = listener.local_addr().unwrap().port();
            // drop to free it for the server
            drop(listener);
            port
        },
        Err(_) => {
            // find an ephemeral free port
            let tmp = TcpListener::bind(SocketAddrV4::new(Ipv4Addr::LOCALHOST, 0))
                .map_err(|e| format!("Failed to acquire a free port: {}", e))?;
            let port = tmp.local_addr().unwrap().port();
            drop(tmp);
            println!("Port {} in use; selected free port {}", desired_port, port);
            port
        }
    };
    
    // Get Python executable with cross-platform support
    let python_cmd = if cfg!(target_os = "windows") {
        // Windows: Try multiple Python locations
        let candidates = vec![
            "python".to_string(),
            "py".to_string(),
            "python3".to_string(),
            format!("{}\\AppData\\Local\\Programs\\Python\\Python311\\python.exe", env::var("USERPROFILE").unwrap_or_default()),
            format!("{}\\AppData\\Local\\Programs\\Python\\Python312\\python.exe", env::var("USERPROFILE").unwrap_or_default()),
            "C:\\Python311\\python.exe".to_string(),
            "C:\\Python312\\python.exe".to_string(),
        ];
        
        let mut found_python = "python".to_string();
        for candidate in candidates {
            if candidate.contains(":\\") {
                // Full path - check if exists
                if std::path::Path::new(&candidate).exists() {
                    println!("Using Python: {}", candidate);
                    found_python = candidate;
                    break;
                }
            } else {
                // Command - try to execute
                if Command::new(&candidate).arg("--version").output().is_ok() {
                    println!("Using Python: {}", candidate);
                    found_python = candidate;
                    break;
                }
            }
        }
        
        if found_python == "python" {
            println!("No Python found, using default 'python'");
        }
        found_python
    } else {
        // macOS/Linux: Try to detect pyenv Python path
        let home_dir = env::var("HOME").unwrap_or_else(|_| "/Users/ktsutsum".to_string());
        let pyenv_python_web = format!("{}/.pyenv/versions/web-whisper/bin/python", home_dir);
        let pyenv_python_gui = format!("{}/.pyenv/versions/whisper-gui/bin/python", home_dir);
        let pyenv_python_web3 = format!("{}/.pyenv/versions/web-whisper/bin/python3", home_dir);
        let pyenv_python_gui3 = format!("{}/.pyenv/versions/whisper-gui/bin/python3", home_dir);
        
        // Check if pyenv Python exists, prioritize web-whisper environment
        if std::path::Path::new(&pyenv_python_web).exists() {
            println!("Using pyenv Python (web-whisper): {}", pyenv_python_web);
            pyenv_python_web
        } else if std::path::Path::new(&pyenv_python_web3).exists() {
            println!("Using pyenv Python (web-whisper python3): {}", pyenv_python_web3);
            pyenv_python_web3
        } else if std::path::Path::new(&pyenv_python_gui).exists() {
            println!("Using pyenv Python (whisper-gui): {}", pyenv_python_gui);
            pyenv_python_gui
        } else if std::path::Path::new(&pyenv_python_gui3).exists() {
            println!("Using pyenv Python (whisper-gui python3): {}", pyenv_python_gui3);
            pyenv_python_gui3
        } else {
            println!("Pyenv Python not found, using system python3");
            "python3".to_string()
        }
    };
    
    // Use standard library Command instead of Tauri shell for better process control
    // Try sidecar first (bundled PyInstaller binary), then fall back to Python
    let sidecar_candidates = if cfg!(target_os = "windows") {
        vec![
            app_dir.join("whisper-gui-core.exe"),
            app_dir.join("whisper-gui-core-simple.exe"),
        ]
    } else {
        vec![
            app_dir.join("whisper-gui-core"),
            app_dir.join("whisper-gui-core-simple"),
        ]
    };

    let mut child: std::process::Child;
    if let Some(bin_path) = sidecar_candidates.into_iter().find(|p| p.exists()) {
        println!("Launching bundled sidecar: {:?}", bin_path);
        let _ = app_handle.emit("engine-progress", serde_json::json!({"percent": 5, "message": "Launching sidecar"}));
        let mut cmd = Command::new(bin_path);
        cmd.args(&["--server.name", "127.0.0.1", "--server.port", &chosen_port.to_string()])
            .current_dir(&backend_dir)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped());
        child = cmd.spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;
    } else {
        println!("No bundled sidecar found; falling back to Python: {}", python_cmd);
        let _ = app_handle.emit("engine-progress", serde_json::json!({"percent": 5, "message": "Launching Python backend"}));
        let mut cmd = Command::new(python_cmd.clone());
        cmd.args(&[main_py.to_str().unwrap(), "--server.name", "127.0.0.1", "--server.port", &chosen_port.to_string()])
            .current_dir(&backend_dir)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped());
        child = cmd.spawn()
            .map_err(|e| format!("Failed to spawn Python process: {}", e))?;
    }
        
    let process_id = child.id();
    
    // Store process ID
    {
        let mut process_guard = process_state.lock().unwrap();
        *process_guard = Some(process_id);
    }
    
    println!("Started Python server with PID: {}", process_id);
    let server_url = format!("http://127.0.0.1:{}", chosen_port);

    // Stream child stdout/stderr to help diagnostics
    if let Some(stdout) = child.stdout.take() {
        let reader = BufReader::new(stdout);
        let app_for_logs = app_handle.clone();
        std::thread::spawn(move || {
            for line in reader.lines().flatten() {
                println!("[sidecar stdout] {}", line);
                let _ = app_for_logs.emit("engine-log", serde_json::json!({"stream": "stdout", "line": line}));
            }
        });
    }
    if let Some(stderr) = child.stderr.take() {
        let reader = BufReader::new(stderr);
        let app_for_logs = app_handle.clone();
        std::thread::spawn(move || {
            for line in reader.lines().flatten() {
                eprintln!("[sidecar stderr] {}", line);
                let _ = app_for_logs.emit("engine-log", serde_json::json!({"stream": "stderr", "line": line}));
            }
        });
    }
    
    // Try to connect to verify server is running
    let client = reqwest::Client::new();
    let mut ready = false;
    for attempt in 1..=30 { // up to ~30 * 300ms = 9s
        match client.get(&server_url).send().await {
            Ok(response) if response.status().is_success() => {
                println!("Server is responding at {}", server_url);
                ready = true;
                let _ = app_handle.emit("engine-progress", serde_json::json!({"percent": 100, "message": "Engine ready"}));
                break;
            }
            _ => {
                // Optionally check if process already exited
                // We cannot directly check without the child handle; rely on retries
                if attempt % 10 == 0 {
                    println!("Still waiting for server startup... (attempt {})", attempt);
                }
                let percent = 10 + attempt * 3; // 13..100 cap below
                let p = if percent > 95 { 95 } else { percent };
                let _ = app_handle.emit("engine-progress", serde_json::json!({"percent": p, "message": "Starting engine..."}));
                tokio::time::sleep(std::time::Duration::from_millis(300)).await;
            }
        }
    }
    if !ready {
        return Err(format!("Server failed to start or is not responding at {}", server_url));
    }
    
    let server_info = ServerInfo {
        url: server_url.clone(),
        port: chosen_port,
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
async fn open_whisper_gui(_app: tauri::AppHandle, state: State<'_, ServerState>) -> Result<(), String> {
    let server_info = {
        let state_guard = state.lock().unwrap();
        state_guard.clone()
    };
    
    if let Some(info) = server_info {
        // Use shell to open the URL in default browser
        if cfg!(target_os = "macos") {
            std::process::Command::new("open")
                .arg(&info.url)
                .spawn()
                .map_err(|e| format!("Failed to open URL: {}", e))?;
        } else if cfg!(target_os = "windows") {
            std::process::Command::new("cmd")
                .args(["/c", "start", &info.url])
                .spawn()
                .map_err(|e| format!("Failed to open URL: {}", e))?;
        } else {
            std::process::Command::new("xdg-open")
                .arg(&info.url)
                .spawn()
                .map_err(|e| format!("Failed to open URL: {}", e))?;
        }
        Ok(())
    } else {
        Err("Whisper server is not running".to_string())
    }
}

#[tauri::command]
async fn save_temp_file(
    file_data: Vec<u8>,
    file_name: String
) -> Result<String, String> {
    use std::io::Write;
    
    // Create temp directory if it doesn't exist
    let temp_dir = std::env::temp_dir().join("web-whisper");
    if !temp_dir.exists() {
        std::fs::create_dir_all(&temp_dir)
            .map_err(|e| format!("Failed to create temp directory: {}", e))?;
    }
    
    // Generate unique filename to avoid conflicts
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let temp_file_path = temp_dir.join(format!("{}_{}", timestamp, file_name));
    
    // Write file data to temp location
    let mut file = std::fs::File::create(&temp_file_path)
        .map_err(|e| format!("Failed to create temp file: {}", e))?;
    file.write_all(&file_data)
        .map_err(|e| format!("Failed to write temp file: {}", e))?;
    
    Ok(temp_file_path.to_string_lossy().to_string())
}

#[tauri::command]
async fn transcribe_audio(
    file_path: String,
    state: State<'_, ServerState>,
    process_state: State<'_, ProcessState>
) -> Result<String, String> {
    // Simply call Python script directly
    let current_exe = env::current_exe().map_err(|e| format!("Failed to get current exe: {}", e))?;
    let app_dir = current_exe.parent().unwrap();
    
    // Find backend directory
    let backend_dir = if let Some(parent) = app_dir.parent() {
        if let Some(grandparent) = parent.parent() {
            let candidate1 = grandparent.join("backend");
            let candidate2 = grandparent.join("../backend");
            
            // Cross-platform fallback paths
            let candidate3 = if cfg!(target_os = "windows") {
                // Windows: Try common locations
                let user_profile = env::var("USERPROFILE").unwrap_or_default();
                PathBuf::from(format!("{}\\Documents\\web-whisper\\backend", user_profile))
            } else {
                // macOS/Linux: Current development path
                PathBuf::from("/Users/ktsutsum/Documents/claude/web-whisper/backend")
            };
            
            if candidate1.join("transcribe_simple.py").exists() {
                candidate1
            } else if candidate2.join("transcribe_simple.py").exists() {
                candidate2
            } else {
                candidate3
            }
        } else {
            // Cross-platform fallback
            if cfg!(target_os = "windows") {
                let user_profile = env::var("USERPROFILE").unwrap_or_default();
                PathBuf::from(format!("{}\\Documents\\web-whisper\\backend", user_profile))
            } else {
                PathBuf::from("/Users/ktsutsum/Documents/claude/web-whisper/backend")
            }
        }
    } else {
        // Cross-platform fallback
        if cfg!(target_os = "windows") {
            let user_profile = env::var("USERPROFILE").unwrap_or_default();
            PathBuf::from(format!("{}\\Documents\\web-whisper\\backend", user_profile))
        } else {
            PathBuf::from("/Users/ktsutsum/Documents/claude/web-whisper/backend")
        }
    };
    
    let transcribe_script = backend_dir.join("transcribe_simple.py");
    
    // Get Python executable
    let home_dir = env::var("HOME").unwrap_or_else(|_| "/Users/ktsutsum".to_string());
    let pyenv_python_web = format!("{}/.pyenv/versions/web-whisper/bin/python", home_dir);
    let python_cmd = if std::path::Path::new(&pyenv_python_web).exists() {
        pyenv_python_web
    } else {
        "python3".to_string()
    };
    
    println!("Using Python: {}", python_cmd);
    println!("Transcribing file: {}", file_path);
    
    // Call transcription script directly with proper environment
    let mut cmd = Command::new(&python_cmd);
    cmd.args(&[
            transcribe_script.to_str().unwrap(),
            &file_path,
            "--language", "auto",
            "--format", "text"
        ])
        .current_dir(&backend_dir);
    
    // Add ffmpeg path to environment - cross platform
    let current_path = env::var("PATH").unwrap_or_default();
    let ffmpeg_paths = if cfg!(target_os = "windows") {
        vec![
            "C:\\ffmpeg\\bin",
            "C:\\Program Files\\FFmpeg\\bin",
            "C:\\Program Files (x86)\\FFmpeg\\bin",
        ]
    } else {
        vec![
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin"
        ]
    };
    
    let mut new_path = current_path.clone();
    let separator = if cfg!(target_os = "windows") { ";" } else { ":" };
    
    for ffmpeg_path in ffmpeg_paths {
        if !new_path.contains(ffmpeg_path) {
            new_path = format!("{}{}{}", ffmpeg_path, separator, new_path);
        }
    }
    
    cmd.env("PATH", new_path);
    
    let output = cmd.output()
        .map_err(|e| format!("Failed to execute transcription: {}", e))?;
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Transcription failed: {}", stderr));
    }
    
    let result = String::from_utf8_lossy(&output.stdout);
    Ok(result.trim().to_string())
}

#[tauri::command]
async fn stop_whisper_server(process_state: State<'_, ProcessState>) -> Result<(), String> {
    let process_id = {
        let process_guard = process_state.lock().unwrap();
        process_guard.clone()
    };
    
    if let Some(pid) = process_id {
        println!("Stopping Python server with PID: {}", pid);
        
        // Kill the process
        if cfg!(target_os = "windows") {
            Command::new("taskkill")
                .args(&["/F", "/PID", &pid.to_string()])
                .output()
                .map_err(|e| format!("Failed to kill process: {}", e))?;
        } else {
            Command::new("kill")
                .args(&["-9", &pid.to_string()])
                .output()
                .map_err(|e| format!("Failed to kill process: {}", e))?;
        }
        
        // Clear process state
        {
            let mut process_guard = process_state.lock().unwrap();
            *process_guard = None;
        }
        
        println!("Python server stopped");
        Ok(())
    } else {
        Err("No server process found".to_string())
    }
}

fn main() {
    let server_state: ServerState = Arc::new(Mutex::new(None));
    let process_state: ProcessState = Arc::new(Mutex::new(None));
    
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(server_state)
        .manage(process_state.clone())
        .invoke_handler(tauri::generate_handler![
            start_whisper_server,
            get_server_info,
            open_whisper_gui,
            save_temp_file,
            transcribe_audio,
            stop_whisper_server
        ])
        .setup({
            let process_state_clone = process_state.clone();
            move |app| {
                #[cfg(desktop)]
                {
                    use tauri::Manager;
                    let window = app.get_webview_window("main").unwrap();
                    
                    // Set window title
                    window.set_title("Web Whisper - Speech to Text").unwrap();
                    
                    // Set up close handler to cleanup server process
                    let process_state_for_close = process_state_clone.clone();
                    window.on_window_event(move |event| {
                        if let tauri::WindowEvent::CloseRequested { .. } = event {
                            // Stop the server process before closing
                            if let Some(pid) = {
                                let guard = process_state_for_close.lock().unwrap();
                                guard.clone()
                            } {
                                println!("Cleaning up Python server process: {}", pid);
                                if cfg!(target_os = "windows") {
                                    let _ = Command::new("taskkill")
                                        .args(&["/F", "/PID", &pid.to_string()])
                                        .output();
                                } else {
                                    let _ = Command::new("kill")
                                        .args(&["-9", &pid.to_string()])
                                        .output();
                                }
                            }
                        }
                    });
                }
                Ok(())
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
