document.addEventListener('DOMContentLoaded', function () {
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarMenu = document.getElementById('navbarMenu');

    if (navbarToggler && navbarMenu) {
        navbarToggler.addEventListener('click', function () {
            navbarMenu.classList.toggle('active');
        });
    }
});
