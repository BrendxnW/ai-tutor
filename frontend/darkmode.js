document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("darkToggle");

    toggle.checked = localStorage.getItem("darkMode") === "true";
    document.body.classList.toggle("dark", toggle.checked);
    
    toggle.addEventListener("change", () => {
        document.body.classList.toggle("dark", toggle.checked);
        localStorage.setItem("darkMode", toggle.checked);
    });
});