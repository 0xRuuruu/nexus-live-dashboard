from flask import Flask, jsonify, Response, render_template_string, request
from datetime import datetime, timedelta
from collections import defaultdict, deque
import os, re, time

# ===== Config (env overridable) =====
LOG_PATH      = os.path.expanduser(os.getenv("LOG_PATH", "~/.nexus/logs/nexus.log"))
PORT          = int(os.getenv("PORT", "5000"))
MAX_LINES     = int(os.getenv("MAX_LINES", "50000"))
BUCKET_MIN    = int(os.getenv("BUCKET_MIN", "5"))
WINDOW_HOURS  = float(os.getenv("WINDOW_HOURS", "2"))

ASSIGNED_PAT   = re.compile(r"job assigned", re.IGNORECASE)
COMPLETED_PAT  = re.compile(r"(proof completed|completed proof|job completed)", re.IGNORECASE)
TIMESTAMP_PAT  = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Nexus Live Jobs Dashboard</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:20px}
    h1{margin:0 0 4px}.meta{color:#666;margin-bottom:12px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
    .card{border:1px solid #e5e7eb;border-radius:12px;padding:12px;box-shadow:0 1px 6px rgba(0,0,0,.05)}
    .num{font-size:28px;font-weight:700}
    canvas{width:100%;height:320px}
    code{background:#f1f5f9;padding:2px 6px;border-radius:6px}
    .ok{color:#15803d}.bad{color:#b91c1c}
  </style>
</head>
<body>
  <h1>Nexus Live Jobs</h1>
  <div class="meta">
    Auto-refresh every <code id="rf">10s</code> · Source: <code id="lp"></code>
  </div>

  <div class="grid" style="margin:12px 0">
    <div class="card"><div>Assigned (last 1h)</div><div id="a1" class="num">—</div></div>
    <div class="card"><div>Completed (last 1h)</div><div id="c1" class="num">—</div></div>
    <div class="card"><div>Assigned (last 24h)</div><div id="a24" class="num">—</div></div>
    <div class="card"><div>Completed (last 24h)</div><div id="c24" class="num">—</div></div>
  </div>

  <div class="card">
    <div><strong>Jobs per {{bucket}} minutes (last {{window}}h)</strong></div>
    <canvas id="chart"></canvas>
    <div style="color:#64748b;font-size:12px;margin-top:6px">Blue=assigned · Green=completed</div>
  </div>

  <div class="card" style="margin-top:12px">
    <strong>Health</strong>
    <div id="health">Loading…</div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    let chart;

    async function loadConfig() {
      const r = await fetch('/config'); const j = await r.json();
      document.getElementById('lp').textContent = j.LOG_PATH;
      document.getElementById('rf').textContent = '10s';
    }

    async function refresh() {
      const r = await fetch('/stats'); const data = await r.json();
      a1.textContent = data.totals.assigned_1h;
      c1.textContent = data.totals.completed_1h;
      a24.textContent = data.totals.assigned_24h;
      c24.textContent = data.totals.completed_24h;

      const labels = data.series.labels;
      const aData  = data.series.assigned;
      const cData  = data.series.completed;

      if (!chart) {
        const ctx = document.getElementById('chart').getContext('2d');
        chart = new Chart(ctx,{
          type:'line',
          data:{ labels, datasets:[
            {label:'Assigned', data:aData, borderWidth:2, tension:.25},
            {label:'Completed', data:cData, borderWidth:2, tension:.25}
          ]},
          options:{ animation:false,responsive:true,maintainAspectRatio:false,
            elements:{point:{radius:0}}, scales:{y:{beginAtZero:true}} }
        });
      } else {
        chart.data.labels = labels;
        chart.data.datasets[0].data = aData;
        chart.data.datasets[1].data = cData;
        chart.update();
      }
    }

    async function pollHealth(){
      const r = await fetch('/health'); const h = await r.json();
      const ok = h.ok ? 'ok' : 'bad';
      health.innerHTML = \`<div>Log: <code>\${h.log_path}</code></div>
      <div>Exists: <span class="\${ok}">\${h.exists}</span> · Size: \${h.size_bytes} · Updated: \${h.mtime}</div>
      <div>Events ({{window}}h): \${h.events_in_window}</div>\`;
    }

    function startSSE(){
      const s = new EventSource('/events');
      s.onerror = ()=>{ s.close(); setTimeout(startSSE, 3000); };
    }

    loadConfig(); refresh(); pollHealth(); startSSE();
    setInterval(()=>{ refresh(); pollHealth(); }, 10000);
  </script>
</body>
</html>
"""

def parse_log(max_lines=MAX_LINES):
    if not os.path.exists(LOG_PATH):
        return []
    lines = deque(maxlen=max_lines)
    with open(LOG_PATH, "r", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if line:
                lines.append(line)
    events = []
    for line in lines:
        m = TIMESTAMP_PAT.match(line)
        if not m:
            continue
        try:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if ASSIGNED_PAT.search(line):
            events.append(("assigned", ts))
        elif COMPLETED_PAT.search(line):
            events.append(("completed", ts))
    return events

def roundN(dt: datetime, minutes: int):
    m = (dt.minute // minutes) * minutes
    return dt.replace(second=0, microsecond=0, minute=m)

@app.route("/")
def index():
    return render_template_string(HTML, bucket=BUCKET_MIN, window=WINDOW_HOURS)

@app.route("/stats")
def stats():
    now = datetime.now()
    events = parse_log()

    a1  = sum(1 for t,ts in events if t=="assigned"  and ts >= now - timedelta(hours=1))
    c1  = sum(1 for t,ts in events if t=="completed" and ts >= now - timedelta(hours=1))
    a24 = sum(1 for t,ts in events if t=="assigned"  and ts >= now - timedelta(hours=24))
    c24 = sum(1 for t,ts in events if t=="completed" and ts >= now - timedelta(hours=24))

    start = now - timedelta(hours=WINDOW_HOURS)
    bucket_a = defaultdict(int); bucket_c = defaultdict(int)
    for t, ts in events:
        if ts < start: continue
        k = roundN(ts, BUCKET_MIN)
        (bucket_a if t=="assigned" else bucket_c)[k] += 1

    labels, A, C = [], [], []
    cur = roundN(start, BUCKET_MIN); end = roundN(now, BUCKET_MIN)
    while cur <= end:
        labels.append(cur.strftime("%H:%M"))
        A.append(bucket_a.get(cur, 0)); C.append(bucket_c.get(cur, 0))
        cur += timedelta(minutes=BUCKET_MIN)

    return jsonify({
        "totals": {"assigned_1h":a1,"completed_1h":c1,"assigned_24h":a24,"completed_24h":c24},
        "series": {"labels":labels,"assigned":A,"completed":C}
    })

@app.route("/recent")
def recent():
    limit = int(request.args.get("limit", 100))
    events = parse_log()
    items = [{"type":t, "ts": ts.isoformat()} for t,ts in events[-limit:]]
    return jsonify({"count": len(items), "items": items})

@app.route("/events")
def sse_events():
    def gen():
        path = LOG_PATH; pos = 0
        if os.path.exists(path):
            try: pos = os.path.getsize(path)
            except Exception: pos = 0
        while True:
            try:
                if os.path.exists(path):
                    with open(path, "r", errors="ignore") as f:
                        f.seek(pos); chunk = f.read(); pos = f.tell()
                        if chunk:
                            for line in chunk.splitlines():
                                m = TIMESTAMP_PAT.match(line)
                                if not m: continue
                                ts = m.group(1)
                                typ = "assigned" if ASSIGNED_PAT.search(line) else ("completed" if COMPLETED_PAT.search(line) else None)
                                if typ:
                                    yield "data: " + '{"ts":"%s","type":"%s"}\n\n' % (ts, typ)
                yield "data: {}\n\n"; time.sleep(1)
            except GeneratorExit:
                break
            except Exception:
                time.sleep(1)
    return Response(gen(), mimetype="text/event-stream")

@app.route("/health")
def health():
    exists = os.path.exists(LOG_PATH)
    size = os.path.getsize(LOG_PATH) if exists else 0
    mtime = datetime.fromtimestamp(os.path.getmtime(LOG_PATH)).isoformat() if exists else None
    events = parse_log()
    now = datetime.now()
    in_window = sum(1 for _,ts in events if ts >= now - timedelta(hours=WINDOW_HOURS))
    return jsonify({"ok": exists and size>0, "log_path": LOG_PATH, "exists": exists,
                    "size_bytes": size, "mtime": mtime, "events_in_window": in_window})

@app.route("/config")
def config():
    return jsonify({"LOG_PATH": LOG_PATH, "PORT": PORT, "MAX_LINES": MAX_LINES,
                    "BUCKET_MIN": BUCKET_MIN, "WINDOW_HOURS": WINDOW_HOURS})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
