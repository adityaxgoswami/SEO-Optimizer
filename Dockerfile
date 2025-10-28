# Base image with Python and Playwright support
FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (if needed by analyzer)
RUN python -m nltk.downloader stopwords punkt averaged_perceptron_tagger punkt_tab averaged_perceptron_tagger_eng

# Copy all files into the container
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Command to run the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
