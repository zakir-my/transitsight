#!/bin/bash
# TransitSight tunnel watchdog with auto-reconnect
# Notifies stderr on each new URL so we can capture it

LOG="$HOME/.hermes/logs/transitsight-tunnel.log"
mkdir -p "$(dirname "$LOG")"

echo "$(date): TransitSight tunnel watchdog starting..." >> "$LOG"

while true; do
    echo "$(date): Connecting tunnel..." >> "$LOG"
    ssh -o StrictHostKeyChecking=no \
        -o ServerAliveInterval=10 \
        -o ServerAliveCountMax=6 \
        -o ExitOnForwardFailure=yes \
        -o TCPKeepAlive=yes \
        -o ConnectionAttempts=5 \
        -R 80:localhost:8000 \
        nokey@localhost.run 2>&1 | while read line; do
            echo "$line" >> "$LOG"
            # If it contains a tunnel URL, log it prominently
            if [[ "$line" == *".lhr.life"* ]] && [[ "$line" == *"https://"* ]]; then
                URL=$(echo "$line" | grep -oP 'https://[a-zA-Z0-9-]+\.lhr\.life')
                echo "=== NEW TUNNEL URL: $URL ===" >> "$LOG"
                echo "=== $(date) ===" >> "$LOG"
            fi
        done
    echo "$(date): Tunnel disconnected. Reconnecting in 5s..." >> "$LOG"
    sleep 5
done
