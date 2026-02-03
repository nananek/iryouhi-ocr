# OCR Server with CUDA support
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Pre-download YomiToku models (optional but recommended for faster startup)
# RUN python -c "from yomitoku import OCR; OCR(visualize=False, device='cpu')"

EXPOSE 8000

# Environment variables
ENV OCR_DEVICE=cuda
ENV MAX_CONCURRENT_OCR=1

CMD ["uvicorn", "ocr_server:app", "--host", "0.0.0.0", "--port", "8000"]
