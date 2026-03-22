# Use .NET 8 LTS base image (required by pythonnet/stock-indicators)
FROM mcr.microsoft.com/dotnet/runtime:8.0

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv curl git \
    && rm -rf /var/lib/apt/lists/*

# Set default Python
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Set workdir and copy files
WORKDIR /app
COPY . /app

# Install Python requirements
RUN pip install --no-cache-dir --upgrade pip --break-system-packages \
    && pip install --no-cache-dir -r requirements.txt --break-system-packages

CMD ["python3", "main.py"]
