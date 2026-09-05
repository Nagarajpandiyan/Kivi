const API = "/api";

const userIdEl = document.getElementById("user-id");
const learnAsr = document.getElementById("learn-asr");
const learnFormatted = document.getElementById("learn-formatted");
const learnResult = document.getElementById("learn-result");
const testAsr = document.getElementById("test-asr");
const testFormatted = document.getElementById("test-formatted");
const testResult = document.getElementById("test-result");
const memoryList = document.getElementById("memory-list");
const traceList = document.getElementById("trace-list");

function userId() { return userIdEl.value.trim() || "user_1"; }

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function statusTagClass(status) {
  return { CANDIDATE: "tag-candidate", ACTIVE: "tag-active", UPDATED: "tag-updated", DEACTIVATED: "tag-deactivated" }[status] || "tag-candidate";
}

function renderMemories(memories) {
  memoryList.innerHTML = "";
  if (!memories.length) {
    memoryList.innerHTML = '<p class="empty-note">No memories yet. Teach it something on the left.</p>';
    return;
  }
  for (const m of memories) {
    const card = document.createElement("div");
    card.className = "memory-card";
    card.innerHTML = `
      <div class="memory-term">
        <span>${escapeHtml(m.source_term)}</span>
        <span class="arrow">&rarr;</span>
        <span>${escapeHtml(m.preferred_term)}</span>
        <span class="tag ${statusTagClass(m.status)}">${m.status}</span>
      </div>
      <div class="memory-meta">
        <span>${m.memory_type}</span>
        <span>confidence ${(m.confidence * 100).toFixed(0)}%</span>
        <span>+${m.supporting_evidence_count} / -${m.conflicting_evidence_count} evidence</span>
        ${m.is_common_word ? '<span>needs context (common word)</span>' : ''}
        ${m.status !== 'DEACTIVATED' ? `<button class="btn-small" data-deactivate="${m.id}">deactivate</button>` : ''}
      </div>`;
    memoryList.appendChild(card);
  }
  memoryList.querySelectorAll("[data-deactivate]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api(`/memory/${btn.dataset.deactivate}/deactivate`, { method: "POST" });
      refreshMemories();
    });
  });
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function refreshMemories() {
  const memories = await api(`/memory?user_id=${encodeURIComponent(userId())}`);
  renderMemories(memories);
}

document.getElementById("learn-btn").addEventListener("click", async () => {
  const asr = learnAsr.value.trim();
  const formatted = learnFormatted.value.trim();
  if (!asr || !formatted) return;
  const result = await api("/memory/learn", {
    method: "POST",
    body: JSON.stringify({ user_id: userId(), asr, formatted }),
  });
  const created = result.memories_created.length;
  const updated = result.memories_updated.length;
  const rejected = result.candidates_rejected.length;
  learnResult.innerHTML = `<p class="reason">
    ${result.candidates_found} candidate word(s) found in the diff &middot;
    ${created} memory created &middot; ${updated} memory updated &middot; ${rejected} rejected as ordinary formatting
    ${rejected ? '<br>' + result.candidates_rejected.map(r => `"${escapeHtml(r.source_term)}" &rarr; "${escapeHtml(r.preferred_term)}": ${escapeHtml(r.reason)}`).join('<br>') : ''}
  </p>`;
  refreshMemories();
});

document.getElementById("test-btn").addEventListener("click", async () => {
  const asr = testAsr.value.trim();
  const formatted = testFormatted.value.trim();
  if (!asr || !formatted) return;
  const result = await api("/transcript/process", {
    method: "POST",
    body: JSON.stringify({ user_id: userId(), asr, formatted }),
  });
  testResult.innerHTML = `
    <div class="output-line">${escapeHtml(result.output)}</div>
    <p class="reason">
      <span class="tag ${result.decision === 'APPLY' ? 'tag-apply' : 'tag-ignore'}">${result.decision}</span>
      &nbsp;${escapeHtml(result.reason)}
    </p>`;
  renderTrace(result.decisions);
  refreshMemories();
});

function renderTrace(decisions) {
  traceList.innerHTML = "";
  if (!decisions.length) {
    traceList.innerHTML = '<p class="empty-note">No decision trace yet. Process a transcript above.</p>';
    return;
  }
  for (const d of decisions) {
    const card = document.createElement("div");
    card.className = "trace-card";
    const term = d.source_term ? `${escapeHtml(d.source_term)} &rarr; ${escapeHtml(d.preferred_term)}` : "(no memory matched)";
    card.innerHTML = `
      <div class="trace-head">
        <span class="tag ${d.decision === 'APPLY' ? 'tag-apply' : 'tag-ignore'}">${d.decision}</span>
        <span>${term}</span>
        ${d.confidence != null ? `<span>${(d.confidence * 100).toFixed(0)}%</span>` : ''}
      </div>
      <p class="reason">${escapeHtml(d.reason)}</p>`;
    traceList.appendChild(card);
  }
}

document.getElementById("reset-btn").addEventListener("click", async () => {
  if (!confirm("Reset all memories, evidence, and decisions for this demo?")) return;
  await api("/reset", { method: "POST" });
  memoryList.innerHTML = '<p class="empty-note">No memories yet. Teach it something on the left.</p>';
  traceList.innerHTML = "";
  learnResult.innerHTML = "";
  testResult.innerHTML = "";
});

refreshMemories();
