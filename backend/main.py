#!/usr/bin/env python3
"""
Cross-platform Whisper GUI with automatic GPU detection.
- macOS Apple Silicon: MLX backend with Metal GPU acceleration
- Windows/NVIDIA: faster-whisper with CUDA acceleration  
- Linux/Other: faster-whisper with auto-detection
"""

import os
import sys
import platform
import argparse
import tempfile
import shutil
from pathlib import Path

# Ensure FFmpeg is in PATH
def setup_ffmpeg_path():
    """Add common FFmpeg installation paths to PATH."""
    current_path = os.environ.get('PATH', '')
    
    if platform.system() == "Darwin":  # macOS
        ffmpeg_paths = [
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin"
        ]
    elif platform.system() == "Windows":
        ffmpeg_paths = [
            "C:\\ffmpeg\\bin",
            "C:\\Program Files\\FFmpeg\\bin",
            "C:\\Program Files (x86)\\FFmpeg\\bin"
        ]
    else:  # Linux
        ffmpeg_paths = [
            "/usr/local/bin",
            "/usr/bin"
        ]
    
    separator = ";" if platform.system() == "Windows" else ":"
    new_paths = []
    
    for path in ffmpeg_paths:
        if os.path.exists(path) and path not in current_path:
            new_paths.append(path)
    
    if new_paths:
        os.environ['PATH'] = separator.join(new_paths) + separator + current_path
        print(f"Added FFmpeg paths to PATH: {', '.join(new_paths)}")

# Setup FFmpeg path early
setup_ffmpeg_path()

# Test FFmpeg availability
def test_ffmpeg():
    """Test if FFmpeg is available."""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg is available")
            return True
        else:
            print("❌ FFmpeg test failed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ FFmpeg not found: {e}")
        return False

# Test FFmpeg on startup
test_ffmpeg()

import gradio as gr
import numpy as np
from typing import Optional, Tuple

# Import platform-specific GPU detection
from patch_gpu import auto_engine_detailed, auto_engine, get_available_models

def get_transcription_engine(model_choice="🎯 High Accuracy"):
    """Initialize the appropriate transcription engine based on platform and model."""
    try:
        return auto_engine_detailed(model_choice)
    except Exception as e:
        print(f"Error initializing transcription engine: {e}")
        sys.exit(1)

# Default transcription engine - will be updated when model is selected
transcription_engine = get_transcription_engine()

def transcribe_audio(
    audio_file: Optional[str] = None,
    microphone_audio: Optional[Tuple[int, np.ndarray]] = None,
    language: str = "auto",
    word_timestamps: bool = True,
    save_output: bool = True,
    output_format: str = "json",
    model_choice: str = "🎯 High Accuracy"
) -> Tuple[str, str, str]:
    """
    Transcribe audio using the platform-optimized engine.
    
    Returns:
        - transcription_text: Plain text transcription
        - timestamps_json: JSON with detailed timestamps
        - info_text: Processing information
    """
    
    # Handle audio input
    if audio_file is not None:
        audio_path = audio_file
    elif microphone_audio is not None:
        # Save microphone input to temp file
        sample_rate, audio_data = microphone_audio
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        
        # Convert numpy array to audio file
        import scipy.io.wavfile
        scipy.io.wavfile.write(temp_file.name, sample_rate, audio_data)
        audio_path = temp_file.name
    else:
        return "No audio input provided", "", ""
    
    try:
        # Get the appropriate engine for the selected model
        current_engine = get_transcription_engine(model_choice)
        
        # Transcribe using the selected model engine
        language_param = None if language == "auto" else language
        result = current_engine(
            audio_path,
            language=language_param,
            word_timestamps=word_timestamps
        )
        
        # Extract results
        transcription_text = result.get("text", "")
        
        # Format timestamps
        if "segments" in result and result["segments"]:
            timestamps_data = []
            for segment in result["segments"]:
                segment_data = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip()
                }
                if "words" in segment and segment["words"]:
                    segment_data["words"] = [
                        {
                            "start": word.start if hasattr(word, 'start') else word.get('start', 0),
                            "end": word.end if hasattr(word, 'end') else word.get('end', 0),
                            "word": word.word if hasattr(word, 'word') else word.get('word', '')
                        }
                        for word in segment["words"]
                    ]
                timestamps_data.append(segment_data)
            
            import json
            timestamps_json = json.dumps(timestamps_data, indent=2, ensure_ascii=False)
        else:
            timestamps_json = "No timestamp data available"
        
        # Processing info
        detected_lang = result.get("language", "unknown")
        lang_prob = result.get("language_probability", 0.0)
        
        # Get base filename for info display
        if audio_file is not None:
            base_filename = Path(audio_file).stem
            input_info = f"Input: {Path(audio_file).name}"
        elif 'temp_file' in locals() and temp_file:
            base_filename = Path(temp_file.name).stem
            input_info = "Input: Microphone recording"
        else:
            base_filename = "transcription"
            input_info = "Input: Unknown source"
        
        info_text = f"{input_info}\nDetected language: {detected_lang} (confidence: {lang_prob:.2f})\nOutput file: {base_filename}.txt"
        
        # Save output if requested
        if save_output:
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            
            # Get base filename from input file
            if audio_file is not None:
                base_filename = Path(audio_file).stem
            elif 'temp_file' in locals() and temp_file:
                # Extract original name from temp file
                base_filename = Path(temp_file.name).stem
            else:
                base_filename = "transcription"
            
            # Save transcription with original filename
            transcription_file = f"{base_filename}.txt"
            with open(output_dir / transcription_file, "w", encoding="utf-8") as f:
                f.write(transcription_text)
            
            # Save timestamps with original filename
            if output_format.lower() == "json":
                timestamps_file = f"{base_filename}_timestamps.json"
                with open(output_dir / timestamps_file, "w", encoding="utf-8") as f:
                    f.write(timestamps_json)
            elif output_format.lower() == "srt":
                timestamps_file = f"{base_filename}.srt"
                srt_content = convert_to_srt(timestamps_data if 'timestamps_data' in locals() else [])
                with open(output_dir / timestamps_file, "w", encoding="utf-8") as f:
                    f.write(srt_content)
            
            print(f"Output saved to {output_dir}/{transcription_file}")
        
        return transcription_text, timestamps_json, info_text
        
    except Exception as e:
        error_msg = f"Transcription error: {str(e)}"
        print(error_msg)
        return error_msg, "", error_msg
    
    finally:
        # Clean up temp file if created
        if 'temp_file' in locals():
            try:
                os.unlink(temp_file.name)
            except:
                pass

def convert_to_srt(segments_data):
    """Convert timestamp data to SRT format."""
    srt_content = ""
    for i, segment in enumerate(segments_data, 1):
        start_time = format_srt_time(segment["start"])
        end_time = format_srt_time(segment["end"])
        text = segment["text"].strip()
        
        srt_content += f"{i}\n"
        srt_content += f"{start_time} --> {end_time}\n"
        srt_content += f"{text}\n\n"
    
    return srt_content

def format_srt_time(seconds):
    """Format seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

# Detect system info for UI
def get_system_info():
    """Get system information for display."""
    system = platform.system()
    machine = platform.machine()
    
    if system == "Darwin" and machine.startswith("arm"):
        backend_info = "🍎 Apple Silicon (MLX + Metal GPU)"
    elif system == "Windows":
        backend_info = "🪟 Windows (faster-whisper + CUDA)"
    elif system == "Darwin":
        backend_info = "🍎 Intel macOS (faster-whisper CPU)"
    else:
        backend_info = f"🐧 {system} (faster-whisper)"
    
    return backend_info

# Create Gradio interface
def create_interface():
    system_info = get_system_info()
    
    with gr.Blocks(
        title="Web Whisper - Cross-platform Speech to Text",
        theme=gr.themes.Soft()
    ) as demo:
        
        gr.Markdown(f"""
        # 🎙️ Web Whisper - Speech to Text
        
        **Backend:** {system_info}  
        **Model:** Whisper Large-v3
        
        Upload an audio file or record directly to get accurate transcriptions with timestamps.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                # Audio input options
                with gr.Group():
                    gr.Markdown("### 📁 Audio Input")
                    audio_file = gr.File(
                        label="Upload Audio/Video File",
                        file_types=[".mp3", ".wav", ".m4a", ".mp4", ".avi", ".mov", ".mkv", ".webm"],
                        type="filepath"
                    )
                    
                    microphone = gr.Audio(
                        label="Record from Microphone",
                        sources=["microphone"],
                        type="numpy"
                    )
                
                # Transcription options
                with gr.Group():
                    gr.Markdown("### ⚙️ Options")
                    model_choice = gr.Dropdown(
                        choices=list(get_available_models().keys()),
                        value="🎯 High Accuracy",
                        label="Model Selection",
                        info="Choose model based on accuracy vs speed preference"
                    )
                    
                    language = gr.Dropdown(
                        choices=["auto", "en", "es", "fr", "de", "it", "ja", "zh", "pt", "ru", "ko"],
                        value="auto",
                        label="Language",
                        info="Select 'auto' for automatic detection"
                    )
                    
                    word_timestamps = gr.Checkbox(
                        value=True,
                        label="Word-level timestamps",
                        info="Generate detailed word-level timing information"
                    )
                    
                    save_output = gr.Checkbox(
                        value=True,
                        label="Save output files",
                        info="Save transcription and timestamps to outputs folder"
                    )
                    
                    output_format = gr.Radio(
                        choices=["json", "srt"],
                        value="json",
                        label="Timestamp format",
                        info="Choose output format for timestamps"
                    )
                
                transcribe_btn = gr.Button(
                    "🚀 Transcribe",
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=2):
                # Results
                with gr.Group():
                    gr.Markdown("### 📝 Transcription")
                    transcription_output = gr.Textbox(
                        label="Text",
                        lines=8,
                        max_lines=20,
                        show_copy_button=True
                    )
                
                with gr.Group():
                    gr.Markdown("### ⏱️ Timestamps")
                    timestamps_output = gr.Textbox(
                        label="Detailed Timestamps",
                        lines=8,
                        max_lines=20,
                        show_copy_button=True
                    )
                
                info_output = gr.Textbox(
                    label="Processing Info",
                    lines=1,
                    max_lines=3
                )
        
        # Connect the transcription function
        transcribe_btn.click(
            fn=transcribe_audio,
            inputs=[
                audio_file,
                microphone, 
                language,
                word_timestamps,
                save_output,
                output_format,
                model_choice
            ],
            outputs=[
                transcription_output,
                timestamps_output,
                info_output
            ]
        )
        
        # Add examples
        gr.Examples(
            examples=[
                ["examples/coffe_break_example.mp3", "auto", True, True, "json", "🎯 High Accuracy"]
            ] if Path("examples/coffe_break_example.mp3").exists() else [],
            inputs=[audio_file, language, word_timestamps, save_output, output_format, model_choice],
            outputs=[transcription_output, timestamps_output, info_output],
            fn=transcribe_audio,
            cache_examples=False
        )
    
    return demo

def main():
    parser = argparse.ArgumentParser(description="Web Whisper - Cross-platform Speech to Text")
    
    parser.add_argument(
        "--autolaunch",
        action="store_true",
        default=False,
        help="Automatically open the web interface in browser"
    )
    
    parser.add_argument(
        "--share",
        action="store_true", 
        default=False,
        help="Create a public Gradio link"
    )
    
    parser.add_argument(
        "--server.name",
        dest="server_name",
        default="127.0.0.1",
        help="Server bind address"
    )
    
    parser.add_argument(
        "--server.port", 
        dest="server_port",
        type=int,
        default=7860,
        help="Server port"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    Path("outputs").mkdir(exist_ok=True)
    
    # Check if running in Docker
    is_docker = os.path.exists('/.dockerenv')
    server_name = "0.0.0.0" if is_docker else args.server_name
    
    print(f"🚀 Starting Web Whisper server on {server_name}:{args.server_port}")
    print(f"🎯 Backend: {get_system_info()}")
    
    # Create and launch interface
    demo = create_interface()
    
    demo.launch(
        server_name=server_name,
        server_port=args.server_port,
        inbrowser=args.autolaunch,
        share=args.share
    )

if __name__ == "__main__":
    main()