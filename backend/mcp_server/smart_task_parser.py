"""
Smart Task Parser for MCP using AI
Created: 2025-01-02 06:30:00 PST
"""

import os
import sys
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import asyncio

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_service import get_ai_service, TaskAnalysis
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SmartTaskParser:
    """Parse natural language task input into structured data"""
    
    # Priority keywords mapping
    PRIORITY_KEYWORDS = {
        "high": ["urgent", "asap", "important", "critical", "high priority", "immediately"],
        "medium": ["normal", "regular", "standard", "moderate"],
        "low": ["low priority", "when possible", "eventually", "someday", "minor"]
    }
    
    # Common date patterns
    DATE_PATTERNS = {
        r"\b(today)\b": lambda: datetime.now().date(),
        r"\b(tomorrow)\b": lambda: (datetime.now() + timedelta(days=1)).date(),
        r"\b(next week)\b": lambda: (datetime.now() + timedelta(weeks=1)).date(),
        r"\b(next month)\b": lambda: (datetime.now() + timedelta(days=30)).date(),
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b": None,  # Handled separately
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b": None,  # Date formats
        r"\b(\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b": None
    }
    
    # Workspace/project indicators
    WORKSPACE_INDICATORS = {
        "work": ["office", "meeting", "client", "project", "deadline", "presentation", "report"],
        "personal": ["home", "family", "personal", "doctor", "shopping", "errands"],
        "development": ["code", "bug", "feature", "deploy", "test", "review", "pr", "commit"]
    }
    
    def __init__(self):
        self.ai_service = get_ai_service()
    
    def extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from text using keywords"""
        text_lower = text.lower()
        
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return priority
        
        return None
    
    def extract_due_date(self, text: str) -> Optional[datetime]:
        """Extract due date from natural language"""
        text_lower = text.lower()
        
        # Check for relative dates
        for pattern, date_func in self.DATE_PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                if date_func:
                    return date_func()
                else:
                    # Try to parse the matched text
                    try:
                        return date_parser.parse(match.group(1), fuzzy=True).date()
                    except:
                        continue
        
        # Check for time expressions like "in 3 days", "in 2 weeks"
        time_match = re.search(r"in (\d+) (day|week|month)s?", text_lower)
        if time_match:
            amount = int(time_match.group(1))
            unit = time_match.group(2)
            
            if unit == "day":
                return (datetime.now() + timedelta(days=amount)).date()
            elif unit == "week":
                return (datetime.now() + timedelta(weeks=amount)).date()
            elif unit == "month":
                return (datetime.now() + timedelta(days=amount * 30)).date()
        
        return None
    
    def suggest_workspace(self, text: str, available_workspaces: List[str]) -> Optional[str]:
        """Suggest best matching workspace based on text content"""
        text_lower = text.lower()
        
        # First check if any workspace name is mentioned directly
        for workspace in available_workspaces:
            if workspace.lower() in text_lower:
                return workspace
        
        # Then check indicators
        scores = {}
        for category, indicators in self.WORKSPACE_INDICATORS.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                scores[category] = score
        
        # Find best matching workspace
        if scores:
            best_category = max(scores, key=scores.get)
            
            # Try to match category with workspace names
            for workspace in available_workspaces:
                if best_category.lower() in workspace.lower():
                    return workspace
        
        return None
    
    def extract_subtasks(self, text: str) -> List[str]:
        """Extract potential subtasks from text"""
        subtasks = []
        
        # Look for numbered lists
        numbered_pattern = r"\d+[.)\s]+([^\n]+)"
        for match in re.finditer(numbered_pattern, text):
            subtasks.append(match.group(1).strip())
        
        # Look for bullet points
        bullet_pattern = r"[-*•]\s+([^\n]+)"
        for match in re.finditer(bullet_pattern, text):
            subtasks.append(match.group(1).strip())
        
        # Look for "and" separated items (if no other subtasks found)
        if not subtasks and " and " in text.lower():
            # Simple split on "and" - could be improved
            parts = re.split(r"\s+and\s+", text, flags=re.IGNORECASE)
            if len(parts) > 1 and len(parts) <= 5:  # Reasonable number of parts
                subtasks = [part.strip() for part in parts]
        
        return subtasks
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from text"""
        mentions = re.findall(r"@(\w+)", text)
        return list(set(mentions))  # Remove duplicates
    
    def extract_tags(self, text: str) -> List[str]:
        """Extract #tags from text"""
        tags = re.findall(r"#(\w+)", text)
        return list(set(tags))
    
    async def parse_task(
        self,
        natural_text: str,
        workspaces: List[Dict[str, str]],
        lists: List[Dict[str, str]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Parse natural language task into structured format
        Returns parsed task data with AI enhancement
        """
        
        # First, try AI parsing
        try:
            ai_analysis = await self.ai_service.parse_natural_task(
                natural_text,
                workspaces,
                lists,
                user_id
            )
            
            # Use AI results as base
            parsed = {
                "title": ai_analysis.suggested_title or natural_text[:100],
                "description": natural_text if len(natural_text) > 100 else None,
                "workspace": ai_analysis.suggested_workspace,
                "list": ai_analysis.suggested_list,
                "priority": ai_analysis.suggested_priority,
                "due_date": ai_analysis.suggested_due_date,
                "confidence": ai_analysis.confidence,
                "ai_reasoning": ai_analysis.reasoning
            }
            
            # Add extracted entities if available
            if ai_analysis.extracted_entities:
                parsed["entities"] = ai_analysis.extracted_entities
            
        except Exception as e:
            logger.warning(f"AI parsing failed, using fallback: {str(e)}")
            
            # Fallback to rule-based parsing
            parsed = {
                "title": natural_text[:100],  # First 100 chars as title
                "description": natural_text if len(natural_text) > 100 else None,
                "workspace": None,
                "list": None,
                "priority": None,
                "due_date": None,
                "confidence": 0.5,
                "ai_reasoning": "Using rule-based parsing"
            }
        
        # Enhance with rule-based extraction
        # This can override or complement AI results
        
        # Extract priority if not set by AI
        if not parsed["priority"]:
            parsed["priority"] = self.extract_priority(natural_text) or "medium"
        
        # Extract due date if not set by AI
        if not parsed["due_date"]:
            due_date = self.extract_due_date(natural_text)
            if due_date:
                parsed["due_date"] = due_date.isoformat()
        
        # Suggest workspace if not set by AI
        if not parsed["workspace"] and workspaces:
            workspace_names = [ws["name"] for ws in workspaces]
            suggested = self.suggest_workspace(natural_text, workspace_names)
            if suggested:
                parsed["workspace"] = suggested
            elif workspace_names:
                parsed["workspace"] = workspace_names[0]  # Default to first
        
        # Extract additional metadata
        parsed["subtasks"] = self.extract_subtasks(natural_text)
        parsed["mentions"] = self.extract_mentions(natural_text)
        parsed["tags"] = self.extract_tags(natural_text)
        
        # Clean up the title (remove dates, tags, mentions if they're at the end)
        if parsed.get("title"):
            title = parsed["title"]
            # Remove trailing date patterns
            title = re.sub(r"\s+(today|tomorrow|next \w+|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})$", "", title, flags=re.IGNORECASE)
            # Remove trailing tags and mentions
            title = re.sub(r"\s+[@#]\w+\s*$", "", title)
            parsed["title"] = title.strip()
        
        return parsed
    
    def generate_task_summary(self, parsed_task: Dict[str, Any]) -> str:
        """Generate a human-readable summary of the parsed task"""
        parts = [f"Task: {parsed_task['title']}"]
        
        if parsed_task.get('workspace'):
            parts.append(f"Workspace: {parsed_task['workspace']}")
        
        if parsed_task.get('list'):
            parts.append(f"List: {parsed_task['list']}")
        
        if parsed_task.get('priority') and parsed_task['priority'] != 'medium':
            parts.append(f"Priority: {parsed_task['priority']}")
        
        if parsed_task.get('due_date'):
            parts.append(f"Due: {parsed_task['due_date']}")
        
        if parsed_task.get('subtasks'):
            parts.append(f"Subtasks: {len(parsed_task['subtasks'])}")
        
        if parsed_task.get('mentions'):
            parts.append(f"Mentions: {', '.join(parsed_task['mentions'])}")
        
        return " | ".join(parts)