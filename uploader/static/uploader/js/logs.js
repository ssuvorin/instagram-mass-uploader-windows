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
    // Apply color formatting to legacy log text
    return logText
        // Format emoji/symbol prefixes
        .replace(/(\[.*?\])/g, '<span style="color: #87CEFA;">$1</span>')  // Light blue for timestamps
        .replace(/(❌)/g, '<span style="color: #FF6347; font-weight: bold;">$1</span>')  // Tomato red for errors
        .replace(/(⚠️)/g, '<span style="color: #FFA500; font-weight: bold;">$1</span>')  // Orange for warnings
        .replace(/(✅)/g, '<span style="color: #90EE90; font-weight: bold;">$1</span>')  // Light green for success
        .replace(/(🔄|🔍|⏳|🌐|🔒)/g, '<span style="color: #ADD8E6;">$1</span>')  // Light blue for info/process symbols
        .replace(/(👤|📝|🎬|📋|📎|👥|👆)/g, '<span style="color: #FFD700;">$1</span>')  // Gold for user actions
        .replace(/(⌨️|🖱️|🔑)/g, '<span style="color: #FF69B4;">$1</span>')  // Hot pink for input actions
        .replace(/(🚀|🔥)/g, '<span style="font-size: 1.1em; color: #FF4500;">$1</span>')  // Orange-red and larger for important actions
        // Format keywords
        .replace(/(ERROR|CRITICAL|Failed|Error|Failed|Exception|Timeout)/gi, '<span style="color: #FF6347; font-weight: bold;">$1</span>')  // Red for errors
        .replace(/(WARNING|Warning|Warn)/gi, '<span style="color: #FFA500; font-weight: bold;">$1</span>')  // Orange for warnings
        .replace(/(SUCCESS|Completed|Success|Successful)/gi, '<span style="color: #90EE90; font-weight: bold;">$1</span>')  // Green for success
        .replace(/(INFO|Starting|Processing|Loading|Initialized)/gi, '<span style="color: #87CEFA;">$1</span>')  // Blue for info
        .replace(/(Username|Password|Login|Cookie)/gi, '<span style="color: #BA55D3;">$1</span>')  // Purple for auth items
        .replace(/(\n)/g, '<br>');  // Replace newlines with <br> tags
}

function renderStructuredLogs(logs) {
    if (!logs || logs.length === 0) {
        return '<div class="text-muted">No logs available yet...</div>';
    }
    
    let html = '';
    
    logs.forEach(log => {
        const timestamp = log.timestamp || '';
        const level = log.level || 'INFO';
        const message = log.message || '';
        const category = log.category || 'GENERAL';
        
        // Skip verbose Playwright logs
        if (isVerbosePlaywrightLog(message)) {
            return;
        }
        
        // Get level styling
        const levelClass = getLevelClass(level);
        const levelIcon = getLevelIcon(level);
        
        // Get category styling
        const categoryClass = getCategoryClass(category);
        
        html += `
            <div class="log-entry ${levelClass}">
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-level ${levelClass}">
                    <i class="${levelIcon}"></i>
                    ${level}
                </span>
                <span class="log-category ${categoryClass}">${category}</span>
                <span class="log-message">${formatLogMessage(message)}</span>
            </div>
        `;
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

function getLevelClass(level) {
    switch (level.toLowerCase()) {
        case 'error': return 'log-level-error';
        case 'warning': return 'log-level-warning';
        case 'success': return 'log-level-success';
        case 'info': return 'log-level-info';
        default: return 'log-level-info';
    }
}

function getLevelIcon(level) {
    switch (level.toLowerCase()) {
        case 'error': return 'bi bi-x-circle-fill';
        case 'warning': return 'bi bi-exclamation-triangle-fill';
        case 'success': return 'bi bi-check-circle-fill';
        case 'info': return 'bi bi-info-circle-fill';
        default: return 'bi bi-info-circle';
    }
}

function getCategoryClass(category) {
    switch (category.toLowerCase()) {
        case 'task_start': return 'category-task';
        case 'task_info': return 'category-task';
        case 'login': return 'category-login';
        case 'upload': return 'category-upload';
        case 'human': return 'category-human';
        case 'dolphin': return 'category-dolphin';
        case 'proxy': return 'category-proxy';
        default: return 'category-general';
    }
}

function formatLogMessage(message) {
    // Apply emoji and keyword highlighting
    return message
        .replace(/(❌)/g, '<span class="emoji-error">$1</span>')
        .replace(/(⚠️)/g, '<span class="emoji-warning">$1</span>')
        .replace(/(✅)/g, '<span class="emoji-success">$1</span>')
        .replace(/(🔄|🔍|⏳|🌐|🔒)/g, '<span class="emoji-info">$1</span>')
        .replace(/(👤|📝|🎬|📋|📎|👥|👆)/g, '<span class="emoji-action">$1</span>')
        .replace(/(⌨️|🖱️|🔑)/g, '<span class="emoji-input">$1</span>')
        .replace(/(🚀|🔥)/g, '<span class="emoji-important">$1</span>')
        // Highlight important keywords
        .replace(/(ERROR|CRITICAL|Failed|Error|Exception|Timeout)/gi, '<span class="keyword-error">$1</span>')
        .replace(/(WARNING|Warning|Warn)/gi, '<span class="keyword-warning">$1</span>')
        .replace(/(SUCCESS|Completed|Success|Successful)/gi, '<span class="keyword-success">$1</span>')
        .replace(/(Username|Password|Login|Cookie)/gi, '<span class="keyword-auth">$1</span>');
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
                // Update logs if there's new content
                if (data.logs && data.logs.length > lastLogCount) {
                    lastLogCount = data.logs.length;
                    logsDiv.innerHTML = renderLog(data.logs);
                    
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
                logsDiv.innerHTML += `
                    <div class="log-entry log-level-error">
                        <span class="log-timestamp">${new Date().toLocaleTimeString()}</span>
                        <span class="log-level log-level-error">
                            <i class="bi bi-exclamation-triangle-fill"></i>
                            ERROR
                        </span>
                        <span class="log-category category-system">SYSTEM</span>
                        <span class="log-message">Failed to fetch logs: ${error.message}</span>
                    </div>
                `;
                
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