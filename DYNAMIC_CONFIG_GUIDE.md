# Dynamic Configuration and File Handling Guide

This guide explains how to use GPT-Researcher with dynamic per-request configuration and safe file handling for multi-user environments.

## Overview

The system now supports:
- **Dynamic per-request configuration** (REPORT_FORMAT, TOTAL_WORDS, LANGUAGE, DOC_PATH)
- **Safe concurrent file handling** with isolated temporary folders
- **Automatic cleanup** of temporary resources
- **Backward compatibility** with existing code

## Key Features

### 1. Per-Request Configuration

You can now override these parameters per request:
- `report_format`: "pdf", "docx", "markdown", etc.
- `total_words`: Number of words for the report
- `language`: Language for the report (e.g., "en", "es", "fr")
- `doc_path`: Path to documents for local research

### 2. Safe File Handling

Each request gets its own isolated temporary folder:
- Files are automatically isolated per user/request
- Automatic cleanup after 5 minutes (configurable)
- Background cleanup service for old folders
- No file conflicts between concurrent users

## Usage Patterns

### Pattern 1: Backend Integration (Recommended)

Since your backend already handles file uploads, use this streamlined approach:

```python
# 1. Your backend receives files from users
# 2. Create a temp folder and save files
temp_doc_path = create_temp_doc_path(user_id="user123")
# Save your files to temp_doc_path

# 3. Make research request with the folder path
research_request = {
    "task": "Analyze the uploaded documents",
    "report_type": "research_report",
    "report_source": "local",
    "tone": "Objective",
    "report_format": "pdf",
    "total_words": 2000,
    "language": "en",
    "doc_path": temp_doc_path,
    "user_id": "user123"
}

# 4. Call GPT-Researcher API
response = await post("/research/", json=research_request)
```

### Pattern 2: WebSocket Integration

```javascript
// Send research request via WebSocket with custom config
const message = {
    task: "Research renewable energy",
    report_type: "research_report",
    report_source: "web",
    tone: "Objective",
    report_format: "markdown",
    total_words: 1500,
    language: "es",
    doc_path: "/path/to/documents"  // Optional for local research
};

websocket.send(JSON.stringify(message));
```

### Pattern 3: API with File Upload

```python
# If you need to upload files directly to GPT-Researcher
# (though backend integration is preferred)

# 1. Create temp folder
response = await get("/create_temp_folder/", params={"user_id": "user123"})
temp_doc_path = response["temp_doc_path"]

# 2. Save your files to temp_doc_path
# (your backend logic here)

# 3. Make research request
research_request = {
    "task": "Analyze documents",
    "doc_path": temp_doc_path,
    "report_format": "docx",
    "total_words": 3000
}
response = await post("/research/", json=research_request)
```

## API Endpoints

### Main Research Endpoint

**POST** `/research/`

```json
{
    "task": "Research task description",
    "report_type": "research_report",
    "report_source": "web|local|hybrid",
    "tone": "Objective|Formal|Analytical",
    "report_format": "pdf|docx|markdown",
    "total_words": 2000,
    "language": "en",
    "doc_path": "/path/to/documents",
    "user_id": "optional_user_id",
    "generate_in_background": true
}
```

### Helper Endpoints

**GET** `/create_temp_folder/`
- Creates a temporary folder for file storage
- Returns the folder path
- Optional `user_id` parameter for tracking

**POST** `/cleanup_temp_folder/`
- Manually cleanup a temporary folder
- Useful for immediate cleanup

## File Handling Best Practices

### 1. Temporary Folder Structure

```
/tmp/gpt_researcher_docs/
├── docs_user123_1674567890_uuid1/
│   ├── document1.pdf
│   └── document2.txt
├── docs_user456_1674567891_uuid2/
│   └── report.docx
└── docs_1674567892_uuid3/  # No user_id
    └── file.txt
```

### 2. Cleanup Strategies

**Automatic Cleanup:**
- Background service runs every hour
- Removes folders older than 2 hours
- Per-request cleanup after 5 minutes

**Manual Cleanup:**
```python
# In your backend, after processing
cleanup_temp_doc_path(temp_doc_path)
```

### 3. Error Handling

```python
try:
    # Create temp folder
    temp_doc_path = create_temp_doc_path(user_id)
    
    # Save files and process
    # ... your logic here ...
    
    # Make research request
    response = await research_with_files(...)
    
except Exception as e:
    # Cleanup on error
    if temp_doc_path:
        cleanup_temp_doc_path(temp_doc_path)
    raise e
```

## Configuration Override Examples

### Research in Spanish with Custom Word Count

```python
request = {
    "task": "Investigar energías renovables",
    "language": "es",
    "total_words": 1500,
    "report_format": "pdf"
}
```

### Local Document Research with Custom Format

```python
request = {
    "task": "Analyze uploaded financial reports",
    "report_source": "local",
    "doc_path": "/tmp/user_docs/session_123",
    "report_format": "docx",
    "total_words": 3000
}
```

### Hybrid Research (Web + Documents)

```python
request = {
    "task": "Market analysis using industry reports",
    "report_source": "hybrid",
    "doc_path": "/tmp/user_docs/market_reports",
    "total_words": 2500,
    "language": "en"
}
```

## Migration from Previous Versions

### Old Way (Global Config)
```python
# Had to modify environment variables
os.environ["REPORT_FORMAT"] = "pdf"
os.environ["TOTAL_WORDS"] = "2000"

# All requests used same config
result = await run_research(task)
```

### New Way (Per-Request Config)
```python
# Each request can have different config
request1 = {"task": "Task 1", "report_format": "pdf", "total_words": 2000}
request2 = {"task": "Task 2", "report_format": "docx", "total_words": 1500}

result1 = await research(request1)
result2 = await research(request2)  # Different config!
```

## Security Considerations

1. **File Isolation**: Each request gets its own folder
2. **Path Validation**: Temp paths are validated to prevent directory traversal
3. **Automatic Cleanup**: Prevents disk space issues
4. **User Tracking**: Optional user_id for audit trails

## Troubleshooting

### Common Issues

1. **Files not found**: Ensure doc_path is correctly set and files exist
2. **Permission errors**: Check temp directory permissions
3. **Cleanup issues**: Verify background cleanup service is running

### Debug Logging

The system includes extensive logging:
```python
# Enable debug logging
import logging
logging.getLogger('gpt_researcher').setLevel(logging.DEBUG)
```

### Health Check

```python
# Check if cleanup service is running
GET /files/  # Should return file list
```

## Performance Considerations

1. **Concurrent Users**: Each gets isolated resources
2. **Memory Usage**: Files are processed individually
3. **Cleanup Frequency**: Configurable via environment variables
4. **Background Tasks**: Non-blocking research generation

This system is now ready for production use with multiple concurrent users, each having their own isolated document workspace and dynamic configuration options.
