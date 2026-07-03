const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    panels.forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
    if (tab.dataset.tab === "tools") loadTools();
  });
});

function statusBanner(status, message) {
  const label = { refer: "Medical referral", blacklisted: "Blocked", caution: "Caution", clear: "Clear", ok: "OK", error: "Error" }[status] || status;
  return `<div class="status-banner status-${status}">${label}${message ? " — " + message : ""}</div>`;
}

function errorBanner(err) {
  return statusBanner("refer", err.message || "Something went wrong talking to the MCP server.");
}

function gradeBadge(grade) {
  return `<span class="grade grade-${grade}">Evidence ${grade}</span>`;
}

function remedyCard(r) {
  return `<div class="card">
    <h3>${r.name} <span class="meta">(${r.sanskrit_name})</span></h3>
    <div class="meta">${gradeBadge(r.evidence_grade)}</div>
    <p><strong>Prep:</strong> ${r.prep}</p>
    <p><strong>Traditional use:</strong> ${r.traditional_use}</p>
    <p><strong>Modern evidence:</strong> ${r.modern_evidence}</p>
    ${r.cautions.length ? `<p><strong>Cautions:</strong></p><ul>${r.cautions.map((c) => `<li>${c}</li>`).join("")}</ul>` : ""}
  </div>`;
}

class ApiError extends Error {}

async function parseOrThrow(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    // response wasn't JSON (e.g. a raw network/proxy error page)
  }
  if (!res.ok) {
    throw new ApiError((body && body.message) || `Request failed (HTTP ${res.status}).`);
  }
  return body;
}

async function postJSON(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return parseOrThrow(res);
}

async function getJSON(url) {
  const res = await fetch(url);
  return parseOrThrow(res);
}

document.getElementById("remedy-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const out = document.getElementById("remedy-result");
  out.innerHTML = `<p class="empty">Checking…</p>`;
  try {
    const result = await postJSON("/api/suggest-remedy", { symptoms: form.get("symptoms"), context: form.get("context") });
    let html = statusBanner(result.status, result.message);
    if (result.guidance) html += `<div class="card">${result.guidance}</div>`;
    if (result.remedies && result.remedies.length) {
      html += result.remedies.map(remedyCard).join("");
    } else if (result.status !== "refer" && result.status !== "blacklisted" && !result.guidance) {
      html += `<p class="empty">No matching remedies found for that description.</p>`;
    }
    if (result.disclaimer) html += `<p class="hint">${result.disclaimer}</p>`;
    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = errorBanner(err);
  }
});

document.getElementById("recipe-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const out = document.getElementById("recipe-result");
  out.innerHTML = `<p class="empty">Searching…</p>`;
  try {
    const params = new URLSearchParams({ dosha: form.get("dosha"), season: form.get("season"), query: form.get("query") });
    const result = await getJSON(`/api/recipes?${params}`);
    if (!result.recipes.length) {
      out.innerHTML = `<p class="empty">No recipes matched.</p>`;
      return;
    }
    out.innerHTML = result.recipes
      .map(
        (r) => `<div class="card">
        <h3>${r.name}</h3>
        <div class="meta">Dosha: ${r.dosha.join(", ")} · Season: ${r.season.join(", ")}</div>
        <p><strong>Ingredients:</strong> ${r.ingredients.join(", ")}</p>
        <p><strong>Method:</strong> ${r.method}</p>
        <p><strong>Notes:</strong> ${r.notes}</p>
      </div>`
      )
      .join("");
  } catch (err) {
    out.innerHTML = errorBanner(err);
  }
});

document.getElementById("routine-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const out = document.getElementById("routine-result");
  out.innerHTML = `<p class="empty">Building plan…</p>`;
  try {
    const result = await postJSON("/api/day-plan", {
      dosha: form.get("dosha"),
      season: form.get("season"),
      level: form.get("level"),
      constraints: form.get("constraints"),
    });
    let html = statusBanner(result.status, result.message);
    if (result.swapped_note) html += `<div class="swapped-note">${result.swapped_note}</div>`;
    if (result.routine && result.routine.daily_steps) {
      const r = result.routine;
      html += `<div class="card">
        <h3>Wake: ${r.wake_time}</h3>
        <p><strong>Seasonal focus:</strong> ${r.seasonal_focus}</p>
        <ul>${r.daily_steps.map((s) => `<li>${s}</li>`).join("")}</ul>
        <p><strong>Exercise:</strong> ${r.exercise.map((ex) => `${ex.name} (${ex.duration_min} min)`).join(", ")}</p>
        <p><strong>Pranayama:</strong> ${r.pranayama.name} — ${r.pranayama.steps}</p>
      </div>`;
    }
    if (result.disclaimer) html += `<p class="hint">${result.disclaimer}</p>`;
    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = errorBanner(err);
  }
});

document.getElementById("pranayama-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const out = document.getElementById("pranayama-result");
  out.innerHTML = `<p class="empty">Searching…</p>`;
  try {
    const params = new URLSearchParams({ effect: form.get("effect") });
    const result = await getJSON(`/api/pranayama?${params}`);
    if (!result.techniques.length) {
      out.innerHTML = `<p class="empty">No techniques matched.</p>`;
      return;
    }
    out.innerHTML = result.techniques
      .map(
        (p) => `<div class="card">
        <h3>${p.name}</h3>
        <div class="meta">Effect: ${p.effect.join(", ")} · ~${p.duration_min} min</div>
        <p>${p.steps}</p>
        ${p.cautions.length ? `<p><strong>Cautions:</strong></p><ul>${p.cautions.map((c) => `<li>${c}</li>`).join("")}</ul>` : ""}
      </div>`
      )
      .join("");
  } catch (err) {
    out.innerHTML = errorBanner(err);
  }
});

async function loadTools() {
  const out = document.getElementById("tools-result");
  out.innerHTML = `<p class="empty">Loading live tool registry…</p>`;
  try {
    const tools = await getJSON("/api/tools");
    out.innerHTML = tools.map((t) => `<div class="card"><h3>${t.name}</h3><p>${t.description}</p></div>`).join("");
  } catch (err) {
    out.innerHTML = errorBanner(err);
  }
}
