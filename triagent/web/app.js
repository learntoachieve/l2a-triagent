"use strict";

// All API calls use RELATIVE URLs so this page works identically locally and
// when deployed behind any host — never hardcode localhost.
const API = "/api";

const els = {
  status: document.getElementById("status"),
  queue: document.getElementById("queue"),
  search: document.getElementById("search"),
  repo: document.getElementById("repo"),
  difficulty: document.getElementById("difficulty"),
  minSolv: document.getElementById("minSolv"),
  minSolvVal: document.getElementById("minSolvVal"),
  overlay: document.getElementById("overlay"),
  detailBody: document.getElementById("detailBody"),
  closeDrawer: document.getElementById("closeDrawer"),
};

let repoChoicesLoaded = false;

function pct(x) {
  return x === null || x === undefined ? "—" : Math.round(x * 100) + "%";
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function metric(label, cls, value) {
  const w = value === null || value === undefined ? 0 : Math.round(value * 100);
  return `
    <div class="metric">
      <span>${label}</span>
      <span class="bar ${cls}"><span style="width:${w}%"></span></span>
      <span class="val">${pct(value)}</span>
    </div>`;
}

function card(issue) {
  const diff = issue.difficulty
    ? `<span class="badge ${esc(issue.difficulty)}">${esc(issue.difficulty)}</span>`
    : "";
  const type = issue.issue_type ? `<span class="badge">${esc(issue.issue_type)}</span>` : "";
  const scored = issue.solvability !== null && issue.solvability !== undefined;
  const scores = scored
    ? metric("S", "solv", issue.solvability) + metric("F", "fit", issue.skill_fit)
    : `<span class="unscored">not yet scored</span>`;

  const li = document.createElement("li");
  li.className = "card";
  li.innerHTML = `
    <div class="card-main">
      <p class="card-title">${esc(issue.title)}</p>
      <div class="card-meta">
        <span class="repo">${esc(issue.repo)}</span>
        <span>#${issue.number}</span>
        ${diff}${type}
        <span>${esc(issue.state)}</span>
      </div>
    </div>
    <div class="scores">${scores}</div>`;
  li.addEventListener("click", () => openDetail(issue));
  return li;
}

async function loadQueue() {
  const params = new URLSearchParams();
  if (els.search.value.trim()) params.set("q", els.search.value.trim());
  if (els.repo.value) params.set("repo", els.repo.value);
  if (els.difficulty.value) params.set("difficulty", els.difficulty.value);
  if (Number(els.minSolv.value) > 0) params.set("min_solvability", els.minSolv.value);

  els.status.textContent = "Loading…";
  els.queue.innerHTML = "";
  try {
    const res = await fetch(`${API}/issues?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const issues = await res.json();

    if (!repoChoicesLoaded) populateRepos(issues);

    if (issues.length === 0) {
      els.status.textContent =
        "No issues match these filters. Only ~40 issues are scored so far — try lowering the minimum solvability.";
      return;
    }
    const scored = issues.filter((i) => i.solvability !== null).length;
    els.status.textContent = `${issues.length} issue${issues.length === 1 ? "" : "s"} · ${scored} scored`;
    const frag = document.createDocumentFragment();
    issues.forEach((i) => frag.appendChild(card(i)));
    els.queue.appendChild(frag);
  } catch (err) {
    els.status.textContent = `Could not load the queue (${err.message}). Is the API running?`;
  }
}

// Populate the repo dropdown once, from the unfiltered first load.
function populateRepos(issues) {
  const repos = [...new Set(issues.map((i) => i.repo))].sort();
  for (const r of repos) {
    const opt = document.createElement("option");
    opt.value = r;
    opt.textContent = r;
    els.repo.appendChild(opt);
  }
  repoChoicesLoaded = true;
}

async function openDetail(issue) {
  els.overlay.classList.remove("hidden");
  els.detailBody.innerHTML = `<p class="status">Loading…</p>`;
  const [owner, rest] = issue.repo.split("/");
  try {
    const res = await fetch(`${API}/issues/${owner}/${rest}/${issue.number}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const d = await res.json();
    renderDetail(d);
  } catch (err) {
    els.detailBody.innerHTML = `<p class="status">Could not load detail (${esc(err.message)}).</p>`;
  }
}

function renderDetail(d) {
  const scored = d.solvability !== null && d.solvability !== undefined;
  const labels = (d.labels || []).map((l) => `<span class="badge">${esc(l)}</span>`).join("");
  const scoreBlock = scored
    ? metric("Solvability", "solv", d.solvability) + metric("Skill fit", "fit", d.skill_fit)
    : `<span class="unscored">not yet scored</span>`;
  const rationale = d.rationale ? esc(d.rationale) : "No rationale (this issue has not been scored).";
  const body = d.body ? esc(d.body) : "(no description)";

  els.detailBody.innerHTML = `
    <div class="detail">
      <h2 id="d-title">${esc(d.title)}</h2>
      <div class="card-meta">
        <span class="repo">${esc(d.repo)}</span><span>#${d.number}</span>
        ${d.difficulty ? `<span class="badge ${esc(d.difficulty)}">${esc(d.difficulty)}</span>` : ""}
        ${d.issue_type ? `<span class="badge">${esc(d.issue_type)}</span>` : ""}
        <span>${esc(d.state)}</span>
      </div>
      <div class="section-label">Scores</div>
      <div class="scores">${scoreBlock}</div>
      <div class="section-label">Rationale</div>
      <div class="rationale">${rationale}</div>
      ${labels ? `<div class="section-label">Labels</div><div class="labels">${labels}</div>` : ""}
      <div class="section-label">Description</div>
      <div class="body">${body}</div>
      <a class="gh-link" href="${esc(d.html_url)}" target="_blank" rel="noopener">Open on GitHub →</a>
    </div>`;
}

function closeDetail() {
  els.overlay.classList.add("hidden");
}

// --- events ---
let searchTimer;
els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadQueue, 200);
});
els.repo.addEventListener("change", loadQueue);
els.difficulty.addEventListener("change", loadQueue);
els.minSolv.addEventListener("input", () => {
  els.minSolvVal.textContent = Number(els.minSolv.value).toFixed(2);
});
els.minSolv.addEventListener("change", loadQueue);
els.closeDrawer.addEventListener("click", closeDetail);
els.overlay.addEventListener("click", (e) => {
  if (e.target === els.overlay) closeDetail();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDetail();
});

loadQueue();
