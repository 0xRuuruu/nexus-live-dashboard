<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Nexus Live Jobs Dashboard</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    :root{
      --bg:#ffffff; --text:#0f172a; --muted:#64748b;
      --card:#ffffff; --border:#e5e7eb; --shadow:0 1px 6px rgba(0,0,0,.05);
      --accent:#2563eb; --ok:#15803d; --bad:#b91c1c;
    }
    :root[data-theme="dark"]{
      --bg:#0b1220; --text:#e5e7eb; --muted:#94a3b8;
      --card:#0f172a; --border:#1f2937; --shadow:0 1px 10px rgba(0,0,0,.4);
      --accent:#60a5fa; --ok:#22c55e; --bad:#f87171;
    }
    html,body{height:100%}
    body{
      font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
      margin:20px;background:var(--bg);color:var(--text);transition:background .2s,color .2s
    }
    h1{margin:0 0 4px}
    .meta{color:var(--muted);margin-bottom:12px}
    .toolbar{display:flex;gap:8px;align-items:center;justify-content:space-between;margin-bottom:8px}
    .btn{
      border:1px solid var(--border);background:var(--card);color:var(--text);
      border-radius:10px;padding:6px 10px;cursor:pointer;box-shadow:var(--shadow)
    }
    .btn:hover{filter:brightness(1.05)}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
    .card{border:1px solid var(--border);border-radius:12px;padding:12px;box-shadow:var(--shadow);background:var(--card)}
    .num{font-size:28px;font-weight:700}
    canvas{width:100%;height:320px}
    code{background:rgba(148,163,184,.15);padding:2px 6px;border-radius:6px}
    .ok{color:var(--ok)} .bad{color:var(--bad)}
  </style>
</head>
<body>
  <div class="toolbar">
    <div>
      <h1 style="margin:0">Nexus Live Jobs</h1>
      <div class="meta">Auto-refresh every <code id="rf">10s</code> · Source: <code id="lp"></code></div>
    </div>
    <button id="themeBtn" class="btn" type="button">🌓 Toggle Theme</button>
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
    <div class="meta">Blue=assigned · Green=completed</div>
  </div>

  <div class="card" style="margin-top:12px">
    <strong>Health</strong>
    <div id="health">Loading…</div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    (function initTheme(){
      const saved = localStorage.getItem('theme');
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = saved || (prefersDark ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', theme);
    })();

    document.addEventListener('DOMContentLoaded', ()=>{
      const btn = document.getElementById('themeBtn');
      btn.addEventListener('click', ()=>{
        const cur = document.documentElement.getAttribute('data-theme') || 'light';
        const next = cur === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
      });
    });

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
