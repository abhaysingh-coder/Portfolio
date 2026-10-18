function toggleMenu() {
    const navLinks = document.getElementById("navLinks");
    const menuButton = document.querySelector(".menu-btn");
    const isOpen = navLinks.classList.toggle("active");
    menuButton.setAttribute("aria-expanded", String(isOpen));
}