import json
import base64
import io
import tempfile
import subprocess
import librosa
import soundfile as sf
from pathlib import Path
import torch
import os
import time

def handler(event):
    """
    RunPod Serverless handler for Demucs processing
    """
    try:
        # Get input data
        input_data = event.get("input", {})
        audio_base64 = input_data.get("audio_data")
        filename = input_data.get("filename", "audio.wav")
        
        if not audio_base64:
            return {"error": "No audio data provided"}
        
        print(f"🎵 Processing {filename} with Serverless Demucs...")
        start_time = time.time()
        
        # Decode audio data
        audio_bytes = base64.b64decode(audio_base64)
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / filename
            output_dir = temp_path / "processed"
            output_dir.mkdir(exist_ok=True)
            
            # Save input audio
            with open(input_file, 'wb') as f:
                f.write(audio_bytes)
            
            # Check GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"🚀 Using device: {device}")
            
            # Run Demucs separation
            cmd = [
                'python', '-m', 'demucs.separate',
                '--two-stems=vocals',
                '--device', device,
                '--out', str(temp_path),
                str(input_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            
            if result.returncode != 0:
                return {"error": f"Demucs failed: {result.stderr}"}
            
            # Find output files
            audio_stem = input_file.stem
            demucs_output = temp_path / "htdemucs" / audio_stem
            vocals_file = demucs_output / "vocals.wav"
            
            if not vocals_file.exists():
                return {"error": "Vocals file not created"}
            
            # Convert to desired format and encode
            audio_data, sr = librosa.load(str(vocals_file), sr=16000)
            
            # Save as WAV and encode to base64
            output_buffer = io.BytesIO()
            sf.write(output_buffer, audio_data, 16000, format='WAV')
            output_base64 = base64.b64encode(output_buffer.getvalue()).decode()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "vocals_data": output_base64,
                "processing_time": processing_time,
                "filename": f"{audio_stem}_vocals.wav",
                "sample_rate": 16000,
                "duration": len(audio_data) / 16000,
                "device_used": device
            }
            
    except Exception as e:
        return {"error": str(e)}

# For local testing
if __name__ == "__main__":
    print("🧪 Testing Serverless Handler...")
    
    # Test with a small audio file
    test_event = {
        "input": {
            "audio_data": "",  # Base64 encoded audio
            "filename": "test.wav"
        }
    }
    
    result = handler(test_event)
    print(f"Result: {result}")
