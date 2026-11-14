import { useLayoutEffect, useState } from 'react';
import { LOGO_DARK, LOGO_LIGHT } from '../../cdn';

// Light is the default for the public/onboarding pages. A new key is used so a "Dark" value
// saved by the old 'alvix-theme' key no longer overrides that default; the toggle still persists.
const THEME_STORAGE_KEY = 'alvix-public-theme';
const LEGACY_THEME_KEY = 'alvix-theme';

function readTheme() {
  try {
    window.localStorage.removeItem(LEGACY_THEME_KEY);
    return window.localStorage.getItem(THEME_STORAGE_KEY) === 'Dark' ? 'Dark' : 'Light';
  } catch {
    return 'Light'; // storage blocked (private mode / cookies disabled)
  }
}

export function usePublicTheme() {
  const [theme, setTheme] = useState(readTheme);

  useLayoutEffect(() => {
    const light = theme === 'Light';
    document.body.classList.toggle('theme-light', light);
    document.body.classList.toggle('theme-dark', !light);
    document.documentElement.dataset.theme = theme.toLowerCase();

    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      /* storage unavailable: theme still applies for this visit */
    }

    const favicon = document.querySelector('link[rel="icon"]');
    if (favicon) favicon.href = light ? LOGO_LIGHT : LOGO_DARK;

    return () => {
      document.body.classList.remove('theme-light', 'theme-dark');
      delete document.documentElement.dataset.theme;
    };
  }, [theme]);

  return { theme, setTheme };
}
