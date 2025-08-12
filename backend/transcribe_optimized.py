# -*- coding: utf-8 -*-
"""
Optimized transcription module that integrates GPU auto-detection with whisper-gui.
This module provides a drop-in replacement for whisperx with platform-optimized backends.
"""

import os
import sys
import time
import json
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

# Import our GPU auto-detection
from patch_gpu import auto_engine_detailed

# Import utilities from original whisper-gui
try:
    from scripts.utils import *  # noqa: F403
    from scripts.config_io import read_config_value, write_config_value
    MSG = {}  # Will be populated from original utils
except ImportError:
    # Fallback messages if not available
    MSG = {
        "inputs_received": "Inputs received",
        "loading_model": "Loading optimized model...",
        "starting_transcription": "Starting transcription...",
        "transcription_complete": "Transcription completed",
        "align_lang_not_supported": "Alignment not supported for language: {}"
    }

# Global variables for model management
g_optimized_engine = None
g_current_backend = None

def get_optimized_engine():
    """
    Get or initialize the optimized transcription engine.
    """
    global g_optimized_engine, g_current_backend
    
    if g_optimized_engine is None:
        try:
            print(MSG.get("loading_model", "Loading optimized model..."))
            g_optimized_engine = auto_engine_detailed()
            # Detect which backend is being used
            import platform
            if platform.system() == "Darwin" and platform.machine().startswith("arm"):
                g_current_backend = "mlx"
            else:
                g_current_backend = "faster-whisper"
            print(f"Optimized engine loaded with {g_current_backend} backend")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize optimized engine: {e}")
    
    return g_optimized_engine

def transcribe_optimized(
        audio_path: str,
        micro_audio: tuple = None,
        language: str = "auto",
        batch_size: int = 16,
        chunk_size: int = 30,
        save_root: Optional[str] = None,
        save_audio: bool = False,
        save_transcription: bool = True,
        save_alignments: bool = False,
        save_in_subfolder: bool = False,
        preserve_name: bool = True,
        alignments_format: str = "json",
        **kwargs
) -> Tuple[str, str, str, str]:
    """
    Optimized transcription using platform-specific backends.
    
    Returns:
        Tuple[str, str, str, str]: (transcription_text, alignment_text, save_path, elapsed_time)
    """
    
    print(MSG.get("inputs_received", "Inputs received"))
    
    # Create temp directory
    temp_dir = os.path.join("temp", str(int(time.time())))
    os.makedirs(temp_dir, exist_ok=True)
    
    # Setup save directory
    save_dir = None
    if save_audio or save_transcription or save_alignments:
        if save_root and save_root.strip():
            save_root_dir = save_root
        else:
            save_root_dir = "outputs"
        
        if save_in_subfolder:
            save_dir = create_save_folder(save_root_dir) if 'create_save_folder' in globals() else save_root_dir
        else:
            save_dir = save_root_dir
    
    try:
        # Load and prepare audio
        if micro_audio and micro_audio[1] is not None:
            # Handle microphone input
            audio_file = os.path.join(temp_dir, "microphone_input.wav")
            # Save microphone audio (this would need proper implementation)
            audio_input = audio_file
        else:
            audio_input = audio_path
        
        if not os.path.exists(audio_input):
            raise FileNotFoundError(f"Audio file not found: {audio_input}")
        
        # Save audio if requested
        if save_audio and save_dir:
            import shutil
            audio_name = os.path.basename(audio_input)
            if preserve_name:
                save_audio_name = audio_name
            else:
                save_audio_name = "audio" + os.path.splitext(audio_name)[1]
            shutil.copy2(audio_input, os.path.join(save_dir, save_audio_name))
        
        # Get optimized engine
        engine = get_optimized_engine()
        
        # Prepare language parameter
        lang_param = None if language == "auto" else language
        
        # Transcribe
        print(MSG.get("starting_transcription", "Starting transcription..."))
        start_time = time.time()
        
        result = engine(
            audio_input,
            language=lang_param,
            word_timestamps=save_alignments
        )
        
        transcription_time = time.time() - start_time
        
        # Extract transcription text
        if isinstance(result, dict):
            if "text" in result:
                transcription_text = result["text"].strip()
            else:
                # Fallback for different result formats
                transcription_text = str(result).strip()
        else:
            transcription_text = str(result).strip()
        
        print(MSG.get("transcription_complete", "Transcription completed"))
        print(f"Transcription completed in {transcription_time:.2f} seconds")
        
        # Save transcription
        save_path = ""
        if save_transcription and save_dir:
            if preserve_name and audio_path:
                base_name = os.path.splitext(os.path.basename(audio_path))[0]
                transcription_filename = f"{base_name}_transcription.txt"
            else:
                transcription_filename = "transcription.txt"
            
            transcription_path = os.path.join(save_dir, transcription_filename)
            with open(transcription_path, 'w', encoding='utf-8') as f:
                f.write(transcription_text)
            save_path = transcription_path
        
        # Handle alignments
        alignment_text = ""
        if save_alignments and isinstance(result, dict) and "segments" in result:
            alignment_data = {
                "segments": result["segments"],
                "language": result.get("language", "unknown"),
                "language_probability": result.get("language_probability", 0.0)
            }
            
            if alignments_format == "json":
                alignment_text = json.dumps(alignment_data, indent=2, ensure_ascii=False)
                if save_dir:
                    if preserve_name and audio_path:
                        base_name = os.path.splitext(os.path.basename(audio_path))[0]
                        alignment_filename = f"{base_name}_alignments.json"
                    else:
                        alignment_filename = "alignments.json"
                    
                    alignment_path = os.path.join(save_dir, alignment_filename)
                    with open(alignment_path, 'w', encoding='utf-8') as f:
                        f.write(alignment_text)
            
            elif alignments_format == "srt":
                alignment_text = segments_to_srt(result["segments"])
                if save_dir:
                    if preserve_name and audio_path:
                        base_name = os.path.splitext(os.path.basename(audio_path))[0]
                        srt_filename = f"{base_name}_alignments.srt"
                    else:
                        srt_filename = "alignments.srt"
                    
                    srt_path = os.path.join(save_dir, srt_filename)
                    with open(srt_path, 'w', encoding='utf-8') as f:
                        f.write(alignment_text)
        
        elapsed_time = f"{transcription_time:.2f}s"
        
        # Cleanup temp directory
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass
        
        return transcription_text, alignment_text, save_path, elapsed_time
        
    except Exception as e:
        # Cleanup on error
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass
        raise e

def segments_to_srt(segments: List[Dict]) -> str:
    """
    Convert segments to SRT format.
    """
    srt_content = []
    for i, segment in enumerate(segments, 1):
        start_time = format_time_srt(segment.get('start', 0))
        end_time = format_time_srt(segment.get('end', 0))
        text = segment.get('text', '').strip()
        
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")  # Empty line between entries
    
    return "\n".join(srt_content)

def format_time_srt(seconds: float) -> str:
    """
    Format time in seconds to SRT time format (HH:MM:SS,mmm).
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def create_save_folder(root_dir: str) -> str:
    """
    Create a timestamped save folder.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(root_dir, f"transcription_{timestamp}")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir

def release_optimized_engine():
    """
    Release the optimized engine to free memory.
    """
    global g_optimized_engine, g_current_backend
    g_optimized_engine = None
    g_current_backend = None
    print("Optimized engine released")

if __name__ == "__main__":
    # Test the optimized transcription
    print("Testing optimized transcription engine...")
    try:
        engine = get_optimized_engine()
        print("Engine initialized successfully!")
        print(f"Using backend: {g_current_backend}")
    except Exception as e:
        print(f"Error: {e}")