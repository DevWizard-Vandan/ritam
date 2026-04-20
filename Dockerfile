FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download FinBERT at build time so it's baked into the image.
# This prevents a ~400MB download on every cold start which causes
# OOM / 503 errors on Render's free tier.
RUN python - <<'EOF'
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
path = "models/finbert"
os.makedirs(path, exist_ok=True)
AutoTokenizer.from_pretrained("ProsusAI/finbert").save_pretrained(path)
AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").save_pretrained(path)
print("FinBERT baked into image at", path)
EOF

# Default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.server:app", \
     "--host", "0.0.0.0", "--port", "8000"]
