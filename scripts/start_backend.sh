#!/bin/bash
# VOXACLE backend service launcher (fully detached, survives shell exit)
cd /home/z/my-project
mkdir -p backend

# stop existing instance
pkill -f "uvicorn backend.main" 2>/dev/null
sleep 1

setsid nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 3030 >> backend/api.log 2>&1 < /dev/null &
echo "VOXACLE backend launched, PID $!"
