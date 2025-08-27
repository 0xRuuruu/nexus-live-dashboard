# Nexus Live Jobs Dashboard

Flask + Chart.js dashboard for monitoring Nexus job assignment and proof completion.

## Run

\`\`\`bash
pip3 install -r requirements.txt --user
python3 app.py
\`\`\`

Logs are read from `~/.nexus/logs/nexus.log`.
Use `tee -a ~/.nexus/logs/nexus.log` to store logs while running `nexus-network`.
