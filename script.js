(function () {
  "use strict";

  // ── Theme Toggle ──────────────────────────────────────────────────
  const root = document.documentElement;
  const themeBtn = document.getElementById("theme-toggle");

  function getPreferredTheme() {
    const stored = localStorage.getItem("cw-guide-theme");
    if (stored) return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      root.setAttribute("data-theme", "dark");
    } else {
      root.removeAttribute("data-theme");
    }
    if (themeBtn) {
      themeBtn.textContent = theme === "dark" ? "\u2600 Light" : "\u263E Dark";
    }
  }

  applyTheme(getPreferredTheme());

  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      const current = root.hasAttribute("data-theme") ? "dark" : "light";
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("cw-guide-theme", next);
      applyTheme(next);
    });
  }

  // Respect OS changes
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", function (e) {
      if (!localStorage.getItem("cw-guide-theme")) {
        applyTheme(e.matches ? "dark" : "light");
      }
    });

  // ── Scroll-Spy ────────────────────────────────────────────────────
  var sections = document.querySelectorAll("section[id]");
  var navLinks = document.querySelectorAll('.guide-nav a[href^="#"]');

  function updateActive() {
    var current = "";
    for (var i = 0; i < sections.length; i++) {
      if (sections[i].getBoundingClientRect().top <= 80) {
        current = sections[i].id;
      }
    }
    navLinks.forEach(function (a) {
      a.classList.toggle(
        "active",
        a.getAttribute("href") === "#" + current
      );
    });
  }
  window.addEventListener("scroll", updateActive, { passive: true });
  updateActive();

  // ── Mobile Nav Toggle ─────────────────────────────────────────────
  var nav = document.querySelector(".guide-nav");
  var toggle = document.querySelector(".nav-toggle");

  if (toggle) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("open");
      toggle.textContent = nav.classList.contains("open")
        ? "\u2715"
        : "\u2630";
    });
    navLinks.forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.innerWidth <= 768) {
          nav.classList.remove("open");
          toggle.textContent = "\u2630";
        }
      });
    });
  }

  // ── Copy-to-Clipboard on Swatches ─────────────────────────────────
  document.querySelectorAll(".swatch").forEach(function (el) {
    el.addEventListener("click", function () {
      var hex = el.querySelector(".swatch-hex").textContent;
      navigator.clipboard.writeText(hex).then(function () {
        var fb = el.querySelector(".copy-feedback");
        if (fb) {
          fb.textContent = "Copied!";
          fb.classList.add("show");
          setTimeout(function () {
            fb.classList.remove("show");
          }, 1200);
        }
        el.style.outline = "2px solid #336699";
        setTimeout(function () {
          el.style.outline = "";
        }, 600);
      });
    });
  });

  // ── Copy-to-Clipboard on Code Blocks ──────────────────────────────
  document.querySelectorAll("pre").forEach(function (pre) {
    var btn = document.createElement("button");
    btn.className = "code-copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var code = pre.querySelector("code");
      var text = code ? code.textContent : pre.textContent;
      navigator.clipboard.writeText(text).then(function () {
        btn.textContent = "Copied!";
        setTimeout(function () {
          btn.textContent = "Copy";
        }, 1500);
      });
    });
    pre.appendChild(btn);
  });

  // ── Interactive Demos ─────────────────────────────────────────────
  // Chevron rotation
  document.querySelectorAll(".chevron-arrow").forEach(function (el) {
    el.addEventListener("click", function () {
      el.classList.toggle("rotated");
    });
  });

  // Badge toggle demo
  document.querySelectorAll(".cw-badge-interactive").forEach(function (el) {
    el.addEventListener("click", function () {
      var isStock = el.classList.contains("stock");
      el.classList.toggle("stock", !isStock);
      el.classList.toggle("not-stock", isStock);
      el.textContent = isStock ? "NOT-STOCK" : "STOCK";
      // Trigger a mini toast to show the pattern
      var toast = document.createElement("div");
      toast.className = "live-toast success";
      toast.innerHTML = "Status toggled \u2714";
      document.body.appendChild(toast);
      setTimeout(function () {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s";
        setTimeout(function () { toast.remove(); }, 300);
      }, 1500);
    });
  });

  // Toast trigger with undo
  var toastBtn = document.getElementById("toast-trigger");
  if (toastBtn) {
    toastBtn.addEventListener("click", function () {
      var toast = document.createElement("div");
      toast.className = "live-toast success";
      var undoBtn = document.createElement("button");
      undoBtn.className = "cw-toast-action";
      undoBtn.textContent = "Undo";
      undoBtn.addEventListener("click", function () { toast.remove(); });
      toast.appendChild(document.createTextNode("Changes saved \u2714 "));
      toast.appendChild(undoBtn);
      document.body.appendChild(toast);
      setTimeout(function () {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s";
        setTimeout(function () { toast.remove(); }, 300);
      }, 4000);
    });
  }
})();
