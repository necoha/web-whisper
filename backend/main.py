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

import gradio as gr
import numpy as np
from typing import Optional, Tuple

# Import platform-specific GPU detection
from patch_gpu import auto_engine_detailed

def get_transcription_engine():
    """Initialize the appropriate transcription engine based on platform."""
    try:
        return auto_engine_detailed()
    except Exception as e:
        print(f"Error initializing transcription engine: {e}")
        sys.exit(1)

# Global transcription engine
transcription_engine = get_transcription_engine()

def transcribe_audio(
    audio_file: Optional[str] = None,
    microphone_audio: Optional[Tuple[int, np.ndarray]] = None,
    language: str = "auto",
    word_timestamps: bool = True,
    save_output: bool = True,
    output_format: str = "json"
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
        # Transcribe using the platform-optimized engine
        language_param = None if language == "auto" else language
        result = transcription_engine(
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
        info_text = f"Detected language: {detected_lang} (confidence: {lang_prob:.2f})"
        
        # Save output if requested
        if save_output:
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            
            # Save transcription
            with open(output_dir / "transcription.txt", "w", encoding="utf-8") as f:
                f.write(transcription_text)
            
            # Save timestamps
            if output_format.lower() == "json":
                with open(output_dir / "timestamps.json", "w", encoding="utf-8") as f:
                    f.write(timestamps_json)
            elif output_format.lower() == "srt":
                srt_content = convert_to_srt(timestamps_data if 'timestamps_data' in locals() else [])
                with open(output_dir / "timestamps.srt", "w", encoding="utf-8") as f:
                    f.write(srt_content)
            
            print(f"Output saved to {output_dir}")
        
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
                output_format
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
                ["examples/coffe_break_example.mp3", "auto", True, True, "json"]
            ] if Path("examples/coffe_break_example.mp3").exists() else [],
            inputs=[audio_file, language, word_timestamps, save_output, output_format],
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