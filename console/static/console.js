const api = (p, opts) => fetch(p, opts).then((r) => r.json());

async function refreshHealth() {
  const el = document.getElementById("health");
  try {
    const h = await api("/api/health");
    const up = h.mcp === "up";
    el.textContent = up ? "MCP up" : "MCP down";
    el.className = "pill " + (up ? "up" : "down");
  } catch {
    el.textContent = "console error";
    el.className = "pill down";
  }
}

async function loadTools() {
  const list = document.getElementById("toolList");
  let tools = [];
  try {
    tools = await api("/api/tools");
  } catch {
    list.innerHTML = '<p class="muted">Cannot reach MCP server.</p>';
    return;
  }
  list.innerHTML = "";
  tools.forEach((t) => {
    const b = document.createElement("button");
    b.textContent = t.name;
    b.onclick = () => renderRunner(t);
    list.appendChild(b);
  });
}

const TOOL_HINTS = {
  generate_connect_url: `
    <details class="tool-hint" open>
      <summary>FinBank test credentials
        <a href="https://developer.mastercard.com/open-finance-us/documentation/integration-and-testing/test-the-apis/"
           target="_blank" rel="noopener">→ Full test profile docs</a>
      </summary>
      <p class="muted">After opening the generated URL, search for <strong>FinBank Profiles – A</strong>
      and log in with one of these (username&nbsp;=&nbsp;password unless noted):</p>

      <p class="hint-section">Test Personas</p>
      <table class="hint-table">
        <thead><tr><th>Username / Password</th><th>Persona</th><th>Key accounts</th></tr></thead>
        <tbody>
          <tr><td><code>profile_700</code></td><td>Sue – PM, steady income</td><td>Checking, savings, mortgage, investments, car lease</td></tr>
          <tr><td><code>profile_701</code></td><td>Francis – restaurant owner</td><td>Multiple business checking, loans</td></tr>
          <tr><td><code>profile_702</code></td><td>Joe – gig / contract worker</td><td>Checking, savings, no investments</td></tr>
          <tr><td><code>profile_703</code></td><td>River – construction, renter</td><td>Checking, savings only</td></tr>
          <tr><td><code>profile_704</code></td><td>Alex – student debt</td><td>Checking, limited savings, investment starter</td></tr>
        </tbody>
      </table>

      <p class="hint-section">Standard bank account profiles</p>
      <table class="hint-table">
        <thead><tr><th>Username / Password</th><th>Accounts</th></tr></thead>
        <tbody>
          <tr><td><code>profile_03</code> ★</td><td>Checking, Personal Investment, 401k, Roth, Savings (used by Happy Path)</td></tr>
          <tr><td><code>profile_02</code></td><td>Savings, IRA, 401k, Credit Card</td></tr>
          <tr><td><code>profile_04</code></td><td>Checking, 403B, 529, Rollover, Mortgage</td></tr>
          <tr><td><code>profile_05</code></td><td>Checking, Investment, Stocks, UGMA, UTMA</td></tr>
          <tr><td><code>profile_06</code></td><td>Checking, Retirement, KEOGH, 457, Credit Card</td></tr>
          <tr><td><code>demo</code> / <code>go</code></td><td>Basic sign-in success (no MFA)</td></tr>
        </tbody>
      </table>
    </details>
  `,
};

function renderRunner(tool) {
  const props = (tool.schema && tool.schema.properties) || {};
  const required = (tool.schema && tool.schema.required) || [];
  const fields = Object.entries(props)
    .map(([k, s]) => {
      const req = required.includes(k) ? " *" : "";
      return `<label>${k}${req} <small>${s.type || ""}</small>
        <input name="${k}" placeholder="${s.description || ""}"></label>`;
    })
    .join("");
  const hint = TOOL_HINTS[tool.name] || "";
  const r = document.getElementById("toolRunner");
  r.innerHTML = `<h2>${tool.name}</h2><p class="muted">${tool.description || ""}</p>
    <form id="callForm">${fields}<button type="submit">Call tool</button></form>
    ${hint}
    <div id="callActions"></div>
    <pre id="callResult" class="terminal">—</pre>`;
  document.getElementById("callForm").onsubmit = async (e) => {
    e.preventDefault();
    const args = {};
    new FormData(e.target).forEach((v, k) => {
      if (v !== "") args[k] = v;
    });
    document.getElementById("callResult").textContent = "Calling…";
    document.getElementById("callActions").innerHTML = "";
    try {
      const res = await api("/api/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: tool.name, arguments: args }),
      });
      document.getElementById("callResult").textContent = JSON.stringify(res, null, 2);
      // Inject an Open Link button for any tool whose response contains a URL.
      const link = res.structured?.data?.link ?? res.structured?.link ?? null;
      if (link) {
        const btn = document.createElement("a");
        btn.href = link;
        btn.target = "_blank";
        btn.rel = "noopener noreferrer";
        btn.className = "open-link-btn";
        btn.textContent = "Open Link ↗";
        document.getElementById("callActions").appendChild(btn);
      }
    } catch (err) {
      document.getElementById("callResult").textContent = "Error: " + err;
    }
  };
}

document.getElementById("runTests").onclick = async () => {
  const out = document.getElementById("testOutput");
  out.textContent = "Running…";
  try {
    const res = await api("/api/tests/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ marker: document.getElementById("marker").value }),
    });
    out.textContent = `exit ${res.returncode}\n\n${res.output}`;
  } catch (err) {
    out.textContent = "Error: " + err;
  }
};

document.querySelectorAll(".tabs button").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    document.querySelectorAll(".tab").forEach((s) => s.classList.add("hidden"));
    document.getElementById("tab-" + b.dataset.tab).classList.remove("hidden");
    if (b.dataset.tab === "happy") loadProfiles();
  };
});

// ── Credentials modal ─────────────────────────────────────────────────────────
const credsModal = document.getElementById("credsModal");
document.getElementById("openCredsBtn").onclick = () => {
  loadCredentials();
  credsModal.showModal();
};
document.getElementById("closeCredsBtn").onclick = () => credsModal.close();
credsModal.addEventListener("click", (e) => {
  if (e.target === credsModal) credsModal.close();
});

let profilesLoaded = false;
async function loadProfiles() {
  if (profilesLoaded) return;
  const sel = document.getElementById("profileKey");
  try {
    const data = await api("/api/finbank-profiles");
    (data.profiles || []).forEach((p) => {
      const o = document.createElement("option");
      o.value = p.key;
      o.textContent = `${p.institution_name} (${p.username}/${p.password})`;
      sel.appendChild(o);
    });
    profilesLoaded = true;
  } catch {
    sel.innerHTML = '<option>cannot reach MCP</option>';
  }
}

const STEP_LABELS = {
  create_testing_customer: "Create testing customer",
  link_testing_accounts: "Link FinBank accounts (headless)",
  get_customer_accounts: "Fetch accounts",
  load_historic_transactions: "Load transaction history",
  get_customer_transactions: "Fetch transactions",
};

document.getElementById("runHappy").onclick = async () => {
  const stepsEl = document.getElementById("happySteps");
  const rawEl = document.getElementById("happyRaw");
  stepsEl.innerHTML = '<p class="muted">Running end-to-end against the sandbox…</p>';
  rawEl.classList.add("hidden");
  try {
    const res = await api("/api/happy-path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_key: document.getElementById("profileKey").value }),
    });
    const env = (res.structured && res.structured) || {};
    const d = env.data || {};
    const steps = d.steps || [];
    const summary = `<div class="card happy-summary ${d.ok ? "confirmed" : ""}">
      <strong>${d.institution || ""}</strong> · customer <code>${d.customer_id || "?"}</code><br>
      accounts: <code>${d.account_count ?? 0}</code> · transactions: <code>${d.transaction_count ?? 0}</code></div>`;
    const cards = steps
      .map(
        (s) => `<div class="q-card ${s.ok ? "confirmed" : ""}">
          <div class="status">${s.ok ? "ok" : "failed"} · ${s.status_code}</div>
          <strong>${STEP_LABELS[s.step] || s.step}</strong>
          ${s.error ? '<p class="muted">' + s.error + "</p>" : ""}</div>`
      )
      .join("");
    stepsEl.innerHTML = summary + cards;
    rawEl.textContent = JSON.stringify(res, null, 2);
    rawEl.classList.remove("hidden");
  } catch (err) {
    stepsEl.innerHTML = '<p class="muted">Error: ' + err + "</p>";
  }
};

refreshHealth();
loadTools();
setInterval(refreshHealth, 15000);

// ── Credentials form ─────────────────────────────────────────────────────────
let credsLoaded = false;

async function loadCredentials() {
  if (credsLoaded) return;
  try {
    const data = await api("/api/credentials");
    document.getElementById("envFilePath").textContent = data.path || ".env";
    const form = document.getElementById("credsForm");
    Object.entries(data.values || {}).forEach(([k, v]) => {
      const input = form.elements[k];
      if (input) input.value = v;
    });
    credsLoaded = true;
  } catch (err) {
    document.getElementById("credsSaveStatus").textContent = "Failed to load: " + err;
    document.getElementById("credsSaveStatus").className = "err";
  }
}

document.querySelectorAll(".toggle-secret").forEach((btn) => {
  btn.onclick = () => {
    const input = document.querySelector(`[name="${btn.dataset.target}"]`);
    if (!input) return;
    const hidden = input.type === "password";
    input.type = hidden ? "text" : "password";
    btn.textContent = hidden ? "Hide" : "Show";
  };
});

document.getElementById("saveCredsBtn").onclick = async () => {
  const status = document.getElementById("credsSaveStatus");
  status.textContent = "Saving…";
  status.className = "muted";
  const body = {};
  const form = document.getElementById("credsForm");
  form.querySelectorAll("input[name]").forEach((inp) => { body[inp.name] = inp.value; });
  try {
    const res = await api("/api/credentials", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.saved) {
      status.textContent = `Saved to ${res.path}`;
      status.className = "ok";
    } else {
      status.textContent = "Save failed: " + (res.error || "unknown error");
      status.className = "err";
    }
  } catch (err) {
    status.textContent = "Error: " + err;
    status.className = "err";
  }
};
