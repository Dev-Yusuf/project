// Dictionary module
const Dictionary = {
    init: function() {
        this.bindEvents();
        this.setupSearch();
    },

    bindEvents: function() {
        document.addEventListener('DOMContentLoaded', () => {
            this.handleSearch();
            this.handlePagination();
        });
    },

    setupSearch: function() {
        const searchButton = document.getElementById('search-button');
        if (searchButton) {
            searchButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleSearch();
            });
        }
    },

    handleSearch: function() {
        const searchForm = document.querySelector('.search-input');
        if (searchForm) {
            searchForm.submit();
        }
    },

    handlePagination: function() {
        const prevButton = document.getElementById('previous-button');
        const nextButton = document.getElementById('next-button');

        if (prevButton) {
            prevButton.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = prevButton.getAttribute('href');
            });
        }

        if (nextButton) {
            nextButton.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = nextButton.getAttribute('href');
            });
        }
    }
};

// Initialize dictionary module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Dictionary.init();
});
