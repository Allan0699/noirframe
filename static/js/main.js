// ---------------------------------------------------------------------
// Landing page interactions. No build step, no framework -- vanilla JS
// kept deliberately small and readable.
// ---------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initPortfolioFilter();
  initPricingToggle();
  initChatWidget();
  autoDismissFlashes();
});

function autoDismissFlashes() {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => el.remove(), 6000);
  });
}

function initPortfolioFilter() {
  const buttons = document.querySelectorAll(".filter-btn");
  const tiles = document.querySelectorAll(".portfolio-tile");
  if (!buttons.length) return;

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const category = btn.dataset.category;

      tiles.forEach((tile) => {
        const match = category === "all" || tile.dataset.category === category;
        tile.style.display = match ? "" : "none";
      });
    });
  });
}

function initPricingToggle() {
  const toggle = document.getElementById("pricing-toggle");
  if (!toggle) return;
  const switchEl = toggle.querySelector(".pricing-toggle__switch");

  toggle.addEventListener("click", () => {
    const isProject = toggle.dataset.state === "monthly";
    toggle.dataset.state = isProject ? "project" : "monthly";
    switchEl.classList.toggle("on", isProject);

    document.querySelectorAll("[data-price-monthly]").forEach((el) => {
      const monthly = el.dataset.priceMonthly;
      const project = el.dataset.priceProject;
      el.textContent = isProject ? project : monthly;
    });
  });
}

function initChatWidget() {
  const widget = document.getElementById("chat-widget");
  if (!widget) return;

  const toggleBtn = widget.querySelector(".chat-widget__toggle");
  const panel = widget.querySelector(".chat-widget__panel");
  const body = widget.querySelector(".chat-widget__body");
  const form = widget.querySelector(".chat-widget__form");
  const input = form.querySelector("input");

  toggleBtn.addEventListener("click", () => {
    panel.classList.toggle("show");
    if (panel.classList.contains("show")) input.focus();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    appendChatMessage(body, message, "user");
    input.value = "";
    input.disabled = true;

    const thinking = document.createElement("div");
    thinking.className = "chat-msg bot";
    thinking.innerHTML = '<span class="spinner"></span>';
    body.appendChild(thinking);
    body.scrollTop = body.scrollHeight;

    try {
      const res = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      thinking.remove();
      if (!res.ok) {
        appendChatMessage(body, data.error || "Something went wrong. Please try the contact form below.", "bot");
      } else {
        appendChatMessage(body, data.reply, "bot");
      }
    } catch (err) {
      thinking.remove();
      appendChatMessage(body, "Couldn't reach the assistant. Please try the contact form below.", "bot");
    } finally {
      input.disabled = false;
      input.focus();
    }
  });
}

function appendChatMessage(container, text, who) {
  const div = document.createElement("div");
  div.className = `chat-msg ${who}`;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}
