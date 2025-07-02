import { useState, useRef, type KeyboardEvent } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Popper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Typography,
  Chip,
} from '@mui/material';
import {
  Send as SendIcon,
  Help as HelpIcon,
  Today as TodayIcon,
  Add as AddIcon,
  Search as SearchIcon,
  List as ListIcon,
} from '@mui/icons-material';

interface Command {
  command: string;
  description: string;
  icon?: React.ReactNode;
}

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  commands?: Command[];
}

const defaultCommands: Command[] = [
  { command: '/today', description: "Show today's tasks", icon: <TodayIcon /> },
  { command: '/create', description: 'Create a new task', icon: <AddIcon /> },
  { command: '/search', description: 'Search tasks', icon: <SearchIcon /> },
  { command: '/list', description: 'List all tasks', icon: <ListIcon /> },
  { command: '/help', description: 'Show all commands', icon: <HelpIcon /> },
];

export default function ChatInput({
  onSendMessage,
  disabled = false,
  placeholder = 'Type a message or / for commands...',
  commands = defaultCommands,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [showCommands, setShowCommands] = useState(false);
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);

  const filteredCommands = commands.filter(cmd =>
    message.startsWith('/') && cmd.command.toLowerCase().includes(message.toLowerCase())
  );

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      setShowCommands(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      
      // If a command is selected, use it
      if (showCommands && selectedCommandIndex >= 0 && selectedCommandIndex < filteredCommands.length) {
        const selectedCommand = filteredCommands[selectedCommandIndex];
        setMessage(selectedCommand.command + ' ');
        setShowCommands(false);
        setSelectedCommandIndex(-1);
      } else {
        handleSend();
      }
    } else if (e.key === 'ArrowDown' && showCommands) {
      e.preventDefault();
      setSelectedCommandIndex(prev => 
        prev < filteredCommands.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp' && showCommands) {
      e.preventDefault();
      setSelectedCommandIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Escape') {
      setShowCommands(false);
      setSelectedCommandIndex(-1);
    }
  };

  const handleChange = (value: string) => {
    setMessage(value);
    
    // Show commands when typing '/'
    if (value.startsWith('/')) {
      setShowCommands(true);
      setSelectedCommandIndex(-1);
    } else {
      setShowCommands(false);
    }
  };

  const handleCommandClick = (command: string) => {
    setMessage(command + ' ');
    setShowCommands(false);
    inputRef.current?.focus();
  };

  const examples = [
    "Schedule meeting with team tomorrow at 3pm",
    "What tasks are due this week?",
    "Create a task to review Q4 reports",
    "Show my high priority tasks",
  ];

  return (
    <Box>
      {/* Example chips for new users */}
      {message === '' && (
        <Box sx={{ mb: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="caption" color="text.secondary">
            Try:
          </Typography>
          {examples.map((example, index) => (
            <Chip
              key={index}
              label={example}
              size="small"
              onClick={() => setMessage(example)}
              sx={{ cursor: 'pointer' }}
            />
          ))}
        </Box>
      )}

      <Paper
        ref={anchorRef}
        sx={{
          display: 'flex',
          alignItems: 'flex-end',
          p: 1,
          gap: 1,
        }}
        elevation={2}
      >
        <TextField
          ref={inputRef}
          fullWidth
          multiline
          maxRows={4}
          value={message}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          variant="standard"
          sx={{
            '& .MuiInput-root': {
              fontSize: '16px',
            },
            '& .MuiInput-root:before': {
              display: 'none',
            },
          }}
        />
        
        {/* Future: Voice input */}
        {/* <IconButton size="small" disabled>
          <MicIcon />
        </IconButton> */}
        
        {/* Future: File attachments */}
        {/* <IconButton size="small" disabled>
          <AttachIcon />
        </IconButton> */}
        
        <IconButton
          color="primary"
          onClick={handleSend}
          disabled={disabled || !message.trim()}
        >
          <SendIcon />
        </IconButton>
      </Paper>

      {/* Command suggestions */}
      <Popper
        open={showCommands && filteredCommands.length > 0}
        anchorEl={anchorRef.current}
        placement="top-start"
        sx={{ zIndex: 1300 }}
      >
        <Paper elevation={3} sx={{ maxHeight: 200, overflow: 'auto' }}>
          <List dense>
            {filteredCommands.map((cmd, index) => (
              <ListItem
                key={cmd.command}
                button
                selected={index === selectedCommandIndex}
                onClick={() => handleCommandClick(cmd.command)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                  },
                }}
              >
                {cmd.icon && (
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {cmd.icon}
                  </ListItemIcon>
                )}
                <ListItemText
                  primary={cmd.command}
                  secondary={cmd.description}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      </Popper>
    </Box>
  );
}