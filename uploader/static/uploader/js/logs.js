// Enhanced log rendering with structured log support
function renderLog(logData) {
    if (typeof logData === 'string') {
        // Legacy string format
        return renderLegacyLog(logData);
    } else if (Array.isArray(logData)) {
        // New structured format
        return renderStructuredLogs(logData);
    }
    return '';
}

function renderLegacyLog(logText) {
    if (!logText || logText.trim() === '') {
        return '<div class="text-muted">No logs available yet...</div>';
    }
    
    // Split into lines and process each line
    const lines = logText.split('\n');
    let html = '';
    
    lines.forEach(line => {
        if (line.trim() === '') return;
        
        // Simple text formatting with basic highlighting
        const formattedMessage = line
            .replace(/(ERROR|CRITICAL|Failed|Error|Exception|Timeout)/gi, '<span style="color: #ff6b6b; font-weight: bold;">$1</span>')
            .replace(/(WARNING|Warning|Warn)/gi, '<span style="color: #ffa726; font-weight: bold;">$1</span>')
            .replace(/(SUCCESS|Completed|Success|Successful)/gi, '<span style="color: #66bb6a; font-weight: bold;">$1</span>')
            .replace(/(❌)/g, '<span style="color: #ff6b6b;">$1</span>')
            .replace(/(⚠️)/g, '<span style="color: #ffa726;">$1</span>')
            .replace(/(✅)/g, '<span style="color: #66bb6a;">$1</span>')
            .replace(/(🚀|🔥)/g, '<span style="color: #ff5722;">$1</span>');
        
        html += `<div class="log-line">${formattedMessage}</div>`;
    });
    
    return html;
}

function renderStructuredLogs(logs) {
    if (!logs || logs.length === 0) {
        return '<div class="text-muted">No logs available yet...</div>';
    }
    
    let html = '';
    
    logs.forEach(log => {
        const message = log.message || '';
        
        // Skip verbose Playwright logs
        if (isVerbosePlaywrightLog(message)) {
            return;
        }
        
        // Simple text formatting
        const formattedMessage = message
            .replace(/(ERROR|CRITICAL|Failed|Error|Exception|Timeout)/gi, '<span style="color: #ff6b6b; font-weight: bold;">$1</span>')
            .replace(/(WARNING|Warning|Warn)/gi, '<span style="color: #ffa726; font-weight: bold;">$1</span>')
            .replace(/(SUCCESS|Completed|Success|Successful)/gi, '<span style="color: #66bb6a; font-weight: bold;">$1</span>')
            .replace(/(❌)/g, '<span style="color: #ff6b6b;">$1</span>')
            .replace(/(⚠️)/g, '<span style="color: #ffa726;">$1</span>')
            .replace(/(✅)/g, '<span style="color: #66bb6a;">$1</span>')
            .replace(/(🚀|🔥)/g, '<span style="color: #ff5722;">$1</span>');
        
        html += `<div class="log-line">${formattedMessage}</div>`;
    });
    
    return html;
}

function isVerbosePlaywrightLog(message) {
    const verboseKeywords = [
        'attempting click action',
        'retrying click action',
        'waiting for element to be visible',
        'scrolling into view',
        'done scrolling',
        'subtree intercepts pointer events',
        'element is visible, enabled and stable',
        'waiting 20ms',
        'waiting 100ms',
        'waiting 500ms',
        'Element is not attached to the DOM',
        'locator.click',
        'locator.fill',
        'locator.type',
        'page.goto',
        'page.wait_for_selector',
        'browser.new_page',
        'context.new_page',
        'retrying click action, attempt',
        'waiting for element to be visible, enabled and stable',
        'element is visible, enabled and stable',
        'scrolling into view if needed',
        'done scrolling',
        'from <div',
        'subtree intercepts pointer events',
        'retrying click action, attempt #',
        'click action',
        'element intercepts pointer events'
    ];
    
    return verboseKeywords.some(keyword => 
        message.toLowerCase().includes(keyword.toLowerCase())
    );
} 

// Enhanced log updater with better error handling and performance
function setupLogUpdater(logUrl, intervalMs = 2000, targetElementId = 'logs') {
    const logsDiv = document.getElementById(targetElementId);
    if (!logsDiv) {
        console.error(`Log container element '${targetElementId}' not found`);
        return;
    }
    
    let lastLogCount = 0;
    let updateInterval;
    let isUpdating = false;
    
    // Function to fetch and update logs
    function updateLogs() {
        if (isUpdating) return; // Prevent concurrent updates
        isUpdating = true;
        
        fetch(logUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                // Handle different log formats
                let logsToRender = '';
                
                if (data.logs && Array.isArray(data.logs)) {
                    // Structured logs
                    logsToRender = renderStructuredLogs(data.logs);
                } else if (data.logs && typeof data.logs === 'string') {
                    // Legacy string format
                    logsToRender = renderLegacyLog(data.logs);
                } else if (data.logs) {
                    // Fallback to legacy format
                    logsToRender = renderLegacyLog(JSON.stringify(data.logs));
                } else {
                    logsToRender = '<div class="text-muted">No logs available yet...</div>';
                }
                
                // Update logs if there's new content or if it's the first load
                if (logsToRender && (lastLogCount === 0 || data.logs && data.logs.length > lastLogCount)) {
                    lastLogCount = data.logs ? data.logs.length : 0;
                    logsDiv.innerHTML = logsToRender;
                    
                    // Auto-scroll to bottom
                    const logContainer = logsDiv.closest('.log-container');
                    if (logContainer) {
                        logContainer.scrollTop = logContainer.scrollHeight;
                    }
                }
                
                // Update progress if provided
                if (data.completion_percentage !== undefined) {
                    updateProgress(data);
                }
                
                // Update status if provided
                if (data.status) {
                    updateStatus(data.status);
                }
                
                // Continue polling if task is still running
                if (data.status === 'RUNNING' || data.status === 'PENDING') {
                    updateInterval = setTimeout(updateLogs, intervalMs);
                } else {
                    // Task completed, do one final update after a short delay
                    setTimeout(() => {
                        updateLogs();
                    }, 2000);
                }
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
                // Show error in log container
                logsDiv.innerHTML += `<div class="log-line">Error fetching logs: ${error.message}</div>`;
                
                // Retry with longer interval on error
                updateInterval = setTimeout(updateLogs, intervalMs * 2);
            })
            .finally(() => {
                isUpdating = false;
            });
    }
    
    function updateProgress(data) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar && data.completion_percentage !== undefined) {
            progressBar.style.width = data.completion_percentage + '%';
        }
        
        if (progressText && data.completed_count !== undefined && data.total_count !== undefined) {
            progressText.textContent = `${data.completed_count} of ${data.total_count} accounts completed (${data.completion_percentage}%)`;
        }
    }
    
    function updateStatus(status) {
        const statusBadge = document.querySelector('.status-badge');
        if (statusBadge) {
            // Remove all status classes
            statusBadge.classList.remove('status-pending', 'status-running', 'status-completed', 'status-failed', 'status-partial');
            
            // Add appropriate class and update content
            statusBadge.classList.add('status-' + status.toLowerCase());
            
            let icon = '';
            let text = '';
            switch(status) {
                case 'PENDING':
                    icon = 'bi-clock';
                    text = 'Pending';
                    break;
                case 'RUNNING':
                    icon = 'bi-play-circle';
                    text = 'Running';
                    break;
                case 'COMPLETED':
                    icon = 'bi-check-circle';
                    text = 'Completed';
                    break;
                case 'PARTIALLY_COMPLETED':
                    icon = 'bi-check-circle-fill';
                    text = 'Partially Completed';
                    statusBadge.classList.add('status-partial');
                    break;
                case 'FAILED':
                    icon = 'bi-x-circle';
                    text = 'Failed';
                    break;
            }
            
            statusBadge.innerHTML = `<i class="bi ${icon}"></i> ${text}`;
        }
    }
    
    // Start the update cycle
    updateLogs();
    
    // Return cleanup function
    return function cleanup() {
        if (updateInterval) {
            clearTimeout(updateInterval);
        }
    };
}

// Initialize log highlighter for static logs (when not using the updater)
document.addEventListener('DOMContentLoaded', function() {
    const logsDiv = document.getElementById('logs');
    if (logsDiv && logsDiv.textContent && !logsDiv.dataset.autoUpdate) {
        logsDiv.innerHTML = renderLog(logsDiv.textContent);
    }
}); 