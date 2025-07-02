# AI Features Documentation

**Created**: 2025-01-02 07:00:00 PST  
**Last Modified**: 2025-01-02 07:00:00 PST

## Overview

Smart-ToDo integrates AI capabilities using Groq's fast inference API with the Llama 3.1 8B model. The AI features enhance task management through semantic understanding, natural language processing, and intelligent suggestions.

## AI-Powered Features

### 1. Semantic Duplicate Detection

Traditional duplicate detection uses text similarity algorithms. The AI enhancement adds:

- **Semantic Understanding**: Detects paraphrased or conceptually similar tasks
- **Context Awareness**: Understands task intent beyond literal text matching
- **Smart Suggestions**: Recommends whether to create, update, or merge tasks

**Example**:
- Existing: "Call dentist for appointment"
- New: "Schedule dental checkup"
- AI: "85% semantic match. Suggest updating existing task with specific action."

### 2. Natural Language Task Creation

The `smart_create_task` MCP tool parses natural language into structured tasks:

**Input**: "Meeting with John next Tuesday at 2pm to discuss Q4 budget report"

**AI Extracts**:
- Title: "Meeting with John - Q4 Budget"
- Workspace: Work (based on "meeting", "budget")
- Due Date: Next Tuesday 2:00 PM
- Priority: High (budget-related)
- Entities: {people: ["John"], projects: ["Q4 budget"]}

### 3. Intelligent Task Routing

AI automatically determines the best workspace and list for new tasks based on:
- Content analysis
- Keyword matching
- User patterns
- Workspace/list naming conventions

### 4. Subtask Extraction

Automatically identifies and creates subtasks from natural language:

**Input**: "Prepare presentation - research data, create slides, practice speech"

**Creates**:
- Main task: "Prepare presentation"
- Subtasks:
  - "Research data"
  - "Create slides"
  - "Practice speech"

## Technical Implementation

### AI Service Architecture

```python
# Core components
- AIService: Main service class for Groq API integration
- SmartTaskParser: Natural language parsing engine
- AIEnhancedDuplicateDetector: Semantic duplicate detection
- UsageTracker: Cost control and monitoring
```

### Cost Optimization

**Monthly Cost Estimation** (10 users, 20 tasks/day each):
- Token usage: ~600,000 tokens/month
- Cost: ~$0.06/month (Llama 3.1 8B at $0.10/million tokens)
- Well under the $2.00 budget target

**Optimization Strategies**:
1. **Response Caching**: 24-hour Redis cache for similar queries
2. **Token Limits**: 500 tokens max per request
3. **Usage Tracking**: Per-user and daily limits
4. **Batch Processing**: Multiple tasks in single API call
5. **Graceful Fallback**: Traditional algorithms when limits reached

### Configuration

Add to `.env`:

```env
# AI Integration (Groq)
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.1-8b-instant
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=500
AI_CACHE_TTL=86400
AI_DAILY_TOKEN_LIMIT=20000
AI_USER_MONTHLY_TOKEN_LIMIT=50000
ENABLE_AI_DUPLICATE_DETECTION=true
```

## API Integration

### Duplicate Detection Response

```json
{
  "detail": "Potential duplicate tasks found",
  "duplicates": [...],
  "similarity_scores": {...},
  "ai_analysis": {
    "suggested_action": "update_existing",
    "reasoning": "Tasks are semantically identical",
    "confidence": 0.92,
    "suggested_title": "Call dentist to schedule appointment"
  }
}
```

### Smart Task Creation (MCP)

```python
# Natural language input
"Fix critical login bug in production by end of day"

# AI-parsed output
{
  "title": "Fix critical login bug",
  "workspace": "Development",
  "list": "Bugs",
  "priority": "urgent",
  "due_date": "2025-01-02T17:00:00",
  "tags": ["production", "critical"],
  "confidence": 0.95
}
```

## Usage Examples

### 1. Via MCP Client

```bash
# Traditional task creation
create_task title="Doctor appointment" list_name="Personal"

# Smart task creation with AI
smart_create_task natural_text="Schedule annual checkup with Dr. Smith next month, need blood work done"
```

### 2. Via API

```bash
# Create task with AI duplicate detection
curl -X POST http://localhost:5482/api/v1/lists/{list_id}/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Review quarterly report",
    "description": "Analyze Q4 financial data"
  }'

# Response includes AI suggestions if duplicates found
```

### 3. Handling AI Suggestions

```python
# Frontend can show AI reasoning
if response.ai_analysis:
    if response.ai_analysis.suggested_action == "update_existing":
        # Show UI: "AI suggests updating existing task because..."
        # Offer options: Update, Create New, Cancel
```

## Monitoring and Limits

### Usage Statistics Endpoint

```bash
GET /api/v1/ai/usage
{
  "daily_usage": 15234,
  "daily_limit": 20000,
  "user_monthly_usage": 45678,
  "user_monthly_limit": 50000,
  "ai_enabled": true
}
```

### Graceful Degradation

When limits are reached:
1. AI features automatically disable
2. Falls back to traditional algorithms
3. Users are notified in response
4. Service remains fully functional

## Future Enhancements

1. **Task Prioritization**: AI-suggested priority based on content and deadlines
2. **Smart Scheduling**: Optimal time slot suggestions based on calendar
3. **Progress Tracking**: Analyze task completion patterns
4. **Team Insights**: Workload distribution recommendations
5. **Bulk Operations**: Process multiple tasks in natural language

## Security Considerations

1. **API Key Protection**: Groq API key stored securely in environment
2. **Input Sanitization**: All natural language input sanitized
3. **PII Handling**: Personal information not sent to AI without consent
4. **Audit Trail**: All AI decisions logged for compliance

## Troubleshooting

### Common Issues

1. **"AI analysis unavailable"**
   - Check GROQ_API_KEY is set correctly
   - Verify usage limits not exceeded
   - Check Redis connection for caching

2. **Poor AI suggestions**
   - Adjust AI_TEMPERATURE (lower = more consistent)
   - Provide more context in task descriptions
   - Check workspace/list names are descriptive

3. **High latency**
   - Enable caching (AI_CACHE_TTL)
   - Reduce AI_MAX_TOKENS if appropriate
   - Check Redis performance

### Debug Mode

Enable detailed AI logging:
```env
LOG_LEVEL=DEBUG
AI_DEBUG_MODE=true
```