import React, { useRef, useMemo, useCallback } from 'react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { Box, Typography, useTheme } from '@mui/material';
import { styled } from '@mui/material/styles';
import { useSnackbar } from 'notistack';
import { attachmentService } from '../services/attachmentService';

// Styled wrapper for the editor
const EditorWrapper = styled(Box)(({ theme }) => ({
  '& .quill': {
    borderRadius: theme.shape.borderRadius,
    backgroundColor: theme.palette.background.paper,
    '& .ql-toolbar': {
      borderTopLeftRadius: theme.shape.borderRadius,
      borderTopRightRadius: theme.shape.borderRadius,
      borderColor: theme.palette.divider,
      backgroundColor: theme.palette.background.default,
    },
    '& .ql-container': {
      borderBottomLeftRadius: theme.shape.borderRadius,
      borderBottomRightRadius: theme.shape.borderRadius,
      borderColor: theme.palette.divider,
      fontSize: theme.typography.body1.fontSize,
      fontFamily: theme.typography.fontFamily,
    },
    '& .ql-editor': {
      minHeight: '150px',
      maxHeight: '400px',
      overflowY: 'auto',
      '&.ql-blank::before': {
        color: theme.palette.text.disabled,
        fontStyle: 'normal',
      },
    },
    '& .ql-editor p, & .ql-editor ol, & .ql-editor ul, & .ql-editor pre, & .ql-editor blockquote, & .ql-editor h1, & .ql-editor h2, & .ql-editor h3': {
      marginBottom: theme.spacing(1),
    },
    '& .ql-editor h1': {
      fontSize: '2em',
    },
    '& .ql-editor h2': {
      fontSize: '1.5em',
    },
    '& .ql-editor h3': {
      fontSize: '1.2em',
    },
    '& .ql-snow .ql-stroke': {
      stroke: theme.palette.text.primary,
    },
    '& .ql-snow .ql-fill': {
      fill: theme.palette.text.primary,
    },
    '& .ql-snow .ql-picker': {
      color: theme.palette.text.primary,
    },
  },
}));

interface RichTextEditorProps {
  value: string;
  onChange: (content: string) => void;
  placeholder?: string;
  label?: string;
  error?: boolean;
  helperText?: string;
  readOnly?: boolean;
  taskId?: string; // Optional task ID for image uploads
  enableImageUpload?: boolean; // Enable/disable image upload functionality
}

const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  placeholder = 'Write your description here...',
  label,
  error,
  helperText,
  readOnly = false,
  taskId,
  enableImageUpload = true,
}) => {
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const quillRef = useRef<ReactQuill | null>(null);

  // Custom image handler
  const imageHandler = useCallback(() => {
    if (!enableImageUpload) {
      enqueueSnackbar('Image upload is not enabled', { variant: 'warning' });
      return;
    }

    if (!taskId) {
      // For new tasks, just prompt for URL
      const url = prompt('Enter image URL:');
      if (url) {
        const quill = quillRef.current?.getEditor();
        if (quill) {
          const range = quill.getSelection();
          if (range) {
            quill.insertEmbed(range.index, 'image', url);
          }
        }
      }
      return;
    }

    // Create file input
    const input = document.createElement('input');
    input.setAttribute('type', 'file');
    input.setAttribute('accept', 'image/*');
    input.click();

    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;

      // Validate file type
      if (!file.type.startsWith('image/')) {
        enqueueSnackbar('Please select an image file', { variant: 'error' });
        return;
      }

      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        enqueueSnackbar('Image size must be less than 10MB', { variant: 'error' });
        return;
      }

      try {
        enqueueSnackbar('Uploading image...', { variant: 'info' });

        // Upload image as attachment
        const response = await attachmentService.uploadAttachment(taskId, file, {
          description: 'Image from task description'
        });

        // Insert image into editor
        const quill = quillRef.current?.getEditor();
        const imageUrl = response.download_url || response.url;
        if (quill && imageUrl) {
          const range = quill.getSelection();
          if (range) {
            quill.insertEmbed(range.index, 'image', imageUrl);
          }
        }

        enqueueSnackbar('Image uploaded successfully', { variant: 'success' });
      } catch (error: any) {
        console.error('Failed to upload image:', error);
        enqueueSnackbar(error.message || 'Failed to upload image', { variant: 'error' });
      }
    };
  }, [taskId, enableImageUpload, enqueueSnackbar]);

  // Quill modules configuration
  const modules = useMemo(() => {
    const config: any = {
      toolbar: readOnly ? false : {
        container: [
          [{ 'header': [1, 2, 3, false] }],
          ['bold', 'italic', 'underline', 'strike'],
          ['blockquote', 'code-block'],
          [{ 'list': 'ordered' }, { 'list': 'bullet' }],
          [{ 'indent': '-1' }, { 'indent': '+1' }],
          [{ 'color': [] }, { 'background': [] }],
          ['link', 'image'],
          ['clean'],
        ],
        handlers: enableImageUpload ? {
          image: imageHandler
        } : {}
      },
      clipboard: {
        matchVisual: false,
      },
    };
    return config;
  }, [readOnly, enableImageUpload, imageHandler]);

  // Quill formats
  const formats = [
    'header',
    'bold', 'italic', 'underline', 'strike',
    'blockquote', 'code-block',
    'list', 'bullet',
    'indent',
    'link', 'image',
    'color', 'background',
  ];

  const handleChange = (content: string, _delta: any, _source: any, editor: any) => {
    // If the editor is empty (only contains <p><br></p>), treat it as empty string
    const isEmpty = editor.getText().trim() === '';
    onChange(isEmpty ? '' : content);
  };

  return (
    <Box>
      {label && (
        <Typography
          variant="subtitle2"
          color={error ? 'error' : 'text.secondary'}
          gutterBottom
          sx={{ mb: 1 }}
        >
          {label}
        </Typography>
      )}
      
      <EditorWrapper
        sx={{
          '& .quill': {
            border: error ? `1px solid ${theme.palette.error.main}` : undefined,
          },
        }}
      >
        <ReactQuill
          ref={quillRef}
          theme="snow"
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          modules={modules}
          formats={formats}
          readOnly={readOnly}
        />
      </EditorWrapper>

      {helperText && (
        <Typography
          variant="caption"
          color={error ? 'error' : 'text.secondary'}
          sx={{ mt: 0.5, display: 'block' }}
        >
          {helperText}
        </Typography>
      )}
    </Box>
  );
};

export default RichTextEditor;