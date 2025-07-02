import { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  SmartToy as AIIcon,
  Send as SendIcon,
  Title as TitleIcon,
  Folder as FolderIcon,
  Flag as PriorityIcon,
  Event as DateIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Edit as EditIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';

import type { Workspace, TaskCreate } from '../types';
import { taskService } from '../services/taskService';

interface SmartTaskInputProps {
  open: boolean;
  onClose: () => void;
  onTaskCreated: (task: any) => void;
  workspaces: Workspace[];
  defaultWorkspaceId?: string;
}

interface ParsedTaskData {
  title: string;
  description?: string;
  workspace?: string;
  list?: string;
  priority?: 'low' | 'medium' | 'high';
  due_date?: string;
  confidence: number;
  ai_reasoning?: string;
  subtasks?: string[];
  tags?: string[];
  mentions?: string[];
}

export default function SmartTaskInput({
  open,
  onClose,
  onTaskCreated,
  workspaces,
}: SmartTaskInputProps) {
  const { enqueueSnackbar } = useSnackbar();
  const [naturalText, setNaturalText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [parsedData, setParsedData] = useState<ParsedTaskData | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');

  const examples = [
    "Meeting with John next Tuesday at 2pm to discuss Q4 budget",
    "Buy groceries tomorrow - milk, eggs, bread, coffee",
    "Fix the login bug in production ASAP",
    "Review Sarah's pull request by end of week",
  ];

  const handleExampleClick = (example: string) => {
    setNaturalText(example);
  };

  const handleParse = async () => {
    if (!naturalText.trim()) return;

    setIsProcessing(true);
    try {
      // For now, we'll simulate parsing - in real implementation, this would call an API
      // that uses the smart_create_task MCP tool or a dedicated parse endpoint
      const simulatedParse: ParsedTaskData = {
        title: naturalText.slice(0, 50),
        description: naturalText.length > 50 ? naturalText : undefined,
        workspace: workspaces[0]?.name,
        list: 'General',
        priority: naturalText.toLowerCase().includes('asap') || naturalText.toLowerCase().includes('urgent') ? 'high' : 'medium',
        due_date: extractDueDate(naturalText),
        confidence: 0.85,
        ai_reasoning: "Parsed based on keywords and context",
        subtasks: extractSubtasks(naturalText),
        tags: extractTags(naturalText),
      };

      setParsedData(simulatedParse);
      setEditedTitle(simulatedParse.title);
      setShowDetails(true);
    } catch (error) {
      enqueueSnackbar('Failed to parse task', { variant: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  const extractDueDate = (text: string): string | undefined => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    if (text.toLowerCase().includes('tomorrow')) {
      return tomorrow.toISOString();
    }
    if (text.toLowerCase().includes('next tuesday')) {
      const nextTuesday = new Date();
      const daysUntilTuesday = (2 - nextTuesday.getDay() + 7) % 7 || 7;
      nextTuesday.setDate(nextTuesday.getDate() + daysUntilTuesday);
      return nextTuesday.toISOString();
    }
    return undefined;
  };

  const extractSubtasks = (text: string): string[] => {
    // Simple extraction of items after dash or comma
    if (text.includes(' - ')) {
      const parts = text.split(' - ');
      if (parts.length > 1) {
        return parts[1].split(',').map(s => s.trim()).filter(s => s);
      }
    }
    return [];
  };

  const extractTags = (text: string): string[] => {
    const tags: string[] = [];
    if (text.toLowerCase().includes('bug')) tags.push('bug');
    if (text.toLowerCase().includes('meeting')) tags.push('meeting');
    if (text.toLowerCase().includes('urgent') || text.toLowerCase().includes('asap')) tags.push('urgent');
    return tags;
  };

  const handleCreate = async () => {
    if (!parsedData) return;

    setIsProcessing(true);
    try {
      // Find the workspace and list
      const workspace = workspaces.find(w => w.name === parsedData.workspace) || workspaces[0];
      
      const taskData: TaskCreate & { list_id: string } = {
        title: isEditing ? editedTitle : parsedData.title,
        description: parsedData.description,
        workspace_id: workspace.id,
        list_id: 'default', // This would be fetched from the workspace's lists
        priority: parsedData.priority || 'medium',
        due_date: parsedData.due_date,
        tags: parsedData.tags,
      };

      // Create the task
      const createdTask = await taskService.createTask(taskData);
      
      // TODO: Create subtasks if any
      
      enqueueSnackbar('Task created successfully!', { variant: 'success' });
      onTaskCreated(createdTask);
      handleClose();
    } catch (error: any) {
      enqueueSnackbar(error.response?.data?.detail || 'Failed to create task', { variant: 'error' });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClose = () => {
    setNaturalText('');
    setParsedData(null);
    setShowDetails(false);
    setIsEditing(false);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <AIIcon color="primary" />
          <Typography variant="h6">Smart Task Creation</Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3}>
          {/* Natural Language Input */}
          <Box>
            <TextField
              fullWidth
              multiline
              rows={3}
              variant="outlined"
              placeholder="Describe your task naturally... e.g., 'Meeting with John next Tuesday at 2pm about Q4 budget'"
              value={naturalText}
              onChange={(e) => setNaturalText(e.target.value)}
              disabled={isProcessing}
              sx={{ mb: 2 }}
            />

            {/* Example Chips */}
            <Box mb={2}>
              <Typography variant="caption" color="text.secondary" gutterBottom>
                Try an example:
              </Typography>
              <Box display="flex" gap={0.5} flexWrap="wrap" mt={0.5}>
                {examples.map((example, index) => (
                  <Chip
                    key={index}
                    label={example.slice(0, 30) + '...'}
                    size="small"
                    onClick={() => handleExampleClick(example)}
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Box>
            </Box>

            <Button
              variant="contained"
              startIcon={isProcessing ? <CircularProgress size={20} /> : <AIIcon />}
              onClick={handleParse}
              disabled={!naturalText.trim() || isProcessing}
              fullWidth
            >
              {isProcessing ? 'Processing...' : 'Parse with AI'}
            </Button>
          </Box>

          {/* Parsed Results */}
          {parsedData && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="subtitle1" fontWeight="medium">
                  Parsed Task Details
                </Typography>
                <Chip
                  size="small"
                  label={`${Math.round(parsedData.confidence * 100)}% confident`}
                  color={parsedData.confidence > 0.8 ? 'success' : 'warning'}
                />
              </Box>

              {parsedData.ai_reasoning && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  <Typography variant="caption">{parsedData.ai_reasoning}</Typography>
                </Alert>
              )}

              <List dense>
                {/* Title */}
                <ListItem>
                  <ListItemIcon>
                    <TitleIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Title"
                    secondary={
                      isEditing ? (
                        <Box display="flex" alignItems="center" gap={1}>
                          <TextField
                            size="small"
                            value={editedTitle}
                            onChange={(e) => setEditedTitle(e.target.value)}
                            fullWidth
                          />
                          <IconButton size="small" onClick={() => setIsEditing(false)}>
                            <CheckIcon />
                          </IconButton>
                        </Box>
                      ) : (
                        <Box display="flex" alignItems="center" gap={1}>
                          {editedTitle}
                          <IconButton size="small" onClick={() => setIsEditing(true)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Box>
                      )
                    }
                  />
                </ListItem>

                {/* Workspace */}
                <ListItem>
                  <ListItemIcon>
                    <FolderIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary="Workspace"
                    secondary={parsedData.workspace || 'Default'}
                  />
                </ListItem>

                {/* Priority */}
                {parsedData.priority && (
                  <ListItem>
                    <ListItemIcon>
                      <PriorityIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Priority"
                      secondary={
                        <Chip
                          size="small"
                          label={parsedData.priority}
                          color={
                            parsedData.priority === 'high' ? 'error' :
                            parsedData.priority === 'medium' ? 'warning' : 'default'
                          }
                        />
                      }
                    />
                  </ListItem>
                )}

                {/* Due Date */}
                {parsedData.due_date && (
                  <ListItem>
                    <ListItemIcon>
                      <DateIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary="Due Date"
                      secondary={new Date(parsedData.due_date).toLocaleDateString()}
                    />
                  </ListItem>
                )}

                {/* More Details */}
                <ListItem button onClick={() => setShowDetails(!showDetails)}>
                  <ListItemText primary="More details" />
                  {showDetails ? <CollapseIcon /> : <ExpandIcon />}
                </ListItem>
              </List>

              <Collapse in={showDetails}>
                <Divider sx={{ my: 1 }} />
                <Stack spacing={1}>
                  {parsedData.description && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">Description:</Typography>
                      <Typography variant="body2">{parsedData.description}</Typography>
                    </Box>
                  )}

                  {parsedData.subtasks && parsedData.subtasks.length > 0 && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">Subtasks:</Typography>
                      {parsedData.subtasks.map((subtask, index) => (
                        <Typography key={index} variant="body2">• {subtask}</Typography>
                      ))}
                    </Box>
                  )}

                  {parsedData.tags && parsedData.tags.length > 0 && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">Tags:</Typography>
                      <Box display="flex" gap={0.5} mt={0.5}>
                        {parsedData.tags.map((tag) => (
                          <Chip key={tag} label={tag} size="small" />
                        ))}
                      </Box>
                    </Box>
                  )}
                </Stack>
              </Collapse>
            </Paper>
          )}
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          startIcon={<SendIcon />}
          onClick={handleCreate}
          disabled={!parsedData || isProcessing}
        >
          Create Task
        </Button>
      </DialogActions>
    </Dialog>
  );
}