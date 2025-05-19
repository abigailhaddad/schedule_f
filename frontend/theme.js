// Theme manager for the Data Explorer
(function() {
    // Define color schemes
    const COLOR_SCHEMES = {
        default: {
            primary: '#6366f1',     // Indigo
            primaryRgb: '99, 102, 241',
            accent: '#14b8a6',      // Teal
            success: '#10b981',     // Green
            warning: '#f59e0b',     // Amber
            info: '#3b82f6',        // Blue
            secondary: '#64748b',   // Slate
            danger: '#ef4444'       // Red
        },
        blue: {
            primary: '#2563eb',     // Rich blue
            primaryRgb: '37, 99, 235',
            accent: '#0ea5e9',      // Light blue
            success: '#10b981',     // Green
            warning: '#f59e0b',     // Amber
            info: '#3b82f6',        // Blue
            secondary: '#64748b',   // Slate
            danger: '#ef4444'       // Red
        },
        teal: {
            primary: '#0d9488',     // Teal
            primaryRgb: '13, 148, 136',
            accent: '#059669',      // Green
            success: '#10b981',     // Green
            warning: '#f59e0b',     // Amber
            info: '#0ea5e9',        // Blue
            secondary: '#64748b',   // Slate
            danger: '#ef4444'       // Red
        },
        slate: {
            primary: '#475569',     // Slate
            primaryRgb: '71, 85, 105',
            accent: '#64748b',      // Lighter slate
            success: '#10b981',     // Green
            warning: '#f59e0b',     // Amber
            info: '#0ea5e9',        // Blue
            secondary: '#94a3b8',   // Light slate
            danger: '#ef4444'       // Red
        },
        darkblue: {
            primary: '#1e40af',     // Dark blue
            primaryRgb: '30, 64, 175',
            accent: '#3b82f6',      // Bright blue
            success: '#10b981',     // Green
            warning: '#f59e0b',     // Amber
            info: '#0ea5e9',        // Blue
            secondary: '#64748b',   // Slate
            danger: '#ef4444'       // Red
        },
        forest: {
            primary: '#166534',     // Forest green
            primaryRgb: '22, 101, 52',
            accent: '#16a34a',      // Bright green
            success: '#10b981',     // Green
            warning: '#f59e0b',     // Amber
            info: '#0ea5e9',        // Blue
            secondary: '#64748b',   // Slate
            danger: '#ef4444'       // Red
        }
    };

    // Define button styles
    const BUTTON_STYLES = {
        default: `
            .btn {
                font-weight: 500;
                letter-spacing: 0.01em;
                border-radius: 0.375rem;
                transition: all 0.2s ease;
            }
            
            .btn-primary {
                background-color: var(--bs-primary);
                border-color: var(--bs-primary);
            }
            
            .btn-primary:hover {
                background-color: var(--accent);
                border-color: var(--accent);
            }
            
            .btn-outline-primary {
                border-color: var(--bs-primary);
                color: var(--bs-primary);
            }
            
            .btn-outline-primary:hover {
                background-color: var(--bs-primary);
                color: white;
            }
            
            /* Make DataTable buttons match */
            .dt-button {
                font-weight: 600 !important;
                background-color: var(--bs-primary) !important;
                border-color: var(--bs-primary) !important;
                color: white !important;
            }
            
            .dt-button:hover {
                background-color: var(--accent) !important;
                border-color: var(--accent) !important;
            }
        `,
        rounded: `
            .btn {
                font-weight: 500;
                letter-spacing: 0.01em;
                border-radius: 50rem;
                padding: 0.5rem 1.25rem;
                transition: all 0.2s ease;
            }
            
            .btn-sm {
                padding: 0.25rem 0.75rem;
            }
            
            .btn-primary {
                background-color: var(--bs-primary);
                border-color: var(--bs-primary);
            }
            
            .btn-primary:hover, .btn-primary:focus {
                background-color: var(--accent);
                border-color: var(--accent);
                transform: scale(1.03);
            }
            
            .btn-outline-primary {
                border-color: var(--bs-primary);
                color: var(--bs-primary);
            }
            
            .btn-outline-primary:hover, .btn-outline-primary:focus {
                background-color: var(--bs-primary);
                color: white;
                transform: scale(1.03);
            }
            
            /* Make DataTable buttons match */
            .dt-button {
                border-radius: 50rem !important;
                font-weight: 600 !important;
                background-color: var(--bs-primary) !important;
                border-color: var(--bs-primary) !important;
                color: white !important;
            }
            
            .dt-button:hover {
                background-color: var(--accent) !important;
                border-color: var(--accent) !important;
                transform: scale(1.03);
            }
        `,
        flat: `
            .btn {
                font-weight: 600;
                letter-spacing: 0.01em;
                border-radius: 0.25rem;
                transition: all 0.15s ease;
                border-width: 2px;
            }
            
            .btn-primary {
                background-color: var(--bs-primary);
                border-color: var(--bs-primary);
            }
            
            .btn-primary:hover, .btn-primary:focus {
                filter: brightness(110%);
            }
            
            .btn-outline-primary {
                border-color: var(--bs-primary);
                color: var(--bs-primary);
            }
            
            .btn-outline-primary:hover, .btn-outline-primary:focus {
                background-color: var(--bs-primary);
                color: white;
            }
            
            .btn-sm {
                padding: 0.25rem 0.75rem;
                font-size: 0.875rem;
            }
            
            /* Make DataTable buttons match */
            .dt-button {
                font-weight: 600 !important;
                border-width: 2px !important;
                background-color: var(--bs-primary) !important;
                border-color: var(--bs-primary) !important;
                color: white !important;
            }
            
            .dt-button:hover {
                filter: brightness(110%);
            }
        `
    };

    // Define card shadow styles
    const CARD_STYLES = {
        subtle: `
            .card {
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
                border: 1px solid rgba(0, 0, 0, 0.08);
                transition: box-shadow 0.2s ease-in-out;
            }
            
            .card:hover {
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }
        `,
        elevated: `
            .card {
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                border: 1px solid rgba(0, 0, 0, 0.12);
                transition: all 0.2s ease-in-out;
            }
            
            .card:hover {
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                transform: translateY(-1px);
            }
        `,
        material: `
            .card {
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border: none;
                border-radius: 8px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .card:hover {
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
                transform: translateY(-2px);
            }
        `,
        bordered: `
            .card {
                box-shadow: none;
                border: 2px solid var(--bs-primary);
                background-color: #ffffff;
                transition: all 0.2s ease-in-out;
            }
            
            .card:hover {
                border-color: var(--accent);
                box-shadow: 0 2px 4px rgba(var(--bs-primary-rgb), 0.1);
            }
        `,
        minimal: `
            .card {
                box-shadow: none;
                border: 1px solid #e5e7eb;
                background-color: #ffffff;
                transition: all 0.2s ease-in-out;
            }
            
            .card:hover {
                border-color: var(--bs-primary);
                box-shadow: 0 1px 2px rgba(var(--bs-primary-rgb), 0.1);
            }
        `,
        glass: `
            .card {
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                backdrop-filter: blur(4px);
                -webkit-backdrop-filter: blur(4px);
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.18);
                transition: all 0.3s ease;
            }
            
            .card:hover {
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.5);
            }
        `
    };

    // Apply theme based on config
    function applyTheme() {
        // Get config
        const config = window.DATASET_CONFIG || {};
        const theme = config.theme || {};
        
        // Get color scheme
        const colorSchemeName = theme.colorScheme || 'default';
        const colorScheme = COLOR_SCHEMES[colorSchemeName] || COLOR_SCHEMES.default;
        
        // Get button style
        const buttonStyleName = theme.buttonStyle || 'default';
        const buttonStyle = BUTTON_STYLES[buttonStyleName] || BUTTON_STYLES.default;
        
        // Get card style
        const cardStyleName = theme.cardStyle || 'subtle';
        const cardStyle = CARD_STYLES[cardStyleName] || CARD_STYLES.subtle;
        
        // Create CSS variables and DataTables specific styling
        const cssVars = `
    :root {
        --bs-primary: ${colorScheme.primary};
        --bs-primary-rgb: ${colorScheme.primaryRgb};
        --accent: ${colorScheme.accent};
        --success: ${colorScheme.success};
        --warning: ${colorScheme.warning};
        --info: ${colorScheme.info};
        --secondary: ${colorScheme.secondary};
        --danger: ${colorScheme.danger};
    }

    .bg-primary {
        background-color: var(--bs-primary) !important;
    }

    .text-primary {
        color: var(--bs-primary) !important;
    }

    /* Bootstrap + Pagination + Filter Overrides */
    .btn-primary,
    .btn-primary:active,
    .btn-primary:focus,
    .btn-primary.active,
    .btn-primary:visited,
    .btn-primary:focus-visible,
    .btn-check:checked + .btn-primary,
    .btn-primary:disabled,
    .btn-primary.disabled {
        background-color: var(--bs-primary) !important;
        border-color: var(--bs-primary) !important;
        color: #fff !important;
    }

    .btn-primary:hover,
    .btn-check:checked + .btn-primary:hover {
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #fff !important;
    }

    .btn-outline-primary {
        background-color: transparent !important;
        border-color: var(--bs-primary) !important;
        color: var(--bs-primary) !important;
    }

    .btn-outline-primary:hover,
    .btn-outline-primary:focus {
        background-color: var(--bs-primary) !important;
        border-color: var(--bs-primary) !important;
        color: #fff !important;
    }

    .btn-outline-primary.active,
    .btn-outline-primary:active,
    .btn-outline-primary.active:focus,
    .btn-outline-primary.active:hover,
    .btn-check:checked + .btn-outline-primary {
        background-color: var(--bs-primary) !important;
        border-color: var(--bs-primary) !important;
        color: #fff !important;
    }

    .page-item.active .page-link,
    .page-link.active {
        background-color: var(--bs-primary) !important;
        border-color: var(--bs-primary) !important;
        color: #fff !important;
    }

    .page-link {
        color: var(--bs-primary) !important;
        border-color: var(--bs-primary) !important;
    }

    .page-link:hover {
        background-color: rgba(var(--bs-primary-rgb), 0.08) !important;
        color: var(--bs-primary) !important;
    }

    ${buttonStyle}
    ${cardStyle}
`;


        
        // Remove existing theme styles to prevent accumulation
        const existingStyle = document.getElementById('theme-styles');
        if (existingStyle) {
            existingStyle.remove();
        }
        
        // Create and append style tag
        const styleTag = document.createElement('style');
        styleTag.id = 'theme-styles';
        styleTag.textContent = cssVars;
        document.head.appendChild(styleTag);
    }

    // Apply theme when DOM is loaded
    document.addEventListener('DOMContentLoaded', applyTheme);
    
    // Export for manual theme changes
    window.applyTheme = applyTheme;
})();