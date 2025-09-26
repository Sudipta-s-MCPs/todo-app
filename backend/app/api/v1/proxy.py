"""
Proxy endpoints for serving external resources securely
Created: 2025-07-14
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional
import httpx
from urllib.parse import unquote

from app.models.user import User
from app.api.deps import get_current_user
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/images/minio/{path:path}")
async def proxy_minio_image(
    path: str,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy MinIO images through HTTPS to avoid mixed content issues
    """
    try:
        # Decode the path
        decoded_path = unquote(path)
        
        # Construct MinIO URL - using the internal MinIO endpoint
        minio_url = f"http://192.168.11.100:7612/{decoded_path}"
        
        # Fetch the image from MinIO
        async with httpx.AsyncClient() as client:
            response = await client.get(
                minio_url,
                timeout=30.0,
                follow_redirects=True
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch image from MinIO"
                )
            
            # Stream the response back
            return StreamingResponse(
                content=response.iter_bytes(),
                media_type=response.headers.get("content-type", "image/png"),
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "X-Content-Type-Options": "nosniff",
                }
            )
            
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy MinIO image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch image from storage"
        )
    except Exception as e:
        logger.error(f"Unexpected error proxying image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/images/external")
async def proxy_external_image(
    url: str,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy external images to avoid CORS issues
    """
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        # Basic security check - avoid localhost/private IPs
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.hostname in ['localhost', '127.0.0.1'] or parsed.hostname.startswith('192.168.') or parsed.hostname.startswith('10.') or parsed.hostname.startswith('172.'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access to private networks not allowed"
            )
        
        # Fetch the external image
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "TodoApp/1.0"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch external image"
                )
            
            # Validate content type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL does not point to an image"
                )
            
            # Stream the response back with CORS headers
            return StreamingResponse(
                content=response.iter_bytes(),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "X-Content-Type-Options": "nosniff",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                }
            )
            
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy external image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch external image"
        )
    except Exception as e:
        logger.error(f"Unexpected error proxying external image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )