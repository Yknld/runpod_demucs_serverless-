import runpod
import json
import base64
import io
import tempfile
import subprocess
import time
import os
from pathlib import Path

def process_audio(job):
    """
    Simplified Demucs processing for RunPod Serverless
    """
    try:
        # Get input data
        input_data = job.get("input", {})
        audio_base64 = input_data.get("audio_data")
        filename = input_data.get("filename", "audio.wav")
        
        if not audio_base64:
            return {"error": "No audio data provided"}
        
        print(f"🎵 Processing {filename} with Demucs...")
        start_time = time.time()
        
        # Decode audio data
        audio_bytes = base64.b64decode(audio_base64)
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / filename
            
            # Save input audio
            with open(input_file, 'wb') as f:
                f.write(audio_bytes)
            
            print(f"🚀 Starting Demucs separation...")
            
            # Run Demucs separation (simplified)
            cmd = [
                'python', '-m', 'demucs.separate',
                '--two-stems=vocals',
                '--mp3',
                '--mp3-bitrate', '192',
                '--out', str(temp_path),
                str(input_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                return {"error": f"Demucs failed: {result.stderr}"}
            
            # Find output files
            audio_stem = input_file.stem
            demucs_output = temp_path / "htdemucs" / audio_stem
            vocals_file = demucs_output / "vocals.mp3"
            
            if not vocals_file.exists():
                return {"error": "Vocals file not created"}
            
            # Read and encode output
            with open(vocals_file, 'rb') as f:
                output_data = f.read()
                output_base64 = base64.b64encode(output_data).decode()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "vocals_data": output_base64,
                "processing_time": processing_time,
                "filename": f"{audio_stem}_vocals.mp3",
                "device_used": "gpu" if os.getenv('CUDA_VISIBLE_DEVICES') else "cpu"
            }
            
    except Exception as e:
        return {"error": str(e)}

# RunPod serverless handler
runpod.serverless.start({"handler": process_audio})