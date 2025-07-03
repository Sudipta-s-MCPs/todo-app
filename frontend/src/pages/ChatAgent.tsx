import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Chip,
  Tooltip,
  AppBar,
  Toolbar,
  Divider,
  useTheme,
  useMediaQuery,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  SmartToy as AIIcon,
  Close as CloseIcon,
  Task as TaskIcon,
  Help as HelpIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';

import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TaskSuggestionPreview from '../components/TaskSuggestionPreview';
import { chatService } from '../services/chatService';
import type { ChatMessage as ChatMessageType } from '../types';

export default function ChatAgent() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { enqueueSnackbar } = useSnackbar();
  
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestedTasks, setSuggestedTasks] = useState<any[]>([]);
  const [aiUsageToday, setAiUsageToday] = useState({ used: 0, limit: 50 });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChatHistory();
    loadAiUsage();
    // Show welcome message
    if (messages.length === 0) {
      setMessages([{
        id: 'welcome',
        content: "👋 Hi! I'm your AI task assistant. I can help you:\n\n• Create tasks from natural language\n• Find and update existing tasks\n• Schedule and organize your work\n• Answer questions about your tasks\n\nTry saying something like 'Schedule a meeting with John next Tuesday' or 'What tasks are due this week?'",
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        metadata: { type: 'welcome' }
      }]);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadChatHistory = async () => {
    try {
      const conversations = await chatService.getConversations();
      if (conversations.length > 0) {
        // Load messages from the single conversation
        const messages = await chatService.getConversationMessages(conversations[0].id);
        if (messages.length > 0) {
          setMessages(messages);
        } else {
          // Show welcome message if no history
          showWelcomeMessage();
        }
      } else {
        showWelcomeMessage();
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
      showWelcomeMessage();
    }
  };
  
  const showWelcomeMessage = () => {
    setMessages([{
      id: 'welcome',
      content: "👋 Hi! I'm your AI task assistant. I can help you:\n\n• Create tasks from natural language\n• Find and update existing tasks\n• Schedule and organize your work\n• Answer questions about your tasks\n\nTry saying something like 'Schedule a meeting with John next Tuesday' or 'What tasks are due this week?'",
      sender: 'assistant',
      timestamp: new Date().toISOString(),
      metadata: { type: 'welcome' }
    }]);
  };

  const loadAiUsage = async () => {
    try {
      const usage = await chatService.getAiUsage();
      setAiUsageToday(usage);
    } catch (error) {
      console.error('Failed to load AI usage:', error);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      content,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Send to backend
      const response = await chatService.sendMessage(content, null);
      
      // Add assistant response
      setMessages(prev => [...prev, response.message]);
      
      // Update suggested tasks if any
      if (response.tasks && response.tasks.length > 0) {
        setSuggestedTasks(response.tasks);
      }
      
      // Update AI usage
      if (response.usedAI) {
        setAiUsageToday(prev => ({ ...prev, used: prev.used + 1 }));
      }
      
      // Show notification only when tasks are actually created (not suggested)
      if (response.action === 'created' && response.tasks && response.tasks.length > 0) {
        enqueueSnackbar('Task created successfully', { variant: 'success' });
      } else if (response.action === 'suggested' || response.action === 'suggest_task') {
        // Don't show notification for suggestions - they'll be shown in preview
      }
      
    } catch (error: any) {
      const errorMessage: ChatMessageType = {
        id: Date.now().toString(),
        content: error.response?.data?.detail || 'Sorry, I encountered an error. Please try again.',
        sender: 'assistant',
        timestamp: new Date().toISOString(),
        metadata: { type: 'error' }
      };
      setMessages(prev => [...prev, errorMessage]);
      enqueueSnackbar('Failed to send message', { variant: 'error' });
    } finally {
      setIsLoading(false);
    }
  };



  const commandHelp = [
    { command: '/today', description: 'Show today\'s tasks' },
    { command: '/create "task"', description: 'Quick task creation' },
    { command: '/search query', description: 'Search tasks' },
    { command: '/help', description: 'Show all commands' },
  ];

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
      {/* Main Chat Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Chat Header */}
          <AppBar position="static" color="default" elevation={1}>
            <Toolbar variant="dense">
              <AIIcon sx={{ mr: 1 }} />
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                AI Task Assistant
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  size="small"
                  label={`AI: ${aiUsageToday.used}/${aiUsageToday.limit}`}
                  color={aiUsageToday.used >= aiUsageToday.limit ? 'error' : 'default'}
                />
                <Tooltip title="Commands">
                  <IconButton size="small">
                    <HelpIcon />
                  </IconButton>
                </Tooltip>
              </Box>
            </Toolbar>
          </AppBar>

          {/* Messages Area */}
          <Box
            ref={chatContainerRef}
            sx={{
              flex: 1,
              overflow: 'auto',
              p: 2,
              backgroundColor: 'background.default',
            }}
          >
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onTaskClick={() => {}}
              />
            ))}
            {isLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}
            <div ref={messagesEndRef} />
          </Box>

          {/* AI Usage Warning */}
          {aiUsageToday.used >= aiUsageToday.limit && (
            <Alert severity="warning" sx={{ mx: 2 }}>
              Daily AI limit reached. Commands will use pattern matching only.
            </Alert>
          )}

          {/* Input Area */}
          <Box sx={{ p: 2, backgroundColor: 'background.paper' }}>
            <ChatInput
              onSendMessage={handleSendMessage}
              disabled={isLoading}
              placeholder="Ask me anything about your tasks..."
              commands={commandHelp}
            />
          </Box>
        </Box>

        {/* Task Suggestion Panel */}
        {suggestedTasks.length > 0 && !isMobile && (
          <Paper
            sx={{
              width: 400,
              display: 'flex',
              flexDirection: 'column',
              borderLeft: 1,
              borderColor: 'divider',
            }}
          >
            <Box sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
              <TaskIcon sx={{ mr: 1 }} />
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Task Suggestion
              </Typography>
              <IconButton size="small" onClick={() => setSuggestedTasks([])}>
                <CloseIcon />
              </IconButton>
            </Box>
            <Divider />
            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
              {suggestedTasks.map((task, index) => (
                <TaskSuggestionPreview
                  key={`suggestion-${index}`}
                  suggestion={task}
                  onApprove={() => {
                    setSuggestedTasks([]);
                    enqueueSnackbar('Task created successfully', { variant: 'success' });
                  }}
                  onReject={() => {
                    setSuggestedTasks([]);
                    enqueueSnackbar('Task suggestion rejected', { variant: 'info' });
                  }}
                />
              ))}
            </Box>
          </Paper>
        )}
      </Box>
  );
}