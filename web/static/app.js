let config = {};
let currentSessionId = null;

const $ = (id) => document.getElementById(id);

function fillSelect(selectEl, models, keepFirst = true) {
  const first = keepFirst ? selectEl.options[0]?.outerHTML : "";
  selectEl.innerHTML = first || "";
  models.forEach((id) => {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = id;
    selectEl.appendChild(opt);
  });
}

async function loadOllamaModels(apiBase, statusEl) {
  const base = (apiBase || "").trim();
  if (!base) {
    if (statusEl) {
      statusEl.textContent = "Indica la URL del servidor Ollama.";
      statusEl.className = "models-status err";
    }
    return [];
  }
  if (statusEl) {
    statusEl.textContent = "Consultando /v1/models…";
    statusEl.className = "models-status";
  }
  try {
    const res = await fetch(`/api/ollama/models?url=${encodeURIComponent(base)}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (statusEl) {
      statusEl.textContent = `${data.count} modelo(s) desde ${data.source}`;
      statusEl.className = "models-status ok";
    }
    return data.models;
  } catch (e) {
    if (statusEl) {
      statusEl.textContent = `Error: ${e.message}`;
      statusEl.className = "models-status err";
    }
    return [];
  }
}

async function refreshModels() {
  const models = await loadOllamaModels($("enhance-api-base").value, $("models-status"));
  if (!models.length) return;

  const enhanceSelect = $("enhance-model");
  const defaultEnhance = config.default_enhance_model;
  fillSelect(enhanceSelect, models, false);
  if (defaultEnhance && models.includes(defaultEnhance)) {
    enhanceSelect.value = defaultEnhance;
  }

  const targetSelect = $("target-model");
  const prev = targetSelect.value;
  const registryIds = new Set((config.target_models || []).map((m) => m.id));
  const merged = [...new Set([...models, ...config.target_models.map((m) => m.id)])];
  fillSelect(targetSelect, merged, true);
  if (prev && [...targetSelect.options].some((o) => o.value === prev)) {
    targetSelect.value = prev;
  } else if (registryIds.size) {
    const firstReg = merged.find((m) => registryIds.has(m));
    if (firstReg) targetSelect.value = firstReg;
  }
}

function normalizeRadioMode(mode) {
  if (mode.hint) return mode;
  const match = mode.label.match(/^(.+?)\s*\((.+)\)\s*$/);
  if (match) {
    return { ...mode, label: match[1].trim(), hint: match[2].trim() };
  }
  return mode;
}

function createRadioOption(name, mode, checked) {
  const item = normalizeRadioMode(mode);
  const label = document.createElement("label");
  label.className = "radio-option";

  const radio = document.createElement("input");
  radio.type = "radio";
  radio.name = name;
  radio.value = item.id;
  radio.checked = checked;

  const text = document.createElement("span");
  text.className = "radio-text";

  const title = document.createElement("span");
  title.className = "radio-title";
  title.textContent = item.label;
  text.appendChild(title);

  if (item.hint) {
    const hint = document.createElement("span");
    hint.className = "radio-hint";
    hint.textContent = item.hint;
    text.appendChild(hint);
  }

  label.appendChild(radio);
  label.appendChild(text);
  return label;
}

function setupOutputFormat() {
  const container = $("output-format");
  container.innerHTML = "";
  config.output_modes.forEach((m, i) => {
    container.appendChild(createRadioOption("output_mode", m, i === 0));
  });
  container.querySelectorAll('input[name="output_mode"]').forEach((el) => {
    el.addEventListener("change", toggleProfileVisibility);
  });
  toggleProfileVisibility();
}

function setupEnhanceYesNo() {
  const container = $("enhance-yesno");
  container.innerHTML = "";
  config.enhance_modes.forEach((m) => {
    container.appendChild(createRadioOption("enhance_mode", m, m.id === "off"));
  });
  container.querySelectorAll('input[name="enhance_mode"]').forEach((el) => {
    el.addEventListener("change", toggleEnhanceModel);
  });
  toggleEnhanceModel();
}

function getOutputMode() {
  const checked = document.querySelector('input[name="output_mode"]:checked');
  return checked ? checked.value : "sequential";
}

function toggleProfileVisibility() {
  const seq = getOutputMode() === "sequential";
  $("profile-wrap").classList.toggle("hidden", !seq);
}

function toggleEnhanceModel() {
  const on = getEnhanceMode() === "on";
  $("enhance-model-wrap").classList.toggle("hidden", !on);
}

function setupSkills() {
  const container = $("skills");
  container.innerHTML = "";
  (config.skills || []).forEach((item) => {
    const label = document.createElement("label");
    label.className = "checkbox-option";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "skills";
    checkbox.value = item.id;
    checkbox.dataset.alwaysOn = item.always_on ? "1" : "0";
    if (item.always_on) {
      checkbox.checked = true;
      checkbox.disabled = true;
    }

    const text = document.createElement("span");
    text.className = "checkbox-text";
    const title = document.createElement("span");
    title.className = "checkbox-title";
    title.textContent = item.id;
    text.appendChild(title);
    if (item.hint) {
      const hint = document.createElement("span");
      hint.className = "checkbox-hint";
      hint.textContent = item.hint;
      text.appendChild(hint);
    }

    label.appendChild(checkbox);
    label.appendChild(text);
    container.appendChild(label);
  });
}

function getSelectedSkills() {
  const checked = [...document.querySelectorAll('input[name="skills"]:checked')]
    .map((el) => el.value)
    .filter((id) => id !== "local-agent-persistence");
  return checked.length ? checked : null;
}

function applySuggestedSkills(skillIds) {
  if (!skillIds || !skillIds.length) return;
  document.querySelectorAll('input[name="skills"]').forEach((el) => {
    if (el.disabled) return;
    el.checked = skillIds.includes(el.value);
  });
}

async function loadConfig() {
  const res = await fetch("/api/config");
  config = await res.json();

  $("enhance-api-base").value = config.default_enhance_api_base;

  setupSkills();

  const agent = $("agent");
  config.agents.forEach((a) => {
    const opt = document.createElement("option");
    opt.value = a;
    opt.textContent = a;
    agent.appendChild(opt);
  });

  setupOutputFormat();
  setupEnhanceYesNo();

  fillSelect($("enhance-model"), config.enhance_models, false);
  $("enhance-model").value = config.default_enhance_model;

  fillSelect(
    $("target-model"),
    config.target_models.map((m) => m.id),
    true,
  );

  await refreshModels();
}

function getObjective() {
  return $("objective").value.trim();
}

function getEnhanceMode() {
  const checked = document.querySelector('input[name="enhance_mode"]:checked');
  return checked ? checked.value : "off";
}

function setStatus(text, type = "idle") {
  const el = $("status");
  el.textContent = text;
  el.className = `status ${type}`;
}

function renderAnalysis(data) {
  const block = $("analysis-result");
  block.classList.remove("hidden");
  const suggested = data.sequential ? "subtareas" : "prompt completo";
  const skillsText = (data.skills || [data.skill]).join(" + ");
  block.innerHTML = `
    <h3>Análisis</h3>
    <dl>
      <dt>Tipo</dt><dd>${data.task_type}</dd>
      <dt>Complejidad</dt><dd>${data.complexity}</dd>
      <dt>Skills sugeridas</dt><dd>${skillsText}</dd>
      <dt>Modelo</dt><dd>${data.model}</dd>
      <dt>URLs</dt><dd>${data.urls.length ? data.urls.join("<br>") : "ninguna"}</dd>
      <dt>Multi-agente</dt><dd>${data.is_multi_agent ? "Sí" : "No"}</dd>
      <dt>Formato sugerido</dt><dd>${suggested}${data.sequential ? ` (perfil ${data.profile})` : ""}</dd>
    </dl>
  `;
  if (data.sequential) {
    const seqRadio = document.querySelector('input[name="output_mode"][value="sequential"]');
    if (seqRadio) seqRadio.checked = true;
    if (data.profile) $("profile").value = data.profile;
    toggleProfileVisibility();
  }
  applySuggestedSkills(data.skills || [data.skill]);
}

function renderGenerate(data) {
  currentSessionId = data.session_id;
  $("generate-result").classList.remove("hidden");
  $("download-actions").classList.remove("hidden");

  const meta = data.metadata || {};
  const skillsText = (meta.skills || [meta.skill]).filter(Boolean).join(" + ") || "—";
  $("metadata").innerHTML = `
    <h3>Generado (${data.mode})</h3>
    <dl>
      <dt>Sesión</dt><dd>${data.session_id}</dd>
      <dt>Skills</dt><dd>${skillsText}</dd>
      <dt>Modelo agente</dt><dd>${meta.model || "—"}</dd>
      <dt>Enriquecido</dt><dd>${meta.enhanced ? "Sí" : "No"}</dd>
      ${meta.steps_enhanced != null ? `<dt>Tareas enriquecidas</dt><dd>${meta.steps_enhanced}/${meta.step_count || "—"}</dd>` : ""}
      ${meta.enhance_model ? `<dt>Modelo LLM</dt><dd>${meta.enhance_model}</dd>` : ""}
      ${meta.profile ? `<dt>Perfil</dt><dd>${meta.profile}</dd>` : ""}
    </dl>
  `;

  const warnings = $("warnings");
  if (data.warnings && data.warnings.length) {
    warnings.innerHTML = data.warnings.map((w) => `⚠ ${w}`).join("<br>");
    warnings.classList.remove("hidden");
  } else {
    warnings.innerHTML = "";
    warnings.classList.add("hidden");
  }

  const fileList = $("file-list");
  fileList.innerHTML = "";
  (data.files || []).forEach((file) => {
    const card = document.createElement("div");
    card.className = "file-card";
    const preview = file.content.slice(0, 1500);
    const truncated = file.content.length > 1500 ? "\n\n… (vista previa truncada)" : "";
    card.innerHTML = `
      <header>
        <span><strong>${file.name}</strong> — ${file.title || ""}</span>
        <button type="button" class="btn-dl" data-file="${file.name}">Descargar</button>
      </header>
      <pre>${escapeHtml(preview + truncated)}</pre>
    `;
    card.querySelector(".btn-dl").addEventListener("click", () => {
      window.location.href = `/api/download/${data.session_id}/${file.name}`;
    });
    fileList.appendChild(card);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function getGeneratePayload() {
  return {
    objective: getObjective(),
    agent: $("agent").value,
    model: $("target-model").value || null,
    skill: null,
    skills: getSelectedSkills(),
    context_limit: parseInt($("context-limit").value, 10) || 32768,
    enhance_mode: getEnhanceMode(),
    enhance_model: $("enhance-model").value || null,
    enhance_api_base: $("enhance-api-base").value || null,
    output_mode: getOutputMode(),
    profile: getOutputMode() === "sequential" ? ($("profile").value || null) : null,
  };
}

$("btn-analyze").addEventListener("click", async () => {
  const objective = getObjective();
  if (!objective) {
    setStatus("Escribe un objetivo.", "error");
    return;
  }
  setStatus("Analizando…", "loading");
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderAnalysis(data);
    setStatus("Análisis completado.", "ok");
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  }
});

$("btn-generate").addEventListener("click", async () => {
  const objective = getObjective();
  if (!objective) {
    setStatus("Escribe un objetivo.", "error");
    return;
  }
  setStatus("Generando prompts… (puede tardar si hay enriquecimiento LLM)", "loading");
  $("generate-result").classList.add("hidden");
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getGeneratePayload()),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderGenerate(data);
    setStatus(`Generación completada (${data.files.length} archivo(s)).`, "ok");
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  }
});

$("btn-download-zip").addEventListener("click", () => {
  if (!currentSessionId) return;
  window.location.href = `/api/download/${currentSessionId}/zip`;
});

$("btn-refresh-models").addEventListener("click", () => refreshModels());
$("btn-refresh-target").addEventListener("click", () => refreshModels());

loadConfig().catch((e) => setStatus(`Error cargando config: ${e.message}`, "error"));
