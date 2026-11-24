import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-sans-arabic/400.css';
import '@fontsource/ibm-plex-sans-arabic/500.css';
import '@fontsource/ibm-plex-sans-arabic/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
// Alexandria: the logo's font (also page titles). Only the subsets we use.
import '@fontsource/alexandria/arabic-500.css';
import '@fontsource/alexandria/arabic-600.css';
import '@fontsource/alexandria/arabic-800.css';
import '@fontsource/alexandria/latin-500.css';
import '@fontsource/alexandria/latin-600.css';
import './theme.css';
import './styles.css';
import App from './App';
import { I18nProvider } from './lib/i18n';
import { LiveProvider } from './lib/live';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <I18nProvider>
      <LiveProvider>
        <App />
      </LiveProvider>
    </I18nProvider>
  </StrictMode>,
);
