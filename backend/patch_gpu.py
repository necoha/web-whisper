# -*- coding: utf-8 -*-
import platform
import importlib

def auto_engine():
    """
    GPU auto-detection for cross-platform Whisper inference.
    - macOS/Apple Silicon: MLX backend with Metal GPU acceleration
    - Windows/NVIDIA: faster-whisper with CUDA acceleration
    """
    system = platform.system()
    machine = platform.machine()
    
    if system == "Darwin" and machine.startswith("arm"):
        # Apple Silicon macOS - Use MLX backend
        try:
            mlx = importlib.import_module("mlx_whisper")
            model_name = "mlx-community/whisper-large-v3-mlx"
            
            def transcribe_mlx(audio_file):
                result = mlx.transcribe(audio_file, path_or_hf_repo=model_name)
                return result["text"]
            
            print("Using MLX backend for Apple Silicon")
            return transcribe_mlx
            
        except ImportError:
            raise RuntimeError("MLX backend not available. Install with: pip install mlx-whisper==0.4.2")
    
    elif system == "Windows":
        # Windows - Use faster-whisper with CUDA
        try:
            from faster_whisper import WhisperModel
            
            # Initialize model with CUDA acceleration
            model = WhisperModel("large-v3", device="cuda", compute_type="float16")
            
            def transcribe_faster_whisper(audio_file):
                segments, info = model.transcribe(audio_file)
                return " ".join(segment.text for segment in segments)
            
            print("Using faster-whisper backend with CUDA")
            return transcribe_faster_whisper
            
        except ImportError:
            raise RuntimeError("faster-whisper not available. Install with: pip install faster-whisper")
        except Exception as e:
            # Fallback to CPU if CUDA not available
            model = WhisperModel("large-v3", device="cpu", compute_type="int8")
            
            def transcribe_cpu_fallback(audio_file):
                segments, info = model.transcribe(audio_file)
                return " ".join(segment.text for segment in segments)
            
            print(f"CUDA not available ({e}), falling back to CPU")
            return transcribe_cpu_fallback
    
    elif system == "Darwin" and not machine.startswith("arm"):
        # Intel macOS - Use faster-whisper as fallback
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("large-v3", device="cpu", compute_type="int8")
            
            def transcribe_intel_mac(audio_file):
                segments, info = model.transcribe(audio_file)
                return " ".join(segment.text for segment in segments)
            
            print("Using faster-whisper backend for Intel macOS")
            return transcribe_intel_mac
            
        except ImportError:
            raise RuntimeError("No suitable backend available for Intel macOS")
    
    else:
        # Linux or other platforms - Use faster-whisper
        try:
            from faster_whisper import WhisperModel
            # Try CUDA first, fallback to CPU
            try:
                model = WhisperModel("large-v3", device="cuda", compute_type="float16")
                device_info = "CUDA"
            except:
                model = WhisperModel("large-v3", device="cpu", compute_type="int8")
                device_info = "CPU"
            
            def transcribe_linux(audio_file):
                segments, info = model.transcribe(audio_file)
                return " ".join(segment.text for segment in segments)
            
            print(f"Using faster-whisper backend on {system} with {device_info}")
            return transcribe_linux
            
        except ImportError:
            raise RuntimeError(f"No suitable backend available for {system}")

def get_gpu_info():
    """Get GPU information for display in the UI"""
    system = platform.system()
    machine = platform.machine()
    
    if system == "Darwin" and machine.startswith("arm"):
        try:
            import mlx.core as mx
            # Test MLX availability
            test_array = mx.array([1.0])
            return "🚀 Apple Silicon (MLX + Metal GPU) - 高速処理"
        except ImportError:
            return "⚠️ Apple Silicon detected, but MLX not available"
        except Exception:
            return "⚠️ Apple Silicon detected, but MLX initialization failed"
    elif system == "Darwin":
        return "💻 Intel Mac (CPU処理)"
    else:
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                return f"🎮 NVIDIA GPU ({gpu_name}) - CUDA加速"
            else:
                return "💻 CPU処理 (CUDA利用不可)"
        except ImportError:
            return "💻 CPU処理 (PyTorch未インストール)"

# Enhanced version with more detailed transcription options
def auto_engine_detailed():
    """
    Enhanced GPU auto-detection with detailed transcription options including timestamps.
    """
    system = platform.system()
    machine = platform.machine()
    
    if system == "Darwin" and machine.startswith("arm"):
        # Apple Silicon macOS - Use MLX backend
        try:
            mlx = importlib.import_module("mlx_whisper")
            model_name = "mlx-community/whisper-large-v3-mlx"
            
            def transcribe_mlx_detailed(audio_file, **kwargs):
                result = mlx.transcribe(
                    audio_file, 
                    path_or_hf_repo=model_name,
                    word_timestamps=kwargs.get('word_timestamps', True),
                    language=kwargs.get('language', None)
                )
                return result
            
            print("Using MLX backend for Apple Silicon with detailed output")
            return transcribe_mlx_detailed
            
        except ImportError:
            raise RuntimeError("MLX backend not available. Install with: pip install mlx-whisper==0.4.2")
    
    else:
        # Other platforms - Use faster-whisper
        try:
            from faster_whisper import WhisperModel
            
            # Auto-detect best device
            device = "cuda" if system == "Windows" else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            try:
                model = WhisperModel("large-v3", device=device, compute_type=compute_type)
            except:
                # Fallback to CPU
                model = WhisperModel("large-v3", device="cpu", compute_type="int8")
                device = "cpu"
            
            def transcribe_faster_whisper_detailed(audio_file, **kwargs):
                segments, info = model.transcribe(
                    audio_file,
                    language=kwargs.get('language', None),
                    word_timestamps=kwargs.get('word_timestamps', True)
                )
                
                result = {
                    "text": " ".join(segment.text for segment in segments),
                    "segments": [
                        {
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text,
                            "words": getattr(segment, 'words', [])
                        }
                        for segment in segments
                    ],
                    "language": info.language,
                    "language_probability": info.language_probability
                }
                return result
            
            print(f"Using faster-whisper backend on {system} with {device.upper()}")
            return transcribe_faster_whisper_detailed
            
        except ImportError:
            raise RuntimeError("faster-whisper not available")

if __name__ == "__main__":
    # Test the auto-detection
    try:
        engine = auto_engine()
        print("Engine initialized successfully!")
        
        detailed_engine = auto_engine_detailed()
        print("Detailed engine initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing engines: {e}")