"""
Smart Task Parser for MCP - Self-contained version
Created: 2025-01-02 06:30:00 PST
Updated: 2025-07-05 - Made self-contained without backend dependencies
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class SmartTaskParser:
    """Parse natural language task input into structured data"""
    
    # Priority keywords mapping
    PRIORITY_KEYWORDS = {
        "high": ["urgent", "asap", "important", "critical", "high priority", "immediately"],
        "medium": ["normal", "regular", "standard", "moderate"],
        "low": ["low priority", "when possible", "eventually", "someday", "minor"]
    }
    
    # Relative date patterns
    RELATIVE_DATE_PATTERNS = {
        "today": 0,
        "tomorrow": 1,
        "day after tomorrow": 2,
        "next week": 7,
        "in a week": 7,
        "next month": 30,
        "in a month": 30,
    }
    
    # Workspace keywords
    WORKSPACE_KEYWORDS = {
        "personal": ["personal", "private", "home", "self"],
        "work": ["work", "office", "job", "professional", "business"],
        "shopping": ["shopping", "buy", "purchase", "groceries"],
        "health": ["health", "doctor", "medical", "fitness", "gym", "exercise"],
        "finance": ["finance", "money", "payment", "bill", "budget"],
        "learning": ["learn", "study", "course", "education", "training"],
        "project": ["project", "development", "build", "create"],
    }
    
    def __init__(self):
        """Initialize the parser"""
        pass
    
    def parse_task(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text into task components
        
        This is a simplified version that doesn't require AI service
        """
        try:
            # Clean the input text
            text = text.strip()
            
            # Initialize result
            result = {
                "title": text,
                "description": "",
                "priority": "medium",
                "due_date": None,
                "workspace": None,
                "list_name": None,
                "tags": [],
                "assigned_to": []
            }
            
            # Extract priority
            priority = self._extract_priority(text)
            if priority:
                result["priority"] = priority
            
            # Extract due date
            due_date, cleaned_text = self._extract_due_date(text)
            if due_date:
                result["due_date"] = due_date
                result["title"] = cleaned_text
            
            # Extract workspace
            workspace = self._extract_workspace(text)
            if workspace:
                result["workspace"] = workspace
            
            # Extract list name (anything after "in" or "to")
            list_match = re.search(r'\b(?:in|to)\s+(\w+(?:\s+\w+)?)\s*(?:list)?', text, re.IGNORECASE)
            if list_match:
                result["list_name"] = list_match.group(1).strip()
            
            # Extract tags (words starting with # or @)
            tags = re.findall(r'[#@](\w+)', text)
            if tags:
                result["tags"] = tags
            
            # Extract assigned users (email patterns)
            emails = re.findall(r'\b[\w._%+-]+@[\w.-]+\.[A-Z|a-z]{2,}\b', text)
            if emails:
                result["assigned_to"] = emails
            
            # Clean up title by removing extracted components
            title = result["title"]
            # Remove priority keywords
            for priority_level, keywords in self.PRIORITY_KEYWORDS.items():
                for keyword in keywords:
                    title = re.sub(rf'\b{keyword}\b', '', title, flags=re.IGNORECASE)
            
            # Remove tags
            title = re.sub(r'[#@]\w+', '', title)
            
            # Remove emails
            for email in emails:
                title = title.replace(email, '')
            
            # Remove list references
            title = re.sub(r'\b(?:in|to)\s+\w+(?:\s+\w+)?\s*(?:list)?', '', title, flags=re.IGNORECASE)
            
            # Clean up multiple spaces
            title = re.sub(r'\s+', ' ', title).strip()
            result["title"] = title
            
            logger.info(f"Parsed task: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing task: {str(e)}")
            # Return basic result on error
            return {
                "title": text,
                "description": "",
                "priority": "medium",
                "due_date": None,
                "workspace": None,
                "list_name": None,
                "tags": [],
                "assigned_to": []
            }
    
    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from text"""
        text_lower = text.lower()
        
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return priority
        
        return None
    
    def _extract_due_date(self, text: str) -> Tuple[Optional[str], str]:
        """Extract due date from text and return cleaned text"""
        try:
            # Check for relative date patterns
            text_lower = text.lower()
            for pattern, days in self.RELATIVE_DATE_PATTERNS.items():
                if pattern in text_lower:
                    due_date = datetime.now() + timedelta(days=days)
                    # Remove the pattern from text
                    cleaned_text = re.sub(rf'\b{pattern}\b', '', text, flags=re.IGNORECASE)
                    return due_date.isoformat(), cleaned_text.strip()
            
            # Check for "by" or "due" followed by a date
            date_match = re.search(r'(?:by|due|on)\s+(.+?)(?:\s|$)', text, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(1)
                try:
                    # Try to parse the date
                    parsed_date = date_parser.parse(date_str, fuzzy=True)
                    # Remove the date portion from text
                    cleaned_text = text[:date_match.start()] + text[date_match.end():]
                    return parsed_date.isoformat(), cleaned_text.strip()
                except:
                    pass
            
            # Check for day names
            days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            for day in days_of_week:
                if f"next {day}" in text_lower:
                    # Calculate days until next occurrence of this day
                    today = datetime.now()
                    target_day = days_of_week.index(day)
                    days_ahead = (target_day - today.weekday() + 7) % 7
                    if days_ahead == 0:  # If it's the same day, assume next week
                        days_ahead = 7
                    due_date = today + timedelta(days=days_ahead)
                    cleaned_text = re.sub(rf'\bnext {day}\b', '', text, flags=re.IGNORECASE)
                    return due_date.isoformat(), cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting due date: {str(e)}")
        
        return None, text
    
    def _extract_workspace(self, text: str) -> Optional[str]:
        """Extract workspace from text based on keywords"""
        text_lower = text.lower()
        
        for workspace, keywords in self.WORKSPACE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return workspace
        
        return None