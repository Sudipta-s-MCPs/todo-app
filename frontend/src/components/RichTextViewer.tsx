import React, { useMemo } from 'react';
import DOMPurify from 'dompurify';
import { Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

// Styled wrapper for rich text content
const ContentWrapper = styled(Box)(({ theme }) => ({
  '& p, & ol, & ul, & pre, & blockquote': {
    marginTop: 0,
    marginBottom: theme.spacing(1),
    '&:last-child': {
      marginBottom: 0,
    },
  },
  '& h1, & h2, & h3': {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(1),
    fontWeight: 600,
    '&:first-child': {
      marginTop: 0,
    },
  },
  '& h1': {
    fontSize: '2em',
  },
  '& h2': {
    fontSize: '1.5em',
  },
  '& h3': {
    fontSize: '1.2em',
  },
  '& ul, & ol': {
    paddingLeft: theme.spacing(3),
  },
  '& blockquote': {
    borderLeft: `4px solid ${theme.palette.divider}`,
    paddingLeft: theme.spacing(2),
    marginLeft: 0,
    color: theme.palette.text.secondary,
    fontStyle: 'italic',
  },
  '& pre': {
    backgroundColor: theme.palette.background.default,
    padding: theme.spacing(1.5),
    borderRadius: theme.shape.borderRadius,
    overflow: 'auto',
    fontFamily: 'monospace',
    fontSize: '0.9em',
  },
  '& code': {
    backgroundColor: theme.palette.background.default,
    padding: '2px 4px',
    borderRadius: 3,
    fontFamily: 'monospace',
    fontSize: '0.9em',
  },
  '& pre code': {
    backgroundColor: 'transparent',
    padding: 0,
  },
  '& a': {
    color: theme.palette.primary.main,
    textDecoration: 'none',
    '&:hover': {
      textDecoration: 'underline',
    },
  },
  '& img': {
    maxWidth: '100%',
    height: 'auto',
    borderRadius: theme.shape.borderRadius,
    marginTop: theme.spacing(1),
    marginBottom: theme.spacing(1),
  },
  '& hr': {
    border: 'none',
    borderTop: `1px solid ${theme.palette.divider}`,
    margin: theme.spacing(2, 0),
  },
  '& table': {
    borderCollapse: 'collapse',
    width: '100%',
    marginTop: theme.spacing(1),
    marginBottom: theme.spacing(1),
  },
  '& table, & th, & td': {
    border: `1px solid ${theme.palette.divider}`,
  },
  '& th, & td': {
    padding: theme.spacing(1),
    textAlign: 'left',
  },
  '& th': {
    backgroundColor: theme.palette.background.default,
    fontWeight: 600,
  },
}));

interface RichTextViewerProps {
  content: string;
  label?: string;
  emptyText?: string;
  maxHeight?: number | string;
}

const RichTextViewer: React.FC<RichTextViewerProps> = ({
  content,
  label,
  emptyText = 'No description provided',
  maxHeight,
}) => {
  // Sanitize HTML content to prevent XSS attacks
  const sanitizedContent = useMemo(() => {
    if (!content || content.trim() === '') {
      return '';
    }

    // Configure DOMPurify to allow safe HTML elements and attributes
    const config = {
      ALLOWED_TAGS: [
        'p', 'br', 'span', 'div',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'strong', 'b', 'em', 'i', 'u', 's', 'strike',
        'a', 'img',
        'blockquote', 'code', 'pre',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr',
      ],
      ALLOWED_ATTR: [
        'href', 'target', 'rel',
        'src', 'alt', 'width', 'height',
        'style', 'class',
      ],
      ALLOWED_STYLE_PROPS: [
        'color', 'background-color',
        'font-size', 'font-weight', 'font-style',
        'text-decoration', 'text-align',
        'margin', 'padding',
      ],
      ALLOW_DATA_ATTR: false,
    };

    const clean = DOMPurify.sanitize(content, config);
    
    // If content was plain text, convert line breaks to <br> tags
    if (!content.includes('<') && !content.includes('>')) {
      return content.replace(/\n/g, '<br />');
    }
    
    return clean;
  }, [content]);

  // Check if content is empty
  const isEmpty = !sanitizedContent || sanitizedContent.trim() === '';

  return (
    <Box>
      {label && (
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          {label}
        </Typography>
      )}
      
      {isEmpty ? (
        <Typography variant="body2" color="text.disabled" sx={{ fontStyle: 'italic' }}>
          {emptyText}
        </Typography>
      ) : (
        <ContentWrapper
          sx={{
            maxHeight: maxHeight,
            overflowY: maxHeight ? 'auto' : undefined,
          }}
          dangerouslySetInnerHTML={{ __html: sanitizedContent }}
        />
      )}
    </Box>
  );
};

export default RichTextViewer;