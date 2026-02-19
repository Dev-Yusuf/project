(function () {
    'use strict';

    function initPasswordToggle() {
        var checkbox = document.getElementById('show-password-toggle');
        if (!checkbox) return;

        var form = checkbox.closest('form');
        if (!form) return;

        var passwordInputs = form.querySelectorAll('input[type="password"]');
        if (!passwordInputs.length) return;

        function toggleVisibility() {
            var type = checkbox.checked ? 'text' : 'password';
            passwordInputs.forEach(function (input) {
                input.type = type;
            });
        }

        checkbox.addEventListener('change', toggleVisibility);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPasswordToggle);
    } else {
        initPasswordToggle();
    }
})();
