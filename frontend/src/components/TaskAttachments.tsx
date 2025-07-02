import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  CircularProgress,
  Tooltip,
  Chip,
  Paper,
  Button,
} from '@mui/material';
import {
  AttachFile as AttachIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Image as ImageIcon,
  PictureAsPdf as PdfIcon,
  Description as DocIcon,
  Folder as ZipIcon,
  Code as CodeIcon,
  AudioFile as AudioIcon,
  VideoFile as VideoIcon,
  InsertDriveFile as FileIcon,
  CloudUpload as UploadIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { formatDistanceToNow } from 'date-fns';

import type { TaskAttachment } from '../types';
import { taskService } from '../services/taskService';
import AttachmentUploadDialog from './AttachmentUploadDialog';

interface TaskAttachmentsProps {
  taskId: string;
  onAttachmentsChange?: (count: number) => void;
}

const getFileIcon = (mimeType: string) => {
  if (mimeType.startsWith('image/')) return ImageIcon;
  if (mimeType === 'application/pdf') return PdfIcon;
  if (mimeType.startsWith('audio/')) return AudioIcon;
  if (mimeType.startsWith('video/')) return VideoIcon;
  if (mimeType.includes('zip') || mimeType.includes('tar') || mimeType.includes('rar')) return ZipIcon;
  if (mimeType.includes('word') || mimeType.includes('document')) return DocIcon;
  if (mimeType.includes('code') || mimeType.includes('text/')) return CodeIcon;
  return FileIcon;
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export default function TaskAttachments({ taskId, onAttachmentsChange }: TaskAttachmentsProps) {
  const [attachments, setAttachments] = useState<TaskAttachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    loadAttachments();
  }, [taskId]);

  const loadAttachments = async () => {
    try {
      setLoading(true);
      const data = await taskService.getAttachments(taskId);
      setAttachments(data);
      onAttachmentsChange?.(data.length);
    } catch (error) {
      console.error('Failed to load attachments:', error);
      enqueueSnackbar('Failed to load attachments', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (attachment: TaskAttachment) => {
    try {
      const blob = await taskService.downloadAttachment(attachment.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = attachment.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download attachment:', error);
      enqueueSnackbar('Failed to download attachment', { variant: 'error' });
    }
  };

  const handleDelete = async (attachmentId: string) => {
    if (!window.confirm('Are you sure you want to delete this attachment?')) {
      return;
    }

    try {
      setDeleting(attachmentId);
      await taskService.deleteAttachment(attachmentId);
      setAttachments(prev => prev.filter(a => a.id !== attachmentId));
      onAttachmentsChange?.(attachments.length - 1);
      enqueueSnackbar('Attachment deleted', { variant: 'success' });
    } catch (error) {
      console.error('Failed to delete attachment:', error);
      enqueueSnackbar('Failed to delete attachment', { variant: 'error' });
    } finally {
      setDeleting(null);
    }
  };

  const handleUploadComplete = (newAttachments: TaskAttachment[]) => {
    setAttachments(prev => [...prev, ...newAttachments]);
    onAttachmentsChange?.(attachments.length + newAttachments.length);
    setUploadOpen(false);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (attachments.length === 0) {
    return (
      <Box textAlign="center" py={4}>
        <AttachIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography color="text.secondary" gutterBottom>
          No attachments yet
        </Typography>
        <Button
          startIcon={<UploadIcon />}
          onClick={() => setUploadOpen(true)}
          variant="outlined"
          size="small"
        >
          Upload Files
        </Button>
        <AttachmentUploadDialog
          open={uploadOpen}
          onClose={() => setUploadOpen(false)}
          taskId={taskId}
          onUploadComplete={handleUploadComplete}
        />
      </Box>
    );
  }

  const FileIconComponent = getFileIcon;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="subtitle2" color="text.secondary">
          {attachments.length} attachment{attachments.length !== 1 ? 's' : ''}
        </Typography>
        <Button
          startIcon={<UploadIcon />}
          onClick={() => setUploadOpen(true)}
          size="small"
        >
          Upload
        </Button>
      </Box>

      <List dense>
        {attachments.map((attachment) => {
          const Icon = getFileIcon(attachment.mime_type);
          return (
            <ListItem key={attachment.id} component={Paper} sx={{ mb: 1 }}>
              <ListItemIcon>
                <Icon color="action" />
              </ListItemIcon>
              <ListItemText
                primary={attachment.filename}
                secondary={
                  <Box display="flex" gap={1} alignItems="center">
                    <Chip 
                      label={formatFileSize(attachment.file_size)} 
                      size="small" 
                      variant="outlined"
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatDistanceToNow(new Date(attachment.uploaded_at), { addSuffix: true })}
                    </Typography>
                    {attachment.uploader_name && (
                      <Typography variant="caption" color="text.secondary">
                        by {attachment.uploader_name}
                      </Typography>
                    )}
                  </Box>
                }
              />
              <ListItemSecondaryAction>
                <Tooltip title="Download">
                  <IconButton
                    edge="end"
                    onClick={() => handleDownload(attachment)}
                    size="small"
                  >
                    <DownloadIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete">
                  <IconButton
                    edge="end"
                    onClick={() => handleDelete(attachment.id)}
                    disabled={deleting === attachment.id}
                    size="small"
                  >
                    {deleting === attachment.id ? (
                      <CircularProgress size={20} />
                    ) : (
                      <DeleteIcon />
                    )}
                  </IconButton>
                </Tooltip>
              </ListItemSecondaryAction>
            </ListItem>
          );
        })}
      </List>

      <AttachmentUploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        taskId={taskId}
        onUploadComplete={handleUploadComplete}
      />
    </Box>
  );
}