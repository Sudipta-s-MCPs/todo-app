import { useState, useEffect } from 'react';
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Box,
} from '@mui/material';
import { GetApp as GetAppIcon } from '@mui/icons-material';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function PWAInstallPrompt() {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as BeforeInstallPromptEvent);
      
      // Show prompt after 30 seconds or on second visit
      const hasVisited = localStorage.getItem('hasVisited');
      if (hasVisited) {
        setShowPrompt(true);
      } else {
        localStorage.setItem('hasVisited', 'true');
        setTimeout(() => setShowPrompt(true), 30000);
      }
    };
    
    window.addEventListener('beforeinstallprompt', handler);
    
    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
    };
  }, []);
  
  const handleInstall = async () => {
    if (!installPrompt) return;
    
    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    
    if (outcome === 'accepted') {
      setInstallPrompt(null);
      setShowPrompt(false);
    }
  };
  
  const handleClose = () => {
    setShowPrompt(false);
    // Ask again after 7 days
    setTimeout(() => setShowPrompt(true), 7 * 24 * 60 * 60 * 1000);
  };
  
  if (!installPrompt || !showPrompt) {
    return null;
  }
  
  return (
    <Dialog open={showPrompt} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <GetAppIcon color="primary" />
          Install Smart ToDo
        </Box>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" gutterBottom>
          Install Smart ToDo on your device for:
        </Typography>
        <Typography variant="body2" component="ul" sx={{ pl: 2 }}>
          <li>Quick access from your home screen</li>
          <li>Work offline</li>
          <li>Native app experience</li>
          <li>Push notifications</li>
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} color="inherit">
          Maybe Later
        </Button>
        <Button onClick={handleInstall} variant="contained">
          Install
        </Button>
      </DialogActions>
    </Dialog>
  );
}