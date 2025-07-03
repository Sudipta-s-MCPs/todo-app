"""
Email service for sending notifications
Created: 2025-07-02 16:10:00 PST
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
import logging
from jinja2 import Template
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.settings import SystemSetting
from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        self.smtp_config: Optional[Dict[str, Any]] = None
        
    async def load_smtp_config(self, db: AsyncSession) -> Dict[str, Any]:
        """Load SMTP configuration from database"""
        # Get all email settings
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.category == "email")
        )
        settings = result.scalars().all()
        
        # Convert to dict
        config = {}
        for setting in settings:
            # Convert value based on type
            if setting.value_type == "bool":
                config[setting.key] = setting.value == "true"
            elif setting.value_type == "int":
                config[setting.key] = int(setting.value) if setting.value else 0
            else:
                config[setting.key] = setting.value or ""
                
        self.smtp_config = config
        return config
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send email to recipients"""
        try:
            # Load config if not already loaded
            if not self.smtp_config and db:
                await self.load_smtp_config(db)
            
            if not self.smtp_config:
                logger.error("SMTP configuration not loaded")
                return False
                
            # Check if SMTP is enabled
            if not self.smtp_config.get("smtp_enabled", False):
                logger.info("SMTP is disabled, skipping email")
                return False
                
            # Validate required settings
            required = ["smtp_host", "smtp_port", "smtp_from_email"]
            for key in required:
                if not self.smtp_config.get(key):
                    logger.error(f"Missing required SMTP setting: {key}")
                    return False
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.smtp_config.get('smtp_from_name', 'Smart ToDo')} <{self.smtp_config['smtp_from_email']}>"
            msg["To"] = ", ".join(to_emails)
            
            # Add text part
            text_part = MIMEText(body, "plain")
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                msg.attach(html_part)
            
            # Connect to SMTP server
            if self.smtp_config.get("smtp_use_ssl", False):
                server = smtplib.SMTP_SSL(
                    self.smtp_config["smtp_host"],
                    self.smtp_config["smtp_port"],
                    timeout=self.smtp_config.get("smtp_timeout", 30)
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_config["smtp_host"],
                    self.smtp_config["smtp_port"],
                    timeout=self.smtp_config.get("smtp_timeout", 30)
                )
                
                if self.smtp_config.get("smtp_use_tls", True):
                    server.starttls()
            
            # Authenticate if credentials provided
            if self.smtp_config.get("smtp_username") and self.smtp_config.get("smtp_password"):
                server.login(
                    self.smtp_config["smtp_username"],
                    self.smtp_config["smtp_password"]
                )
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    async def send_approval_email(
        self,
        user_email: str,
        user_name: str,
        approved: bool,
        rejection_reason: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send user approval status email"""
        # Check if approval notifications are enabled
        if db:
            await self.load_smtp_config(db)
            
        if not self.smtp_config.get("email_approval_notifications", True):
            logger.info("Approval notifications disabled")
            return False
        
        # Prepare email content
        if approved:
            subject = "Your Smart ToDo Account Has Been Approved"
            body = f"""
Hello {user_name},

Great news! Your Smart ToDo account has been approved and is now active.

You can now log in at: {settings.FRONTEND_URL or 'http://localhost:3000'}

If you have any questions or need assistance, please don't hesitate to reach out.

Best regards,
The Smart ToDo Team
"""
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4A90E2;">Welcome to Smart ToDo!</h2>
        <p>Hello {user_name},</p>
        <p>Great news! Your Smart ToDo account has been <strong style="color: #27ae60;">approved</strong> and is now active.</p>
        <p>You can now log in at: <a href="{settings.FRONTEND_URL or 'http://localhost:3000'}" style="color: #4A90E2;">Smart ToDo</a></p>
        <p>If you have any questions or need assistance, please don't hesitate to reach out.</p>
        <p>Best regards,<br>The Smart ToDo Team</p>
    </div>
</body>
</html>
"""
        else:
            subject = "Smart ToDo Account Registration Update"
            body = f"""
Hello {user_name},

Thank you for your interest in Smart ToDo. After reviewing your registration, we regret to inform you that your account application has not been approved at this time.

{f'Reason: {rejection_reason}' if rejection_reason else ''}

If you believe this decision was made in error or have questions, please contact our support team.

Best regards,
The Smart ToDo Team
"""
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4A90E2;">Smart ToDo Account Registration Update</h2>
        <p>Hello {user_name},</p>
        <p>Thank you for your interest in Smart ToDo. After reviewing your registration, we regret to inform you that your account application has not been approved at this time.</p>
        {f'<p><strong>Reason:</strong> {rejection_reason}</p>' if rejection_reason else ''}
        <p>If you believe this decision was made in error or have questions, please contact our support team.</p>
        <p>Best regards,<br>The Smart ToDo Team</p>
    </div>
</body>
</html>
"""
        
        return await self.send_email(
            to_emails=[user_email],
            subject=subject,
            body=body,
            html_body=html_body,
            db=db
        )


# Global email service instance
email_service = EmailService()