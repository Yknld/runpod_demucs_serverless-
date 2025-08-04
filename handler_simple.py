import runpod
import json
import base64
import tempfile
import subprocess
import time
from pathlib import Path

def handler(job):
    """
    Simple working RunPod handler for Demucs
    """
    try:
        input_data = job.get("input", {})
        
        # Test mode
        if input_data.get("test"):
            return {
                "success": True,
                "message": f"Handler working! Test: {input_data['test']}",
                "status": "ready"
            }
        
        # Audio processing mode
        audio_base64 = input_data.get("audio_data")
        
        if not audio_base64:
            return {
                "error": "No audio data provided",
                "help": "Send base64 encoded audio in 'audio_data' field"
            }
        
        print(f"🎵 Processing audio with Demucs...")
        start_time = time.time()
        
        # Decode audio
        audio_bytes = base64.b64decode(audio_base64)
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "input.wav"
            
            # Save input
            with open(input_file, 'wb') as f:
                f.write(audio_bytes)
            
            print(f"📁 Saved input: {input_file} ({len(audio_bytes)} bytes)")
            
            # Run Demucs
            cmd = [
                'python', '-m', 'demucs.separate',
                '--two-stems=vocals',
                '--mp3',
                '--mp3-bitrate', '192',
                str(input_file)
            ]
            
            print(f"🚀 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                return {
                    "error": f"Demucs failed: {result.stderr}",
                    "stdout": result.stdout[:500],
                    "command": ' '.join(cmd)
                }
            
            # Find vocals file
            separated_dir = temp_path / "separated" / "htdemucs" / "input"
            vocals_file = separated_dir / "vocals.mp3"
            
            if not vocals_file.exists():
                # Try alternative path
                vocals_file = separated_dir / "vocals.wav"
                
            if not vocals_file.exists():
                return {
                    "error": "Vocals file not found",
                    "stdout": result.stdout,
                    "directory_contents": str(list(temp_path.rglob("*")))
                }
            
            # Read and encode vocals
            with open(vocals_file, 'rb') as f:
                vocals_bytes = f.read()
            
            vocals_base64 = base64.b64encode(vocals_bytes).decode()
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "vocals_data": vocals_base64,
                "processing_time": processing_time,
                "input_size": len(audio_bytes),
                "output_size": len(vocals_bytes),
                "format": vocals_file.suffix
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }

# Start RunPod handler
runpod.serverless.start({"handler": handler})
