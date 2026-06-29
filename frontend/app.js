const EXAMPLES = [
  "où est gérée l'authentification ?",
  "comment sont créés les tokens JWT ?",
  "où se trouve la connexion à la base de données ?",
  "comment fonctionne le paiement ?",
];

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

async function refresh() {
  const s = await api("/api/stats");
  $("status").textContent = `${s.files} fichiers · ${s.chunks} chunks indexés`;
  $("status").className = "status ok";
  if (s.path) {
    const name = s.path.replace(/[\\/]+$/, "").split(/[\\/]/).pop();
    $("repo-chip").textContent = name || s.path;
    $("repo-chip").title = s.path;
  }
  renderFiles(await api("/api/tree"));
  renderCrit(await api("/api/critical"));
}

async function init() {
  EXAMPLES.forEach((ex) => {
    const c = document.createElement("button");
    c.className = "chip";
    c.textContent = ex;
    c.onclick = () => { $("q").value = ex; ask(); };
    $("chips").appendChild(c);
  });
  $("ask").addEventListener("click", () => ask());
  $("q").addEventListener("keydown", (e) => { if (e.key === "Enter") ask(); });
  $("load").addEventListener("click", () => loadRepo());
  $("repo-path").addEventListener("keydown", (e) => { if (e.key === "Enter") loadRepo(); });
  $("reset").addEventListener("click", () => loadRepo("sample_repo"));
  $("browse").addEventListener("click", () => $("folder").click());
  $("folder").addEventListener("change", importFiles);

  try { await refresh(); }
  catch (e) {
    $("status").textContent = "API non disponible — démarrez le serveur";
    $("status").className = "status err";
  }
}

function showLoadMsg(kind, text) {
  const msg = $("load-msg");
  msg.hidden = false;
  msg.className = "load-msg" + (kind ? " " + kind : "");
  msg.textContent = text;
}

async function loadRepo(forced) {
  const path = forced || $("repo-path").value.trim();
  if (!path) return;
  showLoadMsg("", "Indexation…");
  try {
    const res = await api("/api/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    if (!res.ok) { showLoadMsg("err", res.error); return; }
    showLoadMsg("ok", `Indexé : ${res.stats.files} fichiers · ${res.stats.chunks} chunks.`);
    if (!forced) $("repo-path").value = "";
    resetAnswer();
    await refresh();
  } catch (e) {
    showLoadMsg("err", "Erreur de communication avec l'API.");
  }
}

const IMPORT_EXTS = ["py","js","ts","jsx","tsx","java","go","rb","php","c","cpp","h","hpp",
  "cs","rs","kt","swift","scala","md","txt","rst","yml","yaml","json","toml","ini","cfg"];
const IMPORT_SKIP = /(^|\/)(node_modules|\.git|__pycache__|\.venv|venv|dist|build)\//;

async function importFiles(e) {
  const picked = [...e.target.files].filter((f) => {
    const rel = f.webkitRelativePath || f.name;
    if (IMPORT_SKIP.test(rel)) return false;
    const ext = f.name.split(".").pop().toLowerCase();
    return IMPORT_EXTS.includes(ext) || f.name.startsWith(".env");
  }).slice(0, 500);

  if (!picked.length) { showLoadMsg("err", "Aucun fichier de code ou doc trouvé dans ce dossier."); return; }
  showLoadMsg("", `Lecture de ${picked.length} fichiers…`);

  const files = [];
  for (const f of picked) {
    try {
      const rel = (f.webkitRelativePath || f.name).split("/").slice(1).join("/") || f.name;
      files.push({ path: rel, content: await f.text() });
    } catch (_) {}
  }
  const label = ((picked[0].webkitRelativePath || "").split("/")[0]) || "dépôt importé";
  try {
    const res = await api("/api/load_files", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files, label }),
    });
    if (!res.ok) { showLoadMsg("err", res.error); return; }
    showLoadMsg("ok", `Indexé : ${res.stats.files} fichiers · ${res.stats.chunks} chunks.`);
    resetAnswer();
    await refresh();
  } catch (err) {
    showLoadMsg("err", "Erreur de communication avec l'API.");
  } finally {
    e.target.value = "";
  }
}

function renderFiles(files) {
  const byDir = {};
  files.forEach((f) => {
    const norm = f.path.replace(/\\/g, "/");
    const dir = norm.includes("/") ? norm.split("/").slice(0, -1).join("/") : "(racine)";
    (byDir[dir] = byDir[dir] || []).push({ ...f, norm });
  });
  let html = "";
  Object.keys(byDir).sort().forEach((dir) => {
    html += `<div class="node dir">${esc(dir)}/</div>`;
    byDir[dir].forEach((f) => {
      const color = f.category === "code" ? "var(--relevance)"
        : f.category === "config" ? "var(--signal)" : "var(--ink-faint)";
      html += `<div class="node indent"><span style="display:flex;gap:7px;align-items:center">
        <span class="dot" style="background:${color}"></span>${esc(f.norm.split("/").pop())}</span>
        <span class="meta">${f.n_lines} l.</span></div>`;
    });
  });
  $("view-files").innerHTML = html;
}

function renderCrit(list) {
  if (!list.length) { $("view-crit").innerHTML = '<div class="empty" style="margin:7px">Aucun fichier critique détecté.</div>'; return; }
  $("view-crit").innerHTML = list.map((c) => `
    <div class="crit">
      <div class="top"><span class="path">${esc(c.path)}</span>
        <span class="score-pill">${c.score.toFixed(2)}</span></div>
      <ul class="reasons">${c.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
    </div>`).join("");
}

function showTab(which) {
  const f = which === "files";
  $("view-files").hidden = !f;
  $("view-crit").hidden = f;
  $("tab-files").setAttribute("aria-selected", f);
  $("tab-crit").setAttribute("aria-selected", !f);
}

function resetAnswer() {
  $("answer").innerHTML = '<div class="empty"><span class="empty-mark">⌕</span>' +
    'Choisissez une question ci-dessus ou tapez la vôtre pour démarrer l\'analyse.</div>';
}

async function ask() {
  const query = $("q").value.trim();
  if (!query) return;
  const a = $("answer");
  a.innerHTML = '<div class="prose">Analyse en cours…</div>';
  try {
    const res = await api("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    renderAnswer(res);
  } catch (e) {
    a.innerHTML = '<div class="notfound">Erreur de communication avec l\'API.</div>';
  }
}

function renderAnswer(res) {
  const a = $("answer");
  if (res.mode === "guardrail") {
    a.innerHTML = `<div class="result"><div class="notfound"><b>Information non trouvée.</b> ${esc(res.answer)}</div></div>`;
    return;
  }
  const cls = res.confidence === "élevée" ? "h" : res.confidence === "moyenne" ? "m" : "l";
  let html = `<div class="result"><div class="ans-head"><h3>Réponse</h3><div class="badges">
      <span class="badge mode">${res.mode === "llm" ? "synthèse LLM" + (res.provider ? " · " + res.provider : "") : "extractif"}</span>
      <span class="badge conf ${cls}">confiance : ${res.confidence}</span></div></div>`;
  html += `<div class="prose">${esc(res.answer)}</div>`;
  (res.sources || []).forEach((s) => {
    const pct = Math.round((s.relevance || 0) * 100);
    html += `<div class="card"><div class="card-h">
        <span class="cite">${esc(s.file)}:${s.start}-${s.end}</span>
        <span class="meter"><i style="width:${Math.max(6, pct)}%"></i></span>
        <span class="pct">${pct}%</span></div></div>`;
  });
  if (res.sources && res.sources.length) {
    html += `<div class="sources"><b>Sources :</b><br>` +
      res.sources.map((s) => `<span class="src-tag">${esc(s.file)}:${s.start}-${s.end}</span>`).join("") +
      `</div>`;
  }
  html += `</div>`;
  a.innerHTML = html;
}

init();
