/**
 * TikTok Server Selector - Common JavaScript for all TikTok pages
 * Handles server selection persistence across page reloads
 */

(function() {
    'use strict';

    // Global API_BASE variable - will be updated dynamically
    window.API_BASE = window.API_BASE || 'http://94.141.161.231:8000';

    /**
     * Initialize server selector on page load
     */
    function initializeServerSelector() {
        const serverSelect = document.getElementById('api-server-select');
        if (!serverSelect) {
            console.log('Server selector not found on this page');
            return;
        }

        // Try to restore selected server from localStorage
        const storedServer = localStorage.getItem('selected_tiktok_server');
        if (storedServer) {
            console.log('Restoring server from localStorage:', storedServer);
            
            // Update dropdown to match stored server FIRST
            let foundServer = false;
            for (let i = 0; i < serverSelect.options.length; i++) {
                if (serverSelect.options[i].value === storedServer) {
                    serverSelect.selectedIndex = i;
                    foundServer = true;
                    console.log('Updated dropdown to match stored server:', storedServer);
                    break;
                }
            }
            
            if (!foundServer) {
                console.warn('Stored server not found in options:', storedServer);
                // Fallback to currently selected server
                const selectedOption = serverSelect.options[serverSelect.selectedIndex];
                if (selectedOption) {
                    window.API_BASE = selectedOption.value;
                    localStorage.setItem('selected_tiktok_server', window.API_BASE);
                    console.log('Fallback to dropdown server:', window.API_BASE);
                }
            } else {
                // Update global API_BASE after dropdown is set
                window.API_BASE = storedServer;
            }
        } else {
            // Use currently selected server from dropdown
            const selectedOption = serverSelect.options[serverSelect.selectedIndex];
            if (selectedOption) {
                window.API_BASE = selectedOption.value;
                // Save to localStorage for next time
                localStorage.setItem('selected_tiktok_server', window.API_BASE);
                console.log('No stored server, using dropdown:', window.API_BASE);
            }
        }

        // Update server link display
        updateServerLinkDisplay();

        // Attach change event listener
        serverSelect.addEventListener('change', handleServerChange);
        
        // Force sync with backend session on page load only if needed
        if (window.API_BASE) {
            // Only persist if the server is different from what's in the dropdown
            const currentDropdownServer = serverSelect.options[serverSelect.selectedIndex].value;
            console.log('DEBUG: Page load - API_BASE:', window.API_BASE, 'Dropdown:', currentDropdownServer);
            if (window.API_BASE !== currentDropdownServer) {
                console.log('DEBUG: Persisting server to backend because API_BASE differs from dropdown');
                persistServerToBackend(window.API_BASE);
            } else {
                console.log('DEBUG: Skipping persist - API_BASE matches dropdown');
            }
            
            // Trigger system status update after a short delay to ensure everything is ready
            setTimeout(() => {
                if (typeof window.updateSystemStatus === 'function') {
                    window.updateSystemStatus();
                }
            }, 300);
        }
    }

    /**
     * Handle server selection change
     */
    function handleServerChange(e) {
        const selectedUrl = e.target.value;
        const selectedOption = e.target.options[e.target.selectedIndex];

        console.log('Server changed to:', selectedUrl);

        // Update global API_BASE
        window.API_BASE = selectedUrl;

        // Update server link display
        updateServerLinkDisplay();
        
        // Update navbar server info
        updateNavbarServerInfo();

        // Update description if present
        const statusContainer = e.target.closest('.api-status');
        if (statusContainer) {
            const descElement = statusContainer.querySelector('small:last-child');
            if (descElement && selectedOption) {
                const desc = selectedOption.dataset.desc || 'Custom server';
                descElement.textContent = desc;
            }
        }

        // Persist to localStorage
        localStorage.setItem('selected_tiktok_server', selectedUrl);
        console.log('Saved server to localStorage:', selectedUrl);

        // Update hidden input if present
        const hiddenInput = document.getElementById('selected-server-input');
        if (hiddenInput) {
            hiddenInput.value = selectedUrl;
        }

        // Persist to backend session
        persistServerToBackend(selectedUrl);

        // Trigger custom event for other scripts to react
        window.dispatchEvent(new CustomEvent('tiktok-server-changed', {
            detail: { serverUrl: selectedUrl }
        }));

        // Refresh API status if function exists
        if (typeof window.checkApiStatus === 'function') {
            window.checkApiStatus();
        }
        if (typeof window.checkAllServersStatus === 'function') {
            window.checkAllServersStatus();
        }
        
        // Update system status if function exists
        if (typeof window.updateSystemStatus === 'function') {
            window.updateSystemStatus();
        }
    }

    /**
     * Update server link display
     */
    function updateServerLinkDisplay() {
        const linkElement = document.getElementById('current-server-link');
        if (linkElement && window.API_BASE) {
            linkElement.href = `${window.API_BASE}/docs`;
            // Update only the text node, not the entire content (to preserve the icon)
            const textNode = linkElement.childNodes[linkElement.childNodes.length - 1];
            if (textNode && textNode.nodeType === Node.TEXT_NODE) {
                textNode.textContent = window.API_BASE;
            } else {
                // Fallback: set entire text content
                const icon = linkElement.querySelector('i');
                linkElement.textContent = window.API_BASE;
                if (icon) {
                    linkElement.prepend(icon);
                }
            }
        }
        
        // Update navbar server info
        updateNavbarServerInfo();
    }
    
    /**
     * Update navbar server info (name and IP)
     */
    function updateNavbarServerInfo() {
        const serverSelect = document.getElementById('api-server-select');
        const serverNameElement = document.getElementById('server-name');
        const serverIpElement = document.getElementById('server-ip');
        
        if (serverSelect && serverNameElement && serverIpElement && window.API_BASE) {
            const selectedOption = serverSelect.options[serverSelect.selectedIndex];
            if (selectedOption) {
                serverNameElement.textContent = selectedOption.textContent;
                serverIpElement.textContent = window.API_BASE;
            }
        }
    }

    /**
     * Persist selected server to backend session
     */
    function persistServerToBackend(serverUrl) {
        console.log('DEBUG: persistServerToBackend called with:', serverUrl);
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfToken) {
            console.warn('CSRF token not found, cannot persist to backend');
            return;
        }

        fetch('/api/tiktok/set-active-server/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken.value
            },
            body: `server_url=${encodeURIComponent(serverUrl)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.ok) {
                console.log('DEBUG: Server persisted to backend session:', serverUrl);
            } else {
                console.error('Failed to persist server to backend:', data);
            }
        })
        .catch(error => {
            console.error('Error persisting server to backend:', error);
        });
    }

    /**
     * Get current selected server URL
     */
    window.getTikTokServerUrl = function() {
        return window.API_BASE;
    };

    /**
     * Manually set server URL (for programmatic changes)
     */
    window.setTikTokServerUrl = function(serverUrl) {
        window.API_BASE = serverUrl;
        localStorage.setItem('selected_tiktok_server', serverUrl);
        
        const serverSelect = document.getElementById('api-server-select');
        if (serverSelect) {
            // Update dropdown to match the new server
            for (let i = 0; i < serverSelect.options.length; i++) {
                if (serverSelect.options[i].value === serverUrl) {
                    serverSelect.selectedIndex = i;
                    console.log('Programmatically set server:', serverUrl);
                    break;
                }
            }
        }
        
        updateServerLinkDisplay();
        persistServerToBackend(serverUrl);
        
        // Trigger change event
        window.dispatchEvent(new CustomEvent('tiktok-server-changed', {
            detail: { serverUrl: serverUrl }
        }));
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            // Small delay to ensure all elements are rendered
            setTimeout(initializeServerSelector, 100);
        });
    } else {
        // DOM already loaded, but add small delay to ensure elements are ready
        setTimeout(initializeServerSelector, 100);
    }

})();

