// Cabinet Theme Chart.js Configuration - mr.Booster colors
(function() {
    'use strict';
    
    // mr.Booster color palette
    const cabinetColors = {
        primary: '#8167FF',      // Slate Blue
        secondary: '#FFE608',    // Canary Yellow
        success: '#ACF639',      // Green Yellow
        danger: '#FF4F52',       // Bittersweet
        info: '#4DE6F4',         // Electric Blue
        warning: '#FFE608',      // Canary Yellow
        dark: '#0D0D0E',         // Night Black
        white: '#FFFFFF'         // Clear White
    };
    
    // Chart.js default configuration
    const cabinetChartConfig = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    font: {
                        family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                        size: 12,
                        weight: '500'
                    },
                    color: cabinetColors.dark,
                    padding: 20,
                    usePointStyle: true,
                    pointStyle: 'circle'
                }
            },
            tooltip: {
                backgroundColor: cabinetColors.white,
                titleColor: cabinetColors.dark,
                bodyColor: cabinetColors.dark,
                borderColor: cabinetColors.dark,
                borderWidth: 1,
                cornerRadius: 8,
                displayColors: true,
                titleFont: {
                    family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    size: 14,
                    weight: '600'
                },
                bodyFont: {
                    family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    size: 12,
                    weight: '500'
                }
            }
        },
        scales: {
            x: {
                grid: {
                    color: 'rgba(13, 13, 14, 0.1)',
                    borderColor: cabinetColors.dark
                },
                ticks: {
                    color: cabinetColors.dark,
                    font: {
                        family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                        size: 11,
                        weight: '500'
                    }
                }
            },
            y: {
                grid: {
                    color: 'rgba(13, 13, 14, 0.1)',
                    borderColor: cabinetColors.dark
                },
                ticks: {
                    color: cabinetColors.dark,
                    font: {
                        family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                        size: 11,
                        weight: '500'
                    }
                }
            }
        }
    };
    
    // Color schemes for different chart types
    const cabinetColorSchemes = {
        primary: [cabinetColors.primary, cabinetColors.secondary, cabinetColors.success, cabinetColors.danger, cabinetColors.info],
        gradient: [
            'rgba(129, 103, 255, 0.8)',   // Slate Blue with opacity
            'rgba(255, 230, 8, 0.8)',     // Canary Yellow with opacity
            'rgba(172, 246, 57, 0.8)',    // Green Yellow with opacity
            'rgba(255, 79, 82, 0.8)',     // Bittersweet with opacity
            'rgba(77, 230, 244, 0.8)'     // Electric Blue with opacity
        ],
        dark: [cabinetColors.dark, cabinetColors.primary, cabinetColors.danger, cabinetColors.info, cabinetColors.success]
    };
    
    // Utility function to create chart with mr.Booster colors
    window.createCabinetChart = function(canvasId, chartType, data, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error('Canvas element not found:', canvasId);
            return null;
        }
        
        // Merge default config with custom options
        const config = {
            type: chartType,
            data: data,
            options: {
                ...cabinetChartConfig,
                ...options
            }
        };
        
        // Apply mr.Booster colors to datasets if not specified
        if (config.data.datasets) {
            config.data.datasets.forEach((dataset, index) => {
                if (!dataset.backgroundColor) {
                    dataset.backgroundColor = cabinetColorSchemes.primary[index % cabinetColorSchemes.primary.length];
                }
                if (!dataset.borderColor) {
                    dataset.borderColor = cabinetColors.primary;
                }
                if (!dataset.pointBackgroundColor) {
                    dataset.pointBackgroundColor = cabinetColors.white;
                }
                if (!dataset.pointBorderColor) {
                    dataset.pointBorderColor = cabinetColors.primary;
                }
            });
        }
        
        return new Chart(ctx, config);
    };
    
    // Export configuration for global use
    window.cabinetChartConfig = cabinetChartConfig;
    window.cabinetColors = cabinetColors;
    window.cabinetColorSchemes = cabinetColorSchemes;
    
    // Auto-apply to existing charts on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Find all canvas elements in cabinet theme
        const cabinetCanvases = document.querySelectorAll('.cabinet-theme canvas');
        cabinetCanvases.forEach(canvas => {
            if (canvas.id && !canvas.chart) {
                // Try to initialize chart if data attributes are present
                const chartType = canvas.getAttribute('data-chart-type');
                const chartData = canvas.getAttribute('data-chart-data');
                
                if (chartType && chartData) {
                    try {
                        const data = JSON.parse(chartData);
                        createCabinetChart(canvas.id, chartType, data);
                    } catch (e) {
                        console.error('Error parsing chart data for', canvas.id, e);
                    }
                }
            }
        });
    });
    
})();
