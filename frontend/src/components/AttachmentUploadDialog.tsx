import { useState, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Alert,
  Paper,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Close as CloseIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import { useDropzone } from 'react-dropzone';

import type { TaskAttachment } from '../types';
import { taskService } from '../services/taskService';

interface AttachmentUploadDialogProps {
  open: boolean;
  onClose: () => void;
  taskId: string;
  onUploadComplete: (attachments: TaskAttachment[]) => void;
}

interface FileUpload {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  attachment?: TaskAttachment;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_FILES = 10;

export default function AttachmentUploadDialog({
  open,
  onClose,
  taskId,
  onUploadComplete,
}: AttachmentUploadDialogProps) {
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    rejectedFiles.forEach((rejection) => {
      const error = rejection.errors[0];
      if (error.code === 'file-too-large') {
        enqueueSnackbar(`${rejection.file.name} is too large. Maximum size is 50MB.`, {
          variant: 'error',
        });
      } else {
        enqueueSnackbar(`${rejection.file.name} was rejected: ${error.message}`, {
          variant: 'error',
        });
      }
    });

    // Add accepted files
    const newFiles: FileUpload[] = acceptedFiles.map((file) => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending' as const,
      progress: 0,
    }));

    setFiles((prev) => {
      const total = prev.length + newFiles.length;
      if (total > MAX_FILES) {
        enqueueSnackbar(`Maximum ${MAX_FILES} files allowed`, { variant: 'warning' });
        return [...prev, ...newFiles.slice(0, MAX_FILES - prev.length)];
      }
      return [...prev, ...newFiles];
    });
  }, [enqueueSnackbar]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: MAX_FILE_SIZE,
    maxFiles: MAX_FILES,
    disabled: uploading,
  });

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const uploadFiles = async () => {
    setUploading(true);
    const pendingFiles = files.filter((f) => f.status === 'pending');
    const uploadedAttachments: TaskAttachment[] = [];

    for (const fileUpload of pendingFiles) {
      try {
        // Update status to uploading
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileUpload.id
              ? { ...f, status: 'uploading' as const, progress: 0 }
              : f
          )
        );

        // Upload file
        const attachment = await taskService.uploadAttachment(
          taskId,
          fileUpload.file,
          (progress) => {
            // Update progress
            setFiles((prev) =>
              prev.map((f) =>
                f.id === fileUpload.id ? { ...f, progress } : f
              )
            );
          }
        );

        // Update status to success
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileUpload.id
              ? { ...f, status: 'success' as const, progress: 100, attachment }
              : f
          )
        );

        uploadedAttachments.push(attachment);
      } catch (error) {
        // Update status to error
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileUpload.id
              ? {
                  ...f,
                  status: 'error' as const,
                  error: error instanceof Error ? error.message : 'Upload failed',
                }
              : f
          )
        );
      }
    }

    setUploading(false);

    if (uploadedAttachments.length > 0) {
      enqueueSnackbar(
        `Successfully uploaded ${uploadedAttachments.length} file${
          uploadedAttachments.length !== 1 ? 's' : ''
        }`,
        { variant: 'success' }
      );
      onUploadComplete(uploadedAttachments);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFiles([]);
      onClose();
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const pendingCount = files.filter((f) => f.status === 'pending').length;
  const hasErrors = files.some((f) => f.status === 'error');

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Upload Attachments
        {files.length > 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            ({files.length}/{MAX_FILES} files)
          </Typography>
        )}
      </DialogTitle>
      <DialogContent>
        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'divider',
            borderRadius: 1,
            p: 3,
            textAlign: 'center',
            cursor: uploading ? 'not-allowed' : 'pointer',
            backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
            transition: 'all 0.2s',
            mb: 2,
          }}
        >
          <input {...getInputProps()} />
          <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          <Typography>
            {isDragActive
              ? 'Drop the files here...'
              : 'Drag & drop files here, or click to select'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Maximum file size: 50MB
          </Typography>
        </Box>

        {files.length > 0 && (
          <List dense>
            {files.map((fileUpload) => (
              <ListItem key={fileUpload.id} component={Paper} sx={{ mb: 1 }}>
                <ListItemIcon>
                  {fileUpload.status === 'success' && <SuccessIcon color="success" />}
                  {fileUpload.status === 'error' && <ErrorIcon color="error" />}
                  {fileUpload.status === 'pending' && <UploadIcon color="disabled" />}
                  {fileUpload.status === 'uploading' && <UploadIcon color="primary" />}
                </ListItemIcon>
                <ListItemText
                  primary={fileUpload.file.name}
                  secondary={
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {formatFileSize(fileUpload.file.size)}
                      </Typography>
                      {fileUpload.error && (
                        <Typography variant="caption" color="error" display="block">
                          {fileUpload.error}
                        </Typography>
                      )}
                      {fileUpload.status === 'uploading' && (
                        <LinearProgress
                          variant="determinate"
                          value={fileUpload.progress}
                          sx={{ mt: 0.5 }}
                        />
                      )}
                    </Box>
                  }
                />
                {!uploading && fileUpload.status !== 'success' && (
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => removeFile(fileUpload.id)}
                      size="small"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                )}
              </ListItem>
            ))}
          </List>
        )}

        {hasErrors && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Some files failed to upload. You can remove them and try again.
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          {files.some((f) => f.status === 'success') ? 'Done' : 'Cancel'}
        </Button>
        {pendingCount > 0 && (
          <Button
            onClick={uploadFiles}
            variant="contained"
            disabled={uploading}
            startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {uploading ? 'Uploading...' : `Upload ${pendingCount} file${pendingCount !== 1 ? 's' : ''}`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}