#!/usr/bin/env python3
"""
Simple command-line transcription script for Web Whisper
"""

import sys
import argparse
from pathlib import Path
from patch_gpu import auto_engine_detailed

def transcribe_file(file_path: str, language: str = "auto", output_format: str = "text"):
    """Transcribe an audio file and return the result."""
    try:
        # Initialize the transcription engine
        print(f"Loading transcription engine...", file=sys.stderr)
        engine = auto_engine_detailed()
        
        print(f"Transcribing: {file_path}", file=sys.stderr)
        
        # Call the transcription function
        print(f"Engine type: {type(engine)}", file=sys.stderr)
        print(f"Engine methods: {[attr for attr in dir(engine) if 'transcribe' in attr.lower()]}", file=sys.stderr)
        
        # Try different transcription methods
        if callable(engine):
            # Function returned by auto_engine_detailed
            result = engine(file_path, language=language if language != "auto" else None)
            if isinstance(result, dict):
                return result.get('text', '').strip()
            else:
                return str(result).strip()
        elif hasattr(engine, 'transcribe'):
            # MLX backend
            result = engine.transcribe(file_path, language=language if language != "auto" else None)
            if isinstance(result, dict):
                return result.get('text', result.get('segments', str(result)))
            else:
                return str(result)
        elif hasattr(engine, 'transcribe_audio'):
            # faster-whisper backend
            segments, info = engine.transcribe_audio(file_path, language=language if language != "auto" else None)
            text = ' '.join(segment.text for segment in segments)
            return text
        else:
            available_methods = [attr for attr in dir(engine) if not attr.startswith('_')]
            return f"Error: Unknown engine type. Available methods: {available_methods}"
            
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        return f"Error: {e}"

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file")
    parser.add_argument("file_path", help="Path to audio file")
    parser.add_argument("--language", default="auto", help="Language code (default: auto)")
    parser.add_argument("--format", default="text", help="Output format (default: text)")
    
    args = parser.parse_args()
    
    if not Path(args.file_path).exists():
        print(f"Error: File not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)
    
    result = transcribe_file(args.file_path, args.language, args.format)
    print(result)

if __name__ == "__main__":
    main()