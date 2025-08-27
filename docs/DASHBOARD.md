# Nexus Live Dashboard Server

Install:
  python3 -m pip install --user flask

Run:
  python3 app.py

Log path:
  ~/.nexus/logs/nexus.log

Notes:
  - Keep the nexus-network process running and pipe logs to the file above.
  - Open http://localhost:5000 to view the dashboard.

## Advanced Usage

### Auto-refresh Dashboard
- Auto-refresh every 10 seconds.
- Displays:
  - Assigned and completed (last 1h / 24h)
  - Jobs per 5-minute buckets (last 2h)

### Customize Port & Log Path
Run the dashboard with custom settings:
    PORT=8080 LOG_PATH=$HOME/.nexus/logs/nexus.log ./run.sh

### Generate Logs Automatically
Make sure nexus-network writes logs:
    mkdir -p ~/.nexus/logs
    stdbuf -oL nexus-network start --node-id <NODE_ID> --max-threads 12 | tee -a ~/.nexus/logs/nexus.log

### View Stats Manually
Tail useful events:
    tail -f ~/.nexus/logs/nexus.log | grep --line-buffered -E "Job assigned|Proof completed"

