FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install public Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ⚠️  vnstock_data (paid library) must be installed here.
# Option 1: If you have a local wheel file, copy and install it:
# COPY vnstock_data-*.whl .
# RUN pip install --no-cache-dir vnstock_data-*.whl

# Option 2: If your Vnstock licence allows pip install from a private index,
# add the pip install command here.

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
