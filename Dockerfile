FROM --platform=linux/amd64 python:3.13.3

WORKDIR /app

# Copy requirements.txt early to leverage Docker caching for dependencies
COPY requirements.txt ./

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else (your scripts, models, etc.)
COPY . ./


CMD ["python", "process_pdfs.py"]
