# RunPod Serverless Demucs Handler
FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel

# Set working directory
WORKDIR /

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_minimal.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy handler
COPY handler.py .

# Set the handler
CMD python -u handler.py