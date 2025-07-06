import React, { useState, useRef, useEffect } from 'react';
import {
  IconButton,
  Box,
  CircularProgress,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  keyframes,
} from '@mui/material';
import {
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Language as LanguageIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useAudioRecorder, formatRecordingTime } from '../hooks/useAudioRecorder';

const pulseAnimation = keyframes`
  0% {
    box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(255, 0, 0, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 0, 0, 0);
  }
`;

interface VoiceButtonProps {
  onAudioRecorded: (audioBlob: Blob, language: string) => Promise<void>;
  disabled?: boolean;
  size?: 'small' | 'medium' | 'large';
}

type Language = 'auto' | 'en' | 'bn' | 'hi';

const languages: { code: Language; label: string; flag: string }[] = [
  { code: 'auto', label: 'Auto Detect', flag: '🌐' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'bn', label: 'বাংলা (Bengali)', flag: '🇮🇳' },
  { code: 'hi', label: 'हिन्दी (Hindi)', flag: '🇮🇳' },
];

export default function VoiceButton({
  onAudioRecorded,
  disabled = false,
  size = 'medium',
}: VoiceButtonProps) {
  const { enqueueSnackbar } = useSnackbar();
  const [selectedLanguage, setSelectedLanguage] = useState<Language>('auto');
  const [isProcessing, setIsProcessing] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  
  const { state, startRecording, stopRecording, error } = useAudioRecorder();
  const longPressTimerRef = useRef<number | null>(null);
  const isPushToTalkRef = useRef(false);

  // Handle error from audio recorder
  useEffect(() => {
    if (error) {
      enqueueSnackbar(error, { variant: 'error' });
    }
  }, [error, enqueueSnackbar]);

  const handleLanguageClick = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleLanguageClose = () => {
    setAnchorEl(null);
  };

  const handleLanguageSelect = (language: Language) => {
    setSelectedLanguage(language);
    handleLanguageClose();
  };

  const handleStartRecording = async () => {
    try {
      await startRecording();
    } catch (err) {
      console.error('Failed to start recording:', err);
    }
  };

  const handleStopRecording = async () => {
    try {
      setIsProcessing(true);
      const audioBlob = await stopRecording();
      
      if (audioBlob && audioBlob.size > 0) {
        await onAudioRecorded(audioBlob, selectedLanguage);
      } else {
        enqueueSnackbar('No audio recorded', { variant: 'warning' });
      }
    } catch (err) {
      console.error('Failed to stop recording:', err);
      enqueueSnackbar('Failed to process recording', { variant: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  // Push-to-talk handlers (desktop)
  const handleMouseDown = () => {
    if (disabled || isProcessing || state.isRecording) return;
    
    // Set flag for push-to-talk mode
    isPushToTalkRef.current = true;
    
    // Start long press timer for toggle mode
    longPressTimerRef.current = window.setTimeout(() => {
      isPushToTalkRef.current = false;
    }, 500); // 500ms for long press
    
    handleStartRecording();
  };

  const handleMouseUp = () => {
    // Clear long press timer
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
    
    // Only stop if in push-to-talk mode
    if (isPushToTalkRef.current && state.isRecording) {
      handleStopRecording();
    }
  };

  const handleMouseLeave = () => {
    // Stop recording if mouse leaves while in push-to-talk mode
    if (isPushToTalkRef.current && state.isRecording) {
      handleStopRecording();
    }
  };

  // Toggle mode handler (mobile tap)
  const handleClick = () => {
    if (disabled || isProcessing) return;
    
    if (state.isRecording) {
      handleStopRecording();
    } else if (!isPushToTalkRef.current) {
      // Only start recording on click if not in push-to-talk mode
      handleStartRecording();
    }
  };

  // Keyboard support
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === ' ' && !state.isRecording) {
      event.preventDefault();
      handleStartRecording();
    }
  };

  const handleKeyUp = (event: React.KeyboardEvent) => {
    if (event.key === ' ' && state.isRecording && isPushToTalkRef.current) {
      event.preventDefault();
      handleStopRecording();
    }
  };

  const getTooltipTitle = () => {
    if (state.isRecording) return 'Recording... Click to stop';
    if (isProcessing) return 'Processing...';
    return 'Hold to record (or click to toggle)';
  };

  const getIcon = () => {
    if (state.isRecording) return <StopIcon />;
    if (error) return <MicOffIcon />;
    return <MicIcon />;
  };

  const getButtonColor = () => {
    if (state.isRecording) return 'error';
    if (error) return 'default';
    return 'primary';
  };

  return (
    <Box sx={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
      {/* Language selector */}
      <Tooltip title="Select language">
        <IconButton
          size="small"
          onClick={handleLanguageClick}
          disabled={disabled || state.isRecording || isProcessing}
          sx={{ mr: 0.5 }}
        >
          <LanguageIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      {/* Main recording button */}
      <Box sx={{ position: 'relative' }}>
        <Tooltip title={getTooltipTitle()}>
          <span>
            <IconButton
              color={getButtonColor()}
              disabled={disabled || isProcessing}
              onMouseDown={handleMouseDown}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseLeave}
              onTouchStart={handleMouseDown}
              onTouchEnd={handleMouseUp}
              onClick={handleClick}
              onKeyDown={handleKeyDown}
              onKeyUp={handleKeyUp}
              size={size}
              sx={{
                position: 'relative',
                animation: state.isRecording ? `${pulseAnimation} 1.5s infinite` : 'none',
                '&:disabled': {
                  color: 'action.disabled',
                },
              }}
            >
              {getIcon()}
            </IconButton>
          </span>
        </Tooltip>

        {/* Recording indicator */}
        {state.isRecording && (
          <>
            {/* Recording time */}
            <Chip
              label={formatRecordingTime(state.recordingTime)}
              size="small"
              color="error"
              sx={{
                position: 'absolute',
                top: -8,
                right: -8,
                height: 20,
                '& .MuiChip-label': {
                  px: 1,
                  fontSize: '0.75rem',
                },
              }}
            />
            
            {/* Audio level indicator */}
            <Box
              sx={{
                position: 'absolute',
                bottom: -4,
                left: '50%',
                transform: 'translateX(-50%)',
                width: `${Math.max(20, state.audioLevel)}%`,
                height: 2,
                backgroundColor: 'error.main',
                borderRadius: 1,
                transition: 'width 0.1s ease-out',
              }}
            />
          </>
        )}

        {/* Processing indicator */}
        {isProcessing && (
          <CircularProgress
            size={24}
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              marginTop: '-12px',
              marginLeft: '-12px',
            }}
          />
        )}
      </Box>

      {/* Language selection menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleLanguageClose}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
      >
        {languages.map((lang) => (
          <MenuItem
            key={lang.code}
            onClick={() => handleLanguageSelect(lang.code)}
            selected={selectedLanguage === lang.code}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <span style={{ fontSize: '1.2rem' }}>{lang.flag}</span>
            </ListItemIcon>
            <ListItemText primary={lang.label} />
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
}