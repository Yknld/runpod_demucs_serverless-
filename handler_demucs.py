import runpod
import json
import base64
import io
import tempfile
import subprocess
import time
import os
from pathlib import Path

def handler(job):
    """
    Production Demucs handler for RunPod Serverless
    """
    try:
        input_data = job.get("input", {})
        
        # Test mode
        if input_data.get("test"):
            return {
                "success": True,
                "message": f"Demucs handler ready! Test: {input_data['test']}",
                "gpu_available": str(os.environ.get('CUDA_VISIBLE_DEVICES', 'unknown')),
                "status": "ready_for_audio"
            }
        
        # Audio processing mode
        audio_base64 = input_data.get("audio_data")
        filename = input_data.get("filename", "audio.wav")
        
        if not audio_base64:
            return {"error": "No audio data provided. Send base64 encoded audio in 'audio_data' field."}
        
        print(f"🎵 Processing {filename} with GPU Demucs...")
        start_time = time.time()
        
        # Decode audio data
        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            return {"error": f"Invalid base64 audio data: {str(e)}"}
        
        # Create temporary files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / filename
            
            # Save input audio
            with open(input_file, 'wb') as f:
                f.write(audio_bytes)
            
            print(f"🚀 Starting Demucs vocal separation...")
            
            # Run Demucs separation
            cmd = [
                'python', '-m', 'demucs.separate',
                '--two-stems=vocals',
                '--mp3',
                '--mp3-bitrate', '192',
                '--out', str(temp_path),
                str(input_file)
            ]
            
            # Run with timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                return {
                    "error": f"Demucs processing failed: {result.stderr}",
                    "stdout": result.stdout,
                    "command": " ".join(cmd)
                }
            
            # Find output files
            audio_stem = input_file.stem
            demucs_output = temp_path / "htdemucs" / audio_stem
            vocals_file = demucs_output / "vocals.mp3"
            
            if not vocals_file.exists():
                # List what files were created for debugging
                created_files = []
                if demucs_output.exists():
                    created_files = [str(f) for f in demucs_output.rglob("*")]
                return {
                    "error": "Vocals file not created by Demucs",
                    "demucs_output_dir": str(demucs_output),
                    "created_files": created_files,
                    "stdout": result.stdout
                }
            
            # Read and encode output
            with open(vocals_file, 'rb') as f:
                output_data = f.read()
                output_base64 = base64.b64encode(output_data).decode()
            
            processing_time = time.time() - start_time
            
            print(f"✅ Vocal separation completed in {processing_time:.2f}s")
            
            return {
                "success": True,
                "vocals_data": output_base64,
                "processing_time": processing_time,
                "filename": f"{audio_stem}_vocals.mp3",
                "original_size": len(audio_bytes),
                "vocals_size": len(output_data),
                "gpu_used": str(os.environ.get('CUDA_VISIBLE_DEVICES', 'unknown')),
                "demucs_model": "htdemucs"
            }
            
    except subprocess.TimeoutExpired:
        return {"error": "Processing timeout (10 minutes). Audio file too large."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# Start RunPod serverless
runpod.serverless.start({"handler": handler})