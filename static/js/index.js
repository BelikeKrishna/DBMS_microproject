document.addEventListener('DOMContentLoaded', function() {
    const alertCloseButtons = document.querySelectorAll('.btn-close');
    alertCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.display = 'none';
        });
    });
});