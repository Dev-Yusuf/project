// Main application entry point
const App = {
    modules: {
        dictionary: null
    },

    init: function() {
        // Initialize modules based on current page
        const currentPage = this.getCurrentPage();
        this.loadModules(currentPage);
    },

    getCurrentPage: function() {
        // Get current page from URL
        const path = window.location.pathname;
        if (path.includes('dictionary')) {
            return 'dictionary';
        }
        return 'main';
    },

    loadModules: function(page) {
        switch (page) {
            case 'dictionary':
                this.modules.dictionary = new Dictionary();
                this.modules.dictionary.init();
                break;
            default:
                // Add other page-specific modules here
                break;
        }
    }
};

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
