/**
 * My Contributions Page - Collapsible Sections
 * 
 * Handles the "View all" toggle functionality for contribution lists.
 * Shows only 4 items by default, with a button to expand/collapse the rest.
 */

(function() {
    'use strict';

    /**
     * Initialize collapsible sections on the page.
     * Finds all [data-collapsible] containers and sets up toggle behavior.
     */
    function initCollapsibleSections() {
        var containers = document.querySelectorAll('[data-collapsible]');
        
        containers.forEach(function(container) {
            var toggleBtn = container.querySelector('[data-collapsible-toggle]');
            var collapsibleItems = container.querySelectorAll('.collapsible-item');
            
            if (!toggleBtn || collapsibleItems.length === 0) {
                return;
            }
            
            var isExpanded = false;
            
            toggleBtn.addEventListener('click', function() {
                isExpanded = !isExpanded;
                
                collapsibleItems.forEach(function(item) {
                    if (isExpanded) {
                        item.classList.remove('is-hidden');
                    } else {
                        item.classList.add('is-hidden');
                    }
                });
                
                updateToggleButton(toggleBtn, isExpanded);
            });
        });
    }

    /**
     * Update the toggle button text and icon based on expanded state.
     * @param {HTMLElement} btn - The toggle button element
     * @param {boolean} isExpanded - Whether the section is currently expanded
     */
    function updateToggleButton(btn, isExpanded) {
        var icon = btn.querySelector('i');
        var originalText = btn.getAttribute('data-original-text');
        
        if (!originalText) {
            btn.setAttribute('data-original-text', btn.textContent.trim());
            originalText = btn.textContent.trim();
        }
        
        if (isExpanded) {
            if (icon) {
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            }
            btn.innerHTML = '<i class="fas fa-chevron-up me-1"></i> Show less';
        } else {
            if (icon) {
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            }
            btn.innerHTML = '<i class="fas fa-chevron-down me-1"></i> ' + originalText.replace(/^[^\s]+\s*/, '');
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCollapsibleSections);
    } else {
        initCollapsibleSections();
    }
})();
