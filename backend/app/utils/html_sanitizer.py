"""HTML sanitization utility for rich text content."""
import bleach
from typing import Optional

# Allowed HTML tags for rich text content
ALLOWED_TAGS = [
    'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'strong', 'em', 'u', 's', 'sub', 'sup',
    'blockquote', 'pre', 'code',
    'a', 'img',
    'span', 'div'
]

# Allowed attributes for specific tags
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'style'],
    'blockquote': ['class'],
    'pre': ['class'],
    'code': ['class'],
    'span': ['style'],
    'div': ['style'],
    '*': ['class']  # Allow class on all elements
}

# Allowed CSS properties for style attributes
ALLOWED_STYLES = [
    'color', 'background-color',
    'font-size', 'font-weight', 'font-style', 'font-family',
    'text-align', 'text-decoration', 'text-indent',
    'line-height',
    'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
    'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
    'width', 'height', 'max-width', 'max-height',
    'display', 'float', 'clear',
    'border', 'border-radius'
]

def sanitize_html(content: Optional[str]) -> Optional[str]:
    """
    Sanitize HTML content to prevent XSS attacks while preserving formatting.
    
    Args:
        content: HTML content to sanitize
        
    Returns:
        Sanitized HTML content or None if input is None
    """
    if not content:
        return content
    
    # If content doesn't contain HTML tags, return as is
    if '<' not in content and '>' not in content:
        return content
    
    # Clean the HTML
    cleaned = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,  # Strip disallowed tags instead of escaping
        strip_comments=True
    )
    
    # Additional cleaning for links
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[_add_link_attrs],
        skip_tags=['pre', 'code']  # Don't linkify inside code blocks
    )
    
    return cleaned

def _add_link_attrs(attrs, new=False):
    """Add security attributes to links."""
    attrs[(None, 'rel')] = 'noopener noreferrer'
    if new:
        attrs[(None, 'target')] = '_blank'
    return attrs

def extract_plain_text(html_content: Optional[str]) -> str:
    """
    Extract plain text from HTML content.
    
    Args:
        html_content: HTML content to extract text from
        
    Returns:
        Plain text content
    """
    if not html_content:
        return ""
    
    # If it's already plain text, return as is
    if '<' not in html_content and '>' not in html_content:
        return html_content
    
    # Use bleach to strip all HTML tags
    return bleach.clean(html_content, tags=[], strip=True)