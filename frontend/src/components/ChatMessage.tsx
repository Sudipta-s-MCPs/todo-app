import { Box, Paper, Typography, Avatar, Chip, IconButton, Tooltip } from '@mui/material';
import {
  SmartToy as AIIcon,
  Person as PersonIcon,
  ContentCopy as CopyIcon,
  Task as TaskIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { useSnackbar } from 'notistack';
import ReactMarkdown from 'react-markdown';

import type { ChatMessage as ChatMessageType, Task } from '../types';

interface ChatMessageProps {
  message: ChatMessageType;
  onTaskClick?: (task: Task) => void;
}

export default function ChatMessage({ message, onTaskClick }: ChatMessageProps) {
  const { enqueueSnackbar } = useSnackbar();
  const isUser = message.sender === 'user';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    enqueueSnackbar('Copied to clipboard', { variant: 'success' });
  };

  const getMessageIcon = () => {
    if (message.metadata?.type === 'error') return <ErrorIcon color="error" />;
    if (message.metadata?.type === 'success') return <SuccessIcon color="success" />;
    if (message.metadata?.type === 'task') return <TaskIcon color="primary" />;
    return null;
  };

  const renderContent = () => {
    // If message contains task references, render them as clickable chips
    if (message.metadata?.tasks) {
      const parts = message.content.split(/(\[task:\w+\])/g);
      return (
        <Box>
          {parts.map((part, index) => {
            const taskMatch = part.match(/\[task:(\w+)\]/);
            if (taskMatch) {
              const taskId = taskMatch[1];
              const task = message.metadata?.tasks?.find((t: Task) => t.id === taskId);
              if (task) {
                return (
                  <Chip
                    key={index}
                    label={task.title}
                    size="small"
                    icon={<TaskIcon />}
                    onClick={() => onTaskClick?.(task)}
                    sx={{ mx: 0.5, cursor: 'pointer' }}
                  />
                );
              }
            }
            return <span key={index}>{part}</span>;
          })}
        </Box>
      );
    }

    // For assistant messages, render markdown
    if (!isUser) {
      return (
        <Box sx={{ '& p': { my: 1 }, '& ul': { mt: 0 } }}>
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </Box>
      );
    }

    return <Typography>{message.content}</Typography>;
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
        gap: 1,
      }}
    >
      {!isUser && (
        <Avatar sx={{ bgcolor: 'primary.main', width: 36, height: 36 }}>
          <AIIcon fontSize="small" />
        </Avatar>
      )}

      <Paper
        elevation={1}
        sx={{
          p: 2,
          maxWidth: '70%',
          backgroundColor: isUser ? 'primary.main' : 'background.paper',
          color: isUser ? 'primary.contrastText' : 'text.primary',
          position: 'relative',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
          {getMessageIcon()}
          <Box sx={{ flex: 1 }}>
            {renderContent()}
            
            {/* Metadata badges */}
            {message.metadata?.usedAI && (
              <Chip
                label="AI"
                size="small"
                icon={<AIIcon />}
                sx={{ mt: 1, mr: 1 }}
                color={isUser ? 'default' : 'primary'}
              />
            )}
            
            {message.metadata?.confidence && (
              <Chip
                label={`${Math.round(message.metadata.confidence * 100)}% confident`}
                size="small"
                sx={{ mt: 1 }}
                variant="outlined"
              />
            )}
          </Box>
        </Box>

        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mt: 1,
            opacity: 0.7,
          }}
        >
          <Typography variant="caption">
            {format(new Date(message.timestamp), 'HH:mm')}
          </Typography>
          
          {!isUser && (
            <Tooltip title="Copy message">
              <IconButton size="small" onClick={handleCopy} sx={{ ml: 1 }}>
                <CopyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Paper>

      {isUser && (
        <Avatar sx={{ bgcolor: 'grey.600', width: 36, height: 36 }}>
          <PersonIcon fontSize="small" />
        </Avatar>
      )}
    </Box>
  );
}