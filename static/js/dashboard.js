// ---------------------------------------------------------------------
// Dashboard interactions shared by admin / team-lead / employee / client
// areas: the notification bell, and the two Gemini-powered AI actions.
// ---------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initNotifications();
  initCostEstimator();
  initSummaryGenerator();
});

function initNotifications() {
  const bellBtn = document.getElementById("bell-btn");
  if (!bellBtn) return;
  const panel = document.getElementById("notif-panel");
  const dot = document.getElementById("bell-dot");
  const list = document.getElementById("notif-list");

  async function refresh() {
    try {
      const res = await fetch("/api/notifications");
      if (!res.ok) return;
      const data = await res.json();
      dot.classList.toggle("show", data.unread > 0);
      dot.textContent = data.unread > 9 ? "9+" : data.unread;

      if (!data.items.length) {
        list.innerHTML = '<div class="notif-empty">You\'re all caught up.</div>';
        return;
      }
      list.innerHTML = data.items
        .map(
          (n) => `<a class="notif-item" href="${n.link || "#"}" style="display:block">
            ${escapeHtml(n.body)}
            <time>${n.created_at}</time>
          </a>`
        )
        .join("");
    } catch (e) { /* fail quietly -- notifications are non-critical */ }
  }

  bellBtn.addEventListener("click", async () => {
    panel.classList.toggle("show");
    if (panel.classList.contains("show")) {
      await fetch("/api/notifications/read-all", { method: "POST" });
      dot.classList.remove("show");
    }
  });

  document.addEventListener("click", (e) => {
    if (!bellBtn.parentElement.contains(e.target)) panel.classList.remove("show");
  });

  refresh();
  setInterval(refresh, 20000);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ----------------------------------------------------------- cost estimator
function initCostEstimator() {
  const form = document.getElementById("cost-estimate-form");
  if (!form) return;
  const resultBox = document.getElementById("cost-estimate-result");
  const btn = form.querySelector("button[type=submit]");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      category: form.category.value,
      scope: form.scope.value,
      duration_hint: form.duration_hint.value,
    };
    setLoading(btn, true);
    resultBox.innerHTML = "";

    try {
      const res = await fetch("/api/ai/cost-estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultBox.innerHTML = `<div class="ai-error">${escapeHtml(data.error)}</div>`;
      } else {
        resultBox.innerHTML = `<div class="ai-result">${escapeHtml(data.estimate)}</div>`;
      }
    } catch (err) {
      resultBox.innerHTML = `<div class="ai-error">Request failed. Check your connection and try again.</div>`;
    } finally {
      setLoading(btn, false);
    }
  });
}

// --------------------------------------------------------- summary generator
function initSummaryGenerator() {
  const btn = document.getElementById("generate-summary-btn");
  if (!btn) return;
  const resultBox = document.getElementById("summary-result");
  const projectId = btn.dataset.projectId;

  btn.addEventListener("click", async () => {
    setLoading(btn, true);
    try {
      const res = await fetch(`/api/ai/project-summary/${projectId}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        resultBox.innerHTML = `<div class="ai-error">${escapeHtml(data.error)}</div>`;
      } else {
        resultBox.innerHTML = `<div class="ai-result">${escapeHtml(data.summary)}</div>`;
      }
    } catch (err) {
      resultBox.innerHTML = `<div class="ai-error">Request failed. Check your connection and try again.</div>`;
    } finally {
      setLoading(btn, false);
    }
  });
}

function setLoading(btn, isLoading) {
  if (!btn) return;
  btn.disabled = isLoading;
  if (isLoading) {
    btn.dataset.label = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Working...';
  } else if (btn.dataset.label) {
    btn.innerHTML = btn.dataset.label;
  }
}
