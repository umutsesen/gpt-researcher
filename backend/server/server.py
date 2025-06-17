import json
import os
from typing import Dict, List
import time
import tempfile
import uuid
import shutil
import threading
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile, BackgroundTasks, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.server.websocket_manager import WebSocketManager
from backend.server.server_utils import (
    get_config_dict, sanitize_filename,
    update_environment_variables, handle_file_upload, handle_file_deletion,
    execute_multi_agents, handle_websocket_communication, cleanup_temp_folders
)

from backend.server.websocket_manager import run_agent
from backend.utils import write_md_to_word, write_md_to_pdf
from gpt_researcher.utils.logging_config import setup_research_logging
from gpt_researcher.utils.enum import Tone
from backend.chat.chat import ChatAgentWithMemory

import logging

# Get logger instance
logger = logging.getLogger(__name__)

# Don't override parent logger settings
logger.propagate = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Only log to console
    ]
)

# Global cleanup thread
_cleanup_thread = None

def start_cleanup_service():
    """Start the background cleanup service"""
    global _cleanup_thread
    if _cleanup_thread is None or not _cleanup_thread.is_alive():
        _cleanup_thread = threading.Thread(target=cleanup_temp_folders, daemon=True)
        _cleanup_thread.start()
        logger.info("Started background temp folder cleanup service")

def create_temp_doc_path(user_id: str = None) -> str:
    """
    Create a temporary directory for document storage
    
    Args:
        user_id: Optional user identifier for better tracking
        
    Returns:
        str: Path to the temporary directory
    """
    # Create a unique identifier
    request_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    if user_id:
        folder_name = f"docs_{user_id}_{timestamp}_{request_id}"
    else:
        folder_name = f"docs_{timestamp}_{request_id}"
    
    # Create temp directory
    temp_base = os.path.join(tempfile.gettempdir(), "gpt_researcher_docs")
    os.makedirs(temp_base, exist_ok=True)
    
    temp_doc_path = os.path.join(temp_base, folder_name)
    os.makedirs(temp_doc_path, exist_ok=True)
    
    logger.info(f"Created temporary doc path: {temp_doc_path}")
    return temp_doc_path

def cleanup_temp_doc_path(doc_path: str) -> bool:
    """
    Clean up a temporary document path
    
    Args:
        doc_path: Path to clean up
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if os.path.exists(doc_path) and "gpt_researcher_docs" in doc_path:
            shutil.rmtree(doc_path)
            logger.info(f"Cleaned up temporary doc path: {doc_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to cleanup temp doc path {doc_path}: {e}")
    return False

# Models


class ResearchRequest(BaseModel):
    task: str
    report_type: str
    report_source: str
    tone: str
    headers: dict | None = None
    repo_name: str
    branch_name: str
    generate_in_background: bool = True
    report_format: str | None = None  # Added
    total_words: int | None = None  # Added
    language: str | None = None  # Added
    user_id: str | None = None  # Added for user identification
    doc_path: str | None = None  # Added for document folder path


class ConfigRequest(BaseModel):
    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: str
    LANGCHAIN_TRACING_V2: str
    LANGCHAIN_API_KEY: str
    OPENAI_API_KEY: str
    DOC_PATH: str
    RETRIEVER: str
    GOOGLE_API_KEY: str = ''
    GOOGLE_CX_KEY: str = ''
    BING_API_KEY: str = ''
    SEARCHAPI_API_KEY: str = ''
    SERPAPI_API_KEY: str = ''
    SERPER_API_KEY: str = ''
    SEARX_URL: str = ''
    XAI_API_KEY: str
    DEEPSEEK_API_KEY: str


# App initialization
app = FastAPI()

# Static files and templates
app.mount("/site", StaticFiles(directory="./frontend"), name="site")
app.mount("/static", StaticFiles(directory="./frontend/static"), name="static")
templates = Jinja2Templates(directory="./frontend")

# WebSocket manager
manager = WebSocketManager()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
DOC_PATH = os.getenv("DOC_PATH", "./my-docs")

# Startup event


@app.on_event("startup")
def startup_event():
    os.makedirs("outputs", exist_ok=True)
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
    # Start the cleanup service for temporary folders
    start_cleanup_service()
    logger.info("GPT-Researcher server started with temp folder management")
    

# Routes


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "report": None})


@app.get("/create_temp_folder/")
async def create_temp_folder_endpoint(user_id: str = None):
    """
    API endpoint to create a temporary folder for your backend to use
    Returns the folder path where you can save files before calling research
    """
    try:
        temp_doc_path = create_temp_doc_path(user_id)
        return {
            "temp_doc_path": temp_doc_path,
            "message": "Temporary folder created successfully",
            "expires_in": "2 hours"
        }
    except Exception as e:
        logger.error(f"Error creating temp folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/{research_id}")
async def read_report(request: Request, research_id: str):
    docx_path = os.path.join('outputs', f"{research_id}.docx")
    if not os.path.exists(docx_path):
        return {"message": "Report not found."}
    return FileResponse(docx_path)


async def write_report_with_files(research_request: ResearchRequest, research_id: str = None, temp_doc_path: str = None):
    """
    Generate report with optional files in temporary folder
    """
    try:
        # Use temp_doc_path if provided, otherwise use default behavior
        doc_path_to_use = temp_doc_path if temp_doc_path else None
        
        report_information = await run_agent(
            task=research_request.task,
            report_type=research_request.report_type,
            report_source=research_request.report_source,
            source_urls=[],
            document_urls=[],
            tone=Tone[research_request.tone],
            websocket=None,
            stream_output=None,
            headers=research_request.headers,
            query_domains=[],
            config_path="",
            return_researcher=True,
            report_format=research_request.report_format,
            total_words=research_request.total_words,
            language=research_request.language,
            doc_path=doc_path_to_use
        )

        docx_path = await write_md_to_word(report_information[0], research_id)
        pdf_path = await write_md_to_pdf(report_information[0], research_id)
        
        if research_request.report_type != "multi_agents":
            report, researcher = report_information
            response = {
                "research_id": research_id,
                "research_information": {
                    "source_urls": researcher.get_source_urls(),
                    "research_costs": researcher.get_costs(),
                    "visited_urls": list(researcher.visited_urls),
                    "research_images": researcher.get_research_images(),
                },
                "report": report,
                "docx_path": docx_path,
                "pdf_path": pdf_path,
                "temp_doc_path": temp_doc_path
            }
        else:
            response = { 
                "research_id": research_id, 
                "report": "", 
                "docx_path": docx_path, 
                "pdf_path": pdf_path,
                "temp_doc_path": temp_doc_path
            }

        return response
    
    finally:
        # Schedule cleanup of temporary folder if we created one
        if temp_doc_path:
            # Cleanup after 5 minutes
            threading.Timer(300, cleanup_temp_doc_path, args=[temp_doc_path]).start()

async def write_report(research_request: ResearchRequest, research_id: str = None):
    """
    Original write_report function for backward compatibility
    """
    return await write_report_with_files(research_request, research_id, None)

# Removed handle_document_uploads function
# Backend handles file saving directly

# Removed redundant research_with_documents endpoint
# Use the main research endpoint with doc_path parameter instead

# Removed redundant write_report_with_temp_path function
# Use write_report_with_files which handles both cases

@app.post("/research/")
async def research(
    research_request: ResearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Main research endpoint - accepts doc_path directly in the request
    Your backend can save files to a folder and pass the path here
    """
    try:
        research_id = sanitize_filename(f"task_{int(time.time())}_{research_request.task}")
        
        if research_request.generate_in_background:
            background_tasks.add_task(
                write_report_with_files, 
                research_request=research_request, 
                research_id=research_id,
                temp_doc_path=research_request.doc_path
            )
            return {
                "message": "Your report is being generated in the background. Please check back later.",
                "research_id": research_id,
                "doc_path": research_request.doc_path
            }
        else:
            response = await write_report_with_files(research_request, research_id, research_request.doc_path)
            return response
            
    except Exception as e:
        logger.error(f"Error in research endpoint: {e}")
        # Cleanup on error if we have a temp doc path
        if research_request.doc_path and "gpt_researcher_docs" in research_request.doc_path:
            cleanup_temp_doc_path(research_request.doc_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/report_with_files/")
async def generate_report_with_files(
    task: str = Form(...),
    report_type: str = Form(...),
    report_source: str = Form("local"),
    tone: str = Form("Objective"),
    report_format: str = Form(None),
    total_words: int = Form(None),
    language: str = Form(None),
    user_id: str = Form(None),
    generate_in_background: bool = Form(True),
    files: List[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Generate research report with uploaded files
    Files are automatically saved to a temporary folder and processed
    """
    research_id = sanitize_filename(f"task_{int(time.time())}_{task}")
    temp_doc_path = None
    
    try:
        # Create temporary folder if files are provided
        if files and any(f.filename for f in files):
            temp_doc_path = create_temp_doc_path(user_id)
            
            # Save uploaded files to temp folder
            for file in files:
                if file.filename:
                    file_path = os.path.join(temp_doc_path, file.filename)
                    with open(file_path, "wb") as buffer:
                        content = await file.read()
                        buffer.write(content)
                    logger.info(f"Saved file {file.filename} to {file_path}")
        
        # Create research request
        research_request = ResearchRequest(
            task=task,
            report_type=report_type,
            report_source=report_source,
            tone=tone,
            headers={},
            repo_name="",
            branch_name="",
            generate_in_background=generate_in_background,
            report_format=report_format,
            total_words=total_words,
            language=language,
            user_id=user_id
        )
        
        if generate_in_background:
            background_tasks.add_task(
                write_report_with_files, 
                research_request=research_request, 
                research_id=research_id,
                temp_doc_path=temp_doc_path
            )
            return {
                "message": "Your report is being generated in the background. Please check back later.",
                "research_id": research_id,
                "temp_doc_path": temp_doc_path
            }
        else:
            response = await write_report_with_files(research_request, research_id, temp_doc_path)
            return response
            
    except Exception as e:
        # Cleanup on error
        if temp_doc_path:
            cleanup_temp_doc_path(temp_doc_path)
        logger.error(f"Error in generate_report_with_files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/")
async def list_files():
    if not os.path.exists(DOC_PATH):
        os.makedirs(DOC_PATH, exist_ok=True)
    files = os.listdir(DOC_PATH)
    print(f"Files in {DOC_PATH}: {files}")
    return {"files": files}


@app.post("/api/multi_agents")
async def run_multi_agents():
    return await execute_multi_agents(manager)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    return await handle_file_upload(file, DOC_PATH)


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    return await handle_file_deletion(filename, DOC_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await handle_websocket_communication(websocket, manager)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

# Removed redundant upload_documents endpoint
# Backend should save files directly and pass doc_path to research requests

@app.post("/cleanup_temp_folder/")
async def cleanup_temp_folder(doc_path: str):
    """
    Manually cleanup a temporary folder
    """
    try:
        success = cleanup_temp_doc_path(doc_path)
        if success:
            return {"message": f"Successfully cleaned up {doc_path}"}
        else:
            return {"error": f"Failed to cleanup {doc_path}"}
    except Exception as e:
        return {"error": f"Error cleaning up folder: {str(e)}"}
