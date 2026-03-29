FROM python:3.10-slim

# Install C++ compiler for high performance
RUN apt-get update && apt-get install -y \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Optimized Compilation
RUN g++ -O3 prime.cpp -o PRIME -pthread

# Set permissions
RUN chmod +x PRIME

# Run the Bot
CMD ["python", "PRIME.py"]