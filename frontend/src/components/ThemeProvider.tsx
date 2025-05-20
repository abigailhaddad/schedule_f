// components/ThemeProvider.tsx
'use client';

import { createContext, useContext, ReactNode, useEffect } from 'react';
import { datasetConfig } from '@/lib/config';

// Define color schemes
const COLOR_SCHEMES: Record<string, Record<string, string>> = {
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
  // Additional color schemes...
};

// Define button styles
const BUTTON_STYLES: Record<string, string> = {
  flat: `
    .btn {
      font-weight: 600;
      letter-spacing: 0.01em;
      border-radius: 0.25rem;
      transition: all 0.15s ease;
      border-width: 2px;
    }
    
    .btn-primary {
      background-color: var(--p);
      border-color: var(--p);
    }
    
    .btn-primary:hover, .btn-primary:focus {
      filter: brightness(110%);
    }
  `,
  // Additional button styles...
};

// Define card styles
const CARD_STYLES: Record<string, string> = {
  minimal: `
    .card {
      box-shadow: none;
      border: 1px solid #e5e7eb;
      background-color: #ffffff;
      transition: all 0.2s ease-in-out;
    }
    
    .card:hover {
      border-color: var(--p);
      box-shadow: 0 1px 2px rgba(var(--p-rgb), 0.1);
    }
  `,
  // Additional card styles...
};

type ThemeContextType = {
  colorScheme: string;
  buttonStyle: string;
  cardStyle: string;
};

const ThemeContext = createContext<ThemeContextType>({
  colorScheme: 'default',
  buttonStyle: 'default',
  cardStyle: 'subtle',
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = datasetConfig.theme;
  
  useEffect(() => {
    const colorScheme = COLOR_SCHEMES[theme.colorScheme] || COLOR_SCHEMES.default;
    const buttonStyle = BUTTON_STYLES[theme.buttonStyle] || BUTTON_STYLES.default;
    const cardStyle = CARD_STYLES[theme.cardStyle] || CARD_STYLES.subtle;
    
    // Create CSS variables and styles
    const cssVars = `
      :root {
        --p: ${colorScheme.primary};
        --p-rgb: ${colorScheme.primaryRgb};
        --a: ${colorScheme.accent};
        --s: ${colorScheme.success};
        --w: ${colorScheme.warning};
        --i: ${colorScheme.info};
        --sc: ${colorScheme.secondary};
        --e: ${colorScheme.danger};
      }

      /* Button Styles */
      ${buttonStyle}
      
      /* Card Styles */
      ${cardStyle}
    `;
    
    // Add styles to document head
    let styleEl = document.getElementById('theme-styles');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'theme-styles';
      document.head.appendChild(styleEl);
    }
    styleEl.textContent = cssVars;
    
  }, [theme]);
  
  return (
    <ThemeContext.Provider value={theme}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}