#!/bin/bash
# Auto-reconnecting SSH tunnel for TransitSight
while true; do
    echo "[$(date)] Starting tunnel..."
    ssh -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=15 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -R 80:localhost:8000 \
        nokey@localhost.run 2>&1
    echo "[$(date)] Tunnel disconnected. Reconnecting in 3s..."
    sleep 3
done
