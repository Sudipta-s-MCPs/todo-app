import { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  Tooltip,
  AppBar,
  Toolbar,
  useTheme,
  useMediaQuery,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Menu as MenuIcon,
  SmartToy as AIIcon,
  History as HistoryIcon,
  Delete as DeleteIcon,
  Close as CloseIcon,
  Task as TaskIcon,
  Add as AddIcon,
  Search as SearchIcon,
  Help as HelpIcon,
} from '@mui/icons-material';
import { formatDistanceToNow } from 'date-fns';
import { useSnackbar } from 'notistack';

import Layout from '../components/Layout';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import TaskPreview from '../components/TaskPreview';
import { chatService } from '../services/chatService';
import type { ChatMessage as ChatMessageType, ChatConversation, Task } from '../types';

export default function ChatAgent() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { enqueueSnackbar } = useSnackbar();
  
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(!isMobile);
  const [previewTasks, setPreviewTasks] = useState<Task[]>([]);
  const [aiUsageToday, setAiUsageToday] = useState({ used: 0, limit: 50 });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversations();
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

  const loadConversations = async () => {
    try {
      const data = await chatService.getConversations();
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
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
      const response = await chatService.sendMessage(content, currentConversationId);
      
      // Add assistant response
      setMessages(prev => [...prev, response.message]);
      
      // Update conversation ID if new
      if (response.conversationId && !currentConversationId) {
        setCurrentConversationId(response.conversationId);
        loadConversations();
      }
      
      // Update preview tasks if any
      if (response.tasks && response.tasks.length > 0) {
        setPreviewTasks(response.tasks);
      }
      
      // Update AI usage
      if (response.usedAI) {
        setAiUsageToday(prev => ({ ...prev, used: prev.used + 1 }));
      }
      
      // Show action notification if any
      if (response.action) {
        enqueueSnackbar(`Task ${response.action}`, { variant: 'success' });
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

  const handleSelectConversation = async (conversation: ChatConversation) => {
    try {
      setCurrentConversationId(conversation.id);
      const messages = await chatService.getConversationMessages(conversation.id);
      setMessages(messages);
      setPreviewTasks([]);
    } catch (error) {
      enqueueSnackbar('Failed to load conversation', { variant: 'error' });
    }
  };

  const handleNewConversation = () => {
    setCurrentConversationId(null);
    setMessages([{
      id: 'new-welcome',
      content: "Starting a new conversation. How can I help you with your tasks?",
      sender: 'assistant',
      timestamp: new Date().toISOString(),
    }]);
    setPreviewTasks([]);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (!window.confirm('Delete this conversation?')) return;
    
    try {
      await chatService.deleteConversation(conversationId);
      if (currentConversationId === conversationId) {
        handleNewConversation();
      }
      loadConversations();
      enqueueSnackbar('Conversation deleted', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar('Failed to delete conversation', { variant: 'error' });
    }
  };

  const drawerWidth = 280;

  const historyDrawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Chat History
        </Typography>
        <Chip
          icon={<AddIcon />}
          label="New Chat"
          onClick={handleNewConversation}
          color="primary"
          sx={{ width: '100%' }}
        />
      </Box>
      <Divider />
      <List sx={{ flex: 1, overflow: 'auto' }}>
        {conversations.map((conv) => (
          <ListItem
            key={conv.id}
            button
            selected={currentConversationId === conv.id}
            onClick={() => handleSelectConversation(conv)}
            secondaryAction={
              <IconButton
                edge="end"
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteConversation(conv.id);
                }}
              >
                <DeleteIcon />
              </IconButton>
            }
          >
            <ListItemIcon>
              <HistoryIcon />
            </ListItemIcon>
            <ListItemText
              primary={conv.title || 'Untitled Chat'}
              secondary={formatDistanceToNow(new Date(conv.created_at), { addSuffix: true })}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );

  const commandHelp = [
    { command: '/today', description: 'Show today\'s tasks' },
    { command: '/create "task"', description: 'Quick task creation' },
    { command: '/search query', description: 'Search tasks' },
    { command: '/help', description: 'Show all commands' },
  ];

  return (
    <Layout>
      <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
        {/* History Drawer */}
        <Drawer
          variant={isMobile ? 'temporary' : 'persistent'}
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              position: 'relative',
              height: '100%',
            },
          }}
        >
          {historyDrawer}
        </Drawer>

        {/* Main Chat Area */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Chat Header */}
          <AppBar position="static" color="default" elevation={1}>
            <Toolbar variant="dense">
              {isMobile && (
                <IconButton
                  edge="start"
                  onClick={() => setHistoryOpen(true)}
                  sx={{ mr: 2 }}
                >
                  <MenuIcon />
                </IconButton>
              )}
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
                onTaskClick={(task) => setPreviewTasks([task])}
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

        {/* Task Preview Panel */}
        {previewTasks.length > 0 && !isMobile && (
          <Paper
            sx={{
              width: 320,
              display: 'flex',
              flexDirection: 'column',
              borderLeft: 1,
              borderColor: 'divider',
            }}
          >
            <Box sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
              <TaskIcon sx={{ mr: 1 }} />
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Task Preview
              </Typography>
              <IconButton size="small" onClick={() => setPreviewTasks([])}>
                <CloseIcon />
              </IconButton>
            </Box>
            <Divider />
            <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
              {previewTasks.map((task) => (
                <TaskPreview
                  key={task.id}
                  task={task}
                  onUpdate={() => {
                    // Refresh task after update
                    enqueueSnackbar('Task updated', { variant: 'success' });
                  }}
                />
              ))}
            </Box>
          </Paper>
        )}
      </Box>
    </Layout>
  );
}