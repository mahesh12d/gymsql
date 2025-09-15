import { useState, useEffect } from 'react';

export function useTheme() {
  // Initialize state only once
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  useEffect(() => {
    // Optimized observer with throttling to prevent excessive re-renders
    let timeoutId: number | null = null;
    
    const observer = new MutationObserver(() => {
      // Throttle updates to prevent rapid re-renders
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      
      timeoutId = window.setTimeout(() => {
        const newIsDarkMode = document.documentElement.classList.contains('dark');
        setIsDarkMode((prevMode) => {
          // Only update if the value has actually changed
          return prevMode !== newIsDarkMode ? newIsDarkMode : prevMode;
        });
      }, 50); // Small delay to batch multiple changes
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });

    return () => {
      observer.disconnect();
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, []);

  return isDarkMode;
}