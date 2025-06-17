# Use .NET 6 base image
FROM mcr.microsoft.com/dotnet/runtime:6.0

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv curl git \
    && rm -rf /var/lib/apt/lists/*

# Set default Python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set workdir and copy files
WORKDIR /app
COPY . /app

# Install Python requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python3", "main.py"]
