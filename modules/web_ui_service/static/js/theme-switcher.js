
document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcher = document.getElementById('theme-switcher');
    const body = document.body;
    const icon = themeSwitcher.querySelector('i');

    // Add transition for smooth theme switching
    body.style.transition = 'background-color 0.3s ease, color 0.3s ease';

    const applyTheme = (theme) => {
        console.log('Applying theme:', theme);
        
        if (theme === 'dark') {
            body.classList.add('dark-theme');
            icon.classList.remove('bi-moon-stars-fill');
            icon.classList.add('bi-sun-fill');
            
            // Update meta theme color for mobile browsers
            const metaThemeColor = document.querySelector('meta[name="theme-color"]');
            if (metaThemeColor) {
                metaThemeColor.setAttribute('content', '#1c1c1e');
            } else {
                const newMeta = document.createElement('meta');
                newMeta.name = 'theme-color';
                newMeta.content = '#1c1c1e';
                document.head.appendChild(newMeta);
            }
        } else {
            body.classList.remove('dark-theme');
            icon.classList.remove('bi-sun-fill');
            icon.classList.add('bi-moon-stars-fill');
            
            // Update meta theme color for mobile browsers
            const metaThemeColor = document.querySelector('meta[name="theme-color"]');
            if (metaThemeColor) {
                metaThemeColor.setAttribute('content', '#ffffff');
            }
        }
    };

    // Get system theme preference
    const getSystemTheme = () => {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        console.log('System theme detected:', isDark ? 'dark' : 'light');
        return isDark ? 'dark' : 'light';
    };

    // Get saved theme or system preference
    const getInitialTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        console.log('Saved theme:', savedTheme);
        
        if (savedTheme) {
            return savedTheme;
        }
        
        const systemTheme = getSystemTheme();
        console.log('Using system theme:', systemTheme);
        return systemTheme;
    };

    // Update button title based on current theme and auto-detection
    const updateButtonTitle = () => {
        const isAuto = !localStorage.getItem('theme');
        const currentTheme = body.classList.contains('dark-theme') ? 'dark' : 'light';
        
        if (isAuto) {
            themeSwitcher.title = `Current: ${currentTheme} (Auto) - Click to switch`;
        } else {
            themeSwitcher.title = `Current: ${currentTheme} (Manual) - Click to switch`;
        }
        
        console.log('Button title updated:', themeSwitcher.title);
    };

    // Add click animation
    themeSwitcher.addEventListener('click', () => {
        // Add click animation
        themeSwitcher.style.transform = 'scale(0.95)';
        setTimeout(() => {
            themeSwitcher.style.transform = 'scale(1)';
        }, 150);

        const isDark = body.classList.contains('dark-theme');
        const newTheme = isDark ? 'light' : 'dark';
        
        console.log('Theme switched to:', newTheme);
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
        updateButtonTitle();
        
        // Dispatch custom event for other scripts
        document.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme: newTheme } 
        }));
    });

    // Initialize theme
    const initialTheme = getInitialTheme();
    console.log('Initial theme:', initialTheme);
    applyTheme(initialTheme);
    updateButtonTitle();

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
        console.log('System theme changed:', e.matches ? 'dark' : 'light');
        
        // Only auto-switch if user hasn't manually set a preference
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            console.log('Auto-switching to:', newTheme);
            applyTheme(newTheme);
            updateButtonTitle();
        }
    });

    // Add hover effects
    themeSwitcher.addEventListener('mouseenter', () => {
        themeSwitcher.style.transform = 'scale(1.05)';
    });

    themeSwitcher.addEventListener('mouseleave', () => {
        themeSwitcher.style.transform = 'scale(1)';
    });

    // Add keyboard support
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + T to toggle theme
        if ((e.ctrlKey || e.metaKey) && e.key === 't') {
            e.preventDefault();
            themeSwitcher.click();
        }
    });

    // Add double-click to reset to auto mode
    let clickTimeout;
    themeSwitcher.addEventListener('click', () => {
        if (clickTimeout) {
            // Double click detected
            clearTimeout(clickTimeout);
            clickTimeout = null;
            
            // Reset to auto mode
            localStorage.removeItem('theme');
            const systemTheme = getSystemTheme();
            console.log('Reset to auto mode, system theme:', systemTheme);
            applyTheme(systemTheme);
            updateButtonTitle();
            
            // Show feedback
            const originalTitle = themeSwitcher.title;
            themeSwitcher.title = 'Switched to Auto mode!';
            setTimeout(() => {
                themeSwitcher.title = originalTitle;
            }, 2000);
            
            return;
        }
        
        clickTimeout = setTimeout(() => {
            clickTimeout = null;
        }, 300);
    });
});
