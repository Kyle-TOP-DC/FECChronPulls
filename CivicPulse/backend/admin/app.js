const $ = (sel) => document.querySelector(sel);

// ---------- auth + fetch helper ----------
$("#adminToken").value = localStorage.getItem("civicpulse_admin_token") || "";

function saveToken() {
  localStorage.setItem("civicpulse_admin_token", $("#adminToken").value.trim());
  toast("Token saved");
  refreshAll();
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": localStorage.getItem("civicpulse_admin_token") || "",
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

// ---------- tabs ----------
document.querySelectorAll("nav button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll("main > section").forEach((s) => (s.hidden = true));
    $(`#tab-${btn.dataset.tab}`).hidden = false;
    refreshAll();
  });
});

// ---------- articles ----------
async function loadArticles() {
  const articles = await api("/api/admin/articles");
  $("#articlesTable tbody").innerHTML = articles
    .map(
      (a) => `<tr>
        <td><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a>
          ${a.admin_note ? `<div class="muted">📝 ${esc(a.admin_note)}</div>` : ""}</td>
        <td>${esc(a.source || "—")}</td>
        <td><span class="badge ${a.published ? "on" : "off"}">${a.published ? "published" : "hidden"}</span></td>
        <td class="muted">${fmtDate(a.created_at)}</td>
        <td><button class="small" onclick="togglePublish(${a.id}, ${!a.published})">
          ${a.published ? "Unpublish" : "Publish"}</button></td>
      </tr>`
    )
    .join("");
  $("#p-article").innerHTML =
    `<option value="">(no article)</option>` +
    articles
      .filter((a) => a.published)
      .map((a) => `<option value="${a.id}">${esc(a.title)}</option>`)
      .join("");
}

async function createArticle() {
  const tags = $("#a-tags").value.split(",").map((t) => t.trim()).filter(Boolean);
  try {
    await api("/api/admin/articles", {
      method: "POST",
      body: JSON.stringify({
        title: $("#a-title").value.trim(),
        source: $("#a-source").value.trim() || null,
        url: $("#a-url").value.trim(),
        image_url: $("#a-image").value.trim() || null,
        summary: $("#a-summary").value.trim() || null,
        article_text: $("#a-text").value.trim() || null,
        admin_note: $("#a-note").value.trim() || null,
        tags,
        published: true,
      }),
    });
    ["a-title", "a-source", "a-url", "a-image", "a-summary", "a-text", "a-note", "a-tags"]
      .forEach((id) => (document.getElementById(id).value = ""));
    toast("Article published");
    loadArticles();
  } catch (e) {
    toast(`Error: ${e.message}`);
  }
}

async function togglePublish(id, published) {
  try {
    await api(`/api/admin/articles/${id}`, { method: "PATCH", body: JSON.stringify({ published }) });
    loadArticles();
  } catch (e) {
    toast(`Error: ${e.message}`);
  }
}

async function sendPush() {
  try {
    const articleId = $("#p-article").value;
    const result = await api("/api/admin/push", {
      method: "POST",
      body: JSON.stringify({
        article_id: articleId ? Number(articleId) : null,
        title: $("#p-title").value.trim(),
        note: $("#p-note").value.trim(),
      }),
    });
    toast(result.detail || `Push sent to ${result.sent} device(s), ${result.failed} failed`);
  } catch (e) {
    toast(`Error: ${e.message}`);
  }
}

// ---------- engagement ----------
async function loadEngagement() {
  const rows = await api("/api/admin/stats/engagement");
  $("#engagementTable tbody").innerHTML = rows
    .map(
      (r) => `<tr>
        <td>${esc(r.title)} ${r.published ? "" : '<span class="badge off">hidden</span>'}</td>
        <td>${r.views}</td><td>${r.reads}</td><td>${r.shares}</td>
        <td>${r.action_opens}</td><td><strong>${r.messages_sent}</strong></td>
      </tr>`
    )
    .join("");
}

// ---------- contacts ----------
async function loadContacts() {
  const rows = await api("/api/admin/stats/contacts");
  $("#contactsTable tbody").innerHTML = rows.length
    ? rows
        .map(
          (r) => `<tr>
            <td>${esc(r.rep_name)}</td>
            <td>${esc(r.rep_role || "—")}</td>
            <td>${esc(r.rep_state || "—")}</td>
            <td><strong>${r.message_count}</strong></td>
            <td>${r.replied_count}</td>
            <td class="muted">${fmtDate(r.last_contacted)}</td>
            <td><button class="small" onclick="showOffice('${esc(r.rep_bioguide_id)}', '${esc(r.rep_name)}')">View messages</button></td>
          </tr>`
        )
        .join("")
    : `<tr><td colspan="7" class="muted">No congressional offices contacted yet.</td></tr>`;
}

async function showOffice(bioguideId, name) {
  const messages = await api(`/api/admin/messages?rep_bioguide_id=${encodeURIComponent(bioguideId)}`);
  $("#officeDetail").hidden = false;
  $("#officeDetailTitle").textContent = `Messages to ${name}`;
  $("#officeMessages").innerHTML = messages
    .map(
      (m) => `<div style="margin-bottom:16px">
        <div><strong>${esc(m.subject)}</strong>
          <span class="badge ${m.status}">${esc(m.status)}</span>
          <span class="muted">· ${fmtDate(m.created_at)} · via ${esc(m.delivery_method)}</span></div>
        <details><summary>Show message</summary><pre class="msgbody">${esc(m.body)}</pre></details>
        ${m.office_reply
          ? `<div class="replybox">↩︎ ${esc(m.office_reply)}</div>`
          : `<details><summary>Log office reply</summary>
              <textarea id="reply-${m.id}" placeholder="Paste the office's response…"></textarea>
              <p><button class="small" onclick="logReply(${m.id})">Save reply &amp; notify user</button></p>
            </details>`}
      </div>`
    )
    .join("");
  $("#officeDetail").scrollIntoView({ behavior: "smooth" });
}

async function logReply(messageId) {
  const text = document.getElementById(`reply-${messageId}`).value.trim();
  if (!text) return;
  try {
    await api(`/api/admin/messages/${messageId}/reply`, {
      method: "POST",
      body: JSON.stringify({ office_reply: text }),
    });
    toast("Reply logged — user notified");
    loadContacts();
    $("#officeDetail").hidden = true;
  } catch (e) {
    toast(`Error: ${e.message}`);
  }
}

// ---------- candidates ----------
async function loadCandidates() {
  const rows = await api("/api/candidates");
  $("#candidatesTable tbody").innerHTML = rows
    .map(
      (c) => `<tr>
        <td>${esc(c.name)}${c.blurb ? `<div class="muted">${esc(c.blurb)}</div>` : ""}</td>
        <td>${esc(c.office)}</td><td>${esc(c.state)}</td><td>${esc(c.party || "—")}</td>
        <td><button class="small danger" onclick="removeCandidate(${c.id})">Remove</button></td>
      </tr>`
    )
    .join("");
}

async function createCandidate() {
  try {
    await api("/api/admin/candidates", {
      method: "POST",
      body: JSON.stringify({
        name: $("#c-name").value.trim(),
        office: $("#c-office").value.trim(),
        state: $("#c-state").value.trim().toUpperCase(),
        party: $("#c-party").value.trim() || null,
        website: $("#c-website").value.trim() || null,
        donate_url: $("#c-donate").value.trim() || null,
        blurb: $("#c-blurb").value.trim() || null,
      }),
    });
    ["c-name", "c-office", "c-state", "c-party", "c-website", "c-donate", "c-blurb"]
      .forEach((id) => (document.getElementById(id).value = ""));
    toast("Candidate added");
    loadCandidates();
  } catch (e) {
    toast(`Error: ${e.message}`);
  }
}

async function removeCandidate(id) {
  try {
    await api(`/api/admin/candidates/${id}`, { method: "DELETE" });
    loadCandidates();
  } catch (e) {
    toast(`Error: ${e.message}`);
  }
}

// ---------- refresh ----------
function refreshAll() {
  loadArticles().catch((e) => toast(`Articles: ${e.message}`));
  loadEngagement().catch(() => {});
  loadContacts().catch(() => {});
  loadCandidates().catch(() => {});
}

refreshAll();
