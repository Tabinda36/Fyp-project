import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './hooks/useAuth';
import { FlashProvider } from './hooks/useFlash';
import ScrollToTop from './components/ScrollToTop';
import { Toaster } from 'react-hot-toast';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <FlashProvider>
          <ScrollToTop />
          <App />
          <Toaster
            position="top-right"
            gutter={10}
            containerStyle={{ top: 16, right: 16, left: 16 }}
            toastOptions={{
              duration: 4000,
              // Light by default; the public pages' dark theme overrides these variables (AuthPages.css).
              style: {
                maxWidth: '380px',
                padding: '12px 14px',
                border: '1px solid var(--toast-border, #d6e2dc)',
                borderRadius: '12px',
                background: 'var(--toast-bg, #ffffff)',
                color: 'var(--toast-ink, #173a30)',
                boxShadow: '0 10px 28px rgba(16, 60, 50, 0.14)',
                fontSize: '13px',
                fontWeight: 600,
                lineHeight: 1.45,
              },
              success: { iconTheme: { primary: '#08785b', secondary: '#ffffff' } },
              error: { duration: 5000, iconTheme: { primary: '#d92d20', secondary: '#ffffff' } },
              loading: { iconTheme: { primary: '#b8953f', secondary: '#e4ece7' } },
            }}
          />
        </FlashProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
