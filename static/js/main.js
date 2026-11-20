document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".main-nav");
  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!expanded));
      nav.classList.toggle("nav-open", !expanded);
    });
  }

  const emergencyDialog = document.getElementById("emergency-dialog");
  document.querySelectorAll("[data-open-emergency]").forEach((button) => {
    button.addEventListener("click", () => emergencyDialog?.showModal());
  });
  document.querySelectorAll("[data-close-emergency]").forEach((button) => {
    button.addEventListener("click", () => emergencyDialog?.close());
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
});
