#!/bin/bash

echo "🚀 Starting QMS Deployment on 104.207.66.129..."

# 1. Update and install system dependencies
echo "📦 Installing system dependencies (Redis, Python venv, Git)..."
sudo apt update && sudo apt install -y redis-server git python3-venv python3-pip

# 2. Setup Redis
echo "⚙️  Ensuring Redis is running..."
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 3. Environment Setup
echo "📂 Setting up project directory..."
cd ~
if [ -d "QMS" ]; then
    echo "Updating existing QMS directory..."
    cd QMS && git pull
else
    git clone https://github.com/alaauddin/QMS.git
    cd QMS
fi

# 4. Python Environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "⚙️  Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Database and Cache Initialization
echo "🗄️  Running migrations..."
python manage.py migrate

echo "🔊 Warming up audio cache (100 tokens)..."
python manage.py warm_audio_cache --tokens 10 --counters 10

# 6. Deployment (Run in background)
echo "🚀 Starting QMS Server on port 8000..."
# Kill any existing process on port 8000 to avoid conflicts
fuser -k 8000/tcp || true

# Use nohup to keep it running
nohup python manage.py runserver 0.0.0.0:8088 > qms_server.log 2>&1 &

echo "------------------------------------------------"
echo "✅ DEPLOYMENT COMPLETE!"
echo "QMS is now running at http://104.207.66.129:8088"
echo "Check logs with: tail -f qms_server.log"
echo "------------------------------------------------"
