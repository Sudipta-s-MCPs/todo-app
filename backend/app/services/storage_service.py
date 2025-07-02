"""
Object storage service using Minio
Created: 2025-01-02 11:30:00 PST
"""

import os
import io
import json
from typing import Optional, Dict, Any, BinaryIO
from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import mimetypes

from minio import Minio
from minio.error import S3Error
from minio.datatypes import Object as MinioObject

from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Service for managing file storage in Minio"""
    
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "smart-todo")
        
        # Initialize Minio client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure bucket exists
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure the bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(f"Creating Minio bucket: {self.bucket_name}")
                self.client.make_bucket(self.bucket_name)
                
                # Set bucket policy to allow read access to attachments
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/attachments/*"]
                        }
                    ]
                }
                self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
                logger.info(f"Bucket {self.bucket_name} created successfully")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure bucket: {str(e)}")
            raise
    
    def _generate_object_name(
        self, 
        file_name: str, 
        user_id: UUID, 
        task_id: UUID,
        prefix: str = "attachments"
    ) -> str:
        """Generate a unique object name for storage"""
        # Extract extension
        _, ext = os.path.splitext(file_name)
        
        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Create unique name
        unique_part = hashlib.md5(f"{user_id}{task_id}{timestamp}".encode()).hexdigest()[:8]
        
        # Build path: prefix/user_id/task_id/timestamp_unique_filename
        object_name = f"{prefix}/{user_id}/{task_id}/{timestamp}_{unique_part}{ext}"
        
        return object_name
    
    async def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        file_size: int,
        content_type: str,
        user_id: UUID,
        task_id: UUID,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload a file to storage"""
        try:
            # Generate object name
            object_name = self._generate_object_name(file_name, user_id, task_id)
            
            # Prepare metadata
            storage_metadata = {
                "user_id": str(user_id),
                "task_id": str(task_id),
                "original_name": file_name,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            if metadata:
                storage_metadata.update(metadata)
            
            # Upload file
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=storage_metadata
            )
            
            # Generate access URL
            url = self.get_file_url(object_name)
            
            return {
                "object_name": object_name,
                "url": url,
                "size": file_size,
                "content_type": content_type,
                "etag": result.etag,
                "version_id": result.version_id
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise
    
    def get_file_url(
        self, 
        object_name: str, 
        expiry: Optional[timedelta] = None
    ) -> str:
        """Get URL for accessing a file"""
        try:
            if expiry:
                # Generate presigned URL
                return self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    expires=expiry
                )
            else:
                # Generate permanent URL (requires public read policy)
                protocol = "https" if self.secure else "http"
                return f"{protocol}://{self.endpoint}/{self.bucket_name}/{object_name}"
                
        except Exception as e:
            logger.error(f"Failed to generate file URL: {str(e)}")
            raise
    
    async def download_file(self, object_name: str) -> tuple[bytes, Dict[str, str]]:
        """Download a file from storage"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            metadata = dict(response.headers)
            response.close()
            response.release_conn()
            
            return data, metadata
            
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from storage"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False
    
    async def delete_task_files(self, task_id: UUID) -> int:
        """Delete all files associated with a task"""
        try:
            prefix = f"attachments/"
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            deleted_count = 0
            for obj in objects:
                # Check if object belongs to this task
                if f"/{task_id}/" in obj.object_name:
                    await self.delete_file(obj.object_name)
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete task files: {str(e)}")
            return 0
    
    async def get_file_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a stored file"""
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            
            return {
                "object_name": object_name,
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "metadata": stat.metadata
            }
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            raise
    
    async def list_task_files(self, task_id: UUID) -> list[Dict[str, Any]]:
        """List all files for a task"""
        try:
            prefix = f"attachments/"
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            files = []
            for obj in objects:
                # Check if object belongs to this task
                if f"/{task_id}/" in obj.object_name:
                    files.append({
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "etag": obj.etag,
                        "last_modified": obj.last_modified
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list task files: {str(e)}")
            return []
    
    def get_upload_presigned_url(
        self,
        file_name: str,
        user_id: UUID,
        task_id: UUID,
        expiry: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Generate presigned URL for direct upload from client"""
        try:
            object_name = self._generate_object_name(file_name, user_id, task_id)
            
            # Generate presigned POST data
            post_data = self.client.presigned_post_policy(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expiry
            )
            
            return {
                "url": post_data["url"],
                "fields": post_data["fields"],
                "object_name": object_name,
                "expires_at": (datetime.utcnow() + expiry).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate upload URL: {str(e)}")
            raise


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create storage service instance"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service