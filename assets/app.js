function statusUrl() {
  const path = window.location.pathname;
  const isSubPage = path.includes("/pages/");
  return new URL(isSubPage ? "../data/status.json" : "./data/status.json", window.location.href).href;
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmtNum(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "Not reported";
  const n = Number(value);
  if (!Number.isFinite(n)) return esc(value);
  return n.toFixed(digits);
}

function fmtAPR(value) {
  if (value === null || value === undefined || value === "") return "Not reported";
  return `${fmtNum(value, 2)}%`;
}

function fmtDD(value) {
  if (value === null || value === undefined || value === "") return "Not reported";
  return `${fmtNum(value, 2)}%`;
}

function fmtDelta(value) {
  if (value === null || value === undefined || value === "") return "";
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)} pts`;
}

function deltaClass(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "flat";
  if (n > 0.005) return "up";
  if (n < -0.005) return "down";
  return "flat";
}

function statusClass(status) {
  const s = String(status || "unknown").toLowerCase();
  if (s === "running") return "status-running";
  if (s === "idle") return "status-idle";
  if (s === "placeholder" || s === "idle_or_stale") return "status-placeholder";
  return "status-unknown";
}

function pill(status) {
  return `<span class="status-pill ${statusClass(status)}">${esc(status || "unknown")}</span>`;
}

function journeyCard(label, metric) {
  const start = metric?.start;
  const now = metric?.now;
  const delta = metric?.delta;
  const cls = deltaClass(delta);
  const startText = start === null || start === undefined ? "Waiting" : fmtAPR(start);
  const nowText = now === null || now === undefined ? "Waiting" : fmtAPR(now);
  const deltaText = delta === null || delta === undefined ? "Baseline forming" : fmtDelta(delta);

  return `
    <section class="card third session-card ${cls}">
      <div class="session-label">${esc(label)}</div>
      <div class="journey">
        <span>${startText}</span>
        <span class="arrow">→</span>
        <span>${nowText}</span>
      </div>
      <div class="session-delta">${deltaText}</div>
    </section>
  `;
}

async function loadStatus() {
  const res = await fetch(statusUrl(), { cache: "no-store" });
  if (!res.ok) throw new Error(`Could not load ${statusUrl()}`);
  return await res.json();
}

function nav(root) {
  return `
    <nav class="nav">
      <a href="${root}index.html">Show Summary All</a>
      <a href="${root}pages/monkey.html">Kraken Profit Monkey Trainer</a>
      <a href="${root}pages/ape.html">Kraken Profit Ape Live Bot (IP)</a>
      <a href="${root}pages/llama.html">Alpaca Profit Llama Trainer (IP)</a>
      <a href="${root}pages/alcuna.html">Alpaca Profit Alcuna Live Bot (IP)</a>
    </nav>
  `;
}

function pageShell(title, subtitle) {
  document.body.innerHTML = `
    <header class="header">
      <div class="header-inner">
        <h1 class="title">${esc(title)}</h1>
        <div class="subtitle">${esc(subtitle)}</div>
        ${nav("./")}
      </div>
    </header>
    <main class="main" id="app"><div class="notice">Loading bot status...</div></main>
    <footer class="footer">Profit AllBots Dashboard</footer>
  `;
}

function pageShellSub(title, subtitle) {
  document.body.innerHTML = `
    <header class="header">
      <div class="header-inner">
        <h1 class="title">${esc(title)}</h1>
        <div class="subtitle">${esc(subtitle)}</div>
        ${nav("../")}
      </div>
    </header>
    <main class="main" id="app"><div class="notice">Loading bot status...</div></main>
    <footer class="footer">Profit AllBots Dashboard</footer>
  `;
}

function renderSummary(data) {
  const s = data.summary || {};
  const bots = data.bots || {};
  const cards = Object.values(bots).map(bot => `
    <section class="card half">
      <h2>${esc(bot.display_name || bot.id)}</h2>
      <div class="kv">
        <div>Status</div><div>${pill(bot.status)}</div>
        <div>Current Run</div><div>${esc(bot.current_run || "Not reported")}</div>
        <div>Estimated APR</div><div>${fmtAPR(bot.estimated_apr)}</div>
        <div>Current Goal</div><div>${esc(bot.current_goal || "Not reported")}</div>
      </div>
    </section>
  `).join("");

  document.getElementById("app").innerHTML = `
    <section class="grid">
      <section class="card third metric"><div class="label">Configured Bots</div><div class="value">${s.configured_bots ?? "0"}</div></section>
      <section class="card third metric"><div class="label">Running Bots</div><div class="value">${s.running_bots ?? "0"}</div></section>
      <section class="card third metric"><div class="label">Profit Monkey Estimated APR</div><div class="value">${fmtAPR(s.profit_monkey_estimated_apr)}</div></section>
      <section class="card">
        <h2>AllBots Summary</h2>
        <div class="kv">
          <div>Generated At</div><div>${esc(data.generated_at || "Not reported")}</div>
          <div>Best Current APR Bot</div><div>${s.best_current_apr_bot ? `${esc(s.best_current_apr_bot.display_name)}: ${fmtAPR(s.best_current_apr_bot.estimated_apr)}` : "Not reported"}</div>
          <div>Profit Monkey Current Run</div><div>${esc(s.profit_monkey_current_run || "Not reported")}</div>
          <div>Profit Monkey Status</div><div>${pill(s.profit_monkey_status)}</div>
        </div>
      </section>
      ${cards}
    </section>
  `;
}

function renderPlaceholder(bot) {
  document.getElementById("app").innerHTML = `
    <section class="grid">
      <section class="card">
        <h2>${esc(bot.display_name || bot.id || "Placeholder")}</h2>
        <div class="notice">This page is reserved. It will automatically populate once this bot starts writing its own status.json.</div>
        <div class="kv" style="margin-top:16px">
          <div>Status</div><div>${pill(bot.status)}</div>
          <div>Current Run</div><div>${esc(bot.current_run || "In progress")}</div>
          <div>Goal</div><div>${esc(bot.current_goal || "Placeholder reserved for future status integration.")}</div>
        </div>
      </section>
    </section>
  `;
}

function renderMonkey(data) {
  const bot = (data.bots || {}).profit_monkey;
  if (!bot || !bot.available) {
    renderPlaceholder(bot || {display_name:"Kraken Profit Monkey Trainer", status:"placeholder"});
    return;
  }

  const session = bot.session_metrics || {};
  const promotions = session.promotions_this_session ?? bot.total_promotions ?? 0;
  const champions = bot.champions || [];

  const rows = champions.map(c => `
    <tr>
      <td class="mono">${esc(c.regime_label || c.regime)}</td>
      <td>${esc(c.generation ?? "0")}</td>
      <td>${esc(c.promotions_total ?? "0")}</td>
      <td>${fmtNum(c.score, 4)}</td>
      <td>${fmtAPR(c.apr)}</td>
      <td>${fmtDD(c.drawdown_pct)}</td>
      <td>${esc(c.trades ?? "0")}</td>
      <td>${esc(c.last_promotion || "Not reported yet")}</td>
      <td class="small">${esc(c.family || "")}</td>
    </tr>
  `).join("");

  const engineRows = (bot.engines || []).map(e => `
    <tr>
      <td>${esc(e.name)}</td>
      <td>${pill(e.status)}</td>
      <td>${esc(e.done ?? 0)} / ${esc(e.total ?? 0)}</td>
      <td>${esc(e.promotions ?? 0)}</td>
    </tr>
  `).join("");

  const laneRows = (bot.lanes || []).map(l => `
    <tr>
      <td>${esc(l.lane)}</td>
      <td>${esc(l.regime)}</td>
      <td>${pill(l.status)}</td>
    </tr>
  `).join("");

  document.getElementById("app").innerHTML = `
    <section class="grid">
      <section class="card third metric"><div class="label">Current Estimated APR</div><div class="value">${fmtAPR(bot.estimated_apr)}</div></section>
      <section class="card third metric"><div class="label">Current Status</div><div class="value">${pill(bot.status)}</div></section>
      <section class="card third metric"><div class="label">Director Cycle</div><div class="value">${esc(bot.director_cycle ?? "Not reported")}</div></section>

      <section class="card session-header">
        <h2>Session Pulse</h2>
        <div class="small">Start → now progress for the current Profit Monkey run.</div>
      </section>
      <section class="card third session-card promo">
        <div class="session-label">Promotions This Session</div>
        <div class="journey big-number">${esc(promotions)}</div>
        <div class="session-delta">${esc(session.session_key ? "Live run total" : "Waiting for run key")}</div>
      </section>
      ${journeyCard("Estimated APR", session.estimated_apr)}
      ${journeyCard("Tested APR", session.tested_apr)}

      <section class="card">
        <h2>Current Run</h2>
        <div class="kv">
          <div>Overall Goal</div><div>${esc(bot.current_goal || "Not reported")}</div>
          <div>Run Mode</div><div>${esc(bot.current_run || "Not reported")}</div>
          <div>Phase</div><div>${esc(bot.phase || "Not reported")}</div>
          <div>Symbol</div><div>${esc(bot.symbol || "Not reported")}</div>
          <div>Aggression Mode</div><div>${esc(bot.aggression_mode || "Not reported")}</div>
          <div>Progressive Level</div><div>${esc(bot.progressive_level ?? "Not reported")}</div>
          <div>Workers</div><div>${esc(bot.workers_verified ?? bot.workers ?? "Not reported")}</div>
          <div>Coverage</div><div>${fmtNum(bot.champion_coverage_pct, 2)}%</div>
          <div>Last Status Update</div><div>${esc(bot.source_updated_at || data.generated_at || "Not reported")}</div>
          <div>Last Combined Test</div><div>${fmtAPR(bot.last_combined_test_apr)} from ${esc(bot.last_combined_test_source || "unknown source")}</div>
        </div>
      </section>

      <section class="card half">
        <h2>Engines</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Engine</th><th>Status</th><th>Progress</th><th>Promotions</th></tr></thead>
            <tbody>${engineRows || `<tr><td colspan="4">No engine data reported.</td></tr>`}</tbody>
          </table>
        </div>
      </section>

      <section class="card half">
        <h2>Worker Lanes</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Lane</th><th>Regime</th><th>Status</th></tr></thead>
            <tbody>${laneRows || `<tr><td colspan="3">No lane data reported.</td></tr>`}</tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <h2>Regime Champions</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Regime</th><th>Gen</th><th>Promotions</th><th>Score</th><th>APR</th><th>DD</th><th>Trades</th><th>Last Promotion</th><th>Family</th>
              </tr>
            </thead>
            <tbody>${rows || `<tr><td colspan="9">No champions reported.</td></tr>`}</tbody>
          </table>
        </div>
        <p class="small">Last promotion will display once the trainer writes a per-champion promotion timestamp. Until then, this page safely shows “Not reported yet.”</p>
      </section>
    </section>
  `;
}

async function boot(kind) {
  try {
    const data = await loadStatus();
    if (kind === "summary") return renderSummary(data);
    if (kind === "monkey") return renderMonkey(data);
    const bot = (data.bots || {})[kind] || { id: kind, display_name: kind, status: "placeholder" };
    return renderPlaceholder(bot);
  } catch (err) {
    document.getElementById("app").innerHTML = `<div class="notice">Could not load status: ${esc(err.message)}</div>`;
  }
}

window.AllBots = { pageShell, pageShellSub, boot };
