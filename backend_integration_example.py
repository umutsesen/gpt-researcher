"""
Example: Backend Integration with GPT-Researcher
This shows how your backend can use the streamlined approach
to handle files and make research requests.
"""

import os
import tempfile
import uuid
import time
import shutil
import requests
import asyncio
from pathlib import Path
from typing import List, Optional

class GPTResearcherClient:
    """
    Client for integrating with GPT-Researcher from your backend
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def create_temp_folder(self, user_id: Optional[str] = None) -> str:
        """
        Create a temporary folder for user documents
        """
        # You can either call the API or create directly
        # Option 1: Call API
        response = requests.get(
            f"{self.base_url}/create_temp_folder/",
            params={"user_id": user_id} if user_id else {}
        )
        if response.status_code == 200:
            return response.json()["temp_doc_path"]
        
        # Option 2: Create directly (if on same server)
        return self._create_temp_doc_path_directly(user_id)
    
    def _create_temp_doc_path_directly(self, user_id: Optional[str] = None) -> str:
        """
        Create temp folder directly (when backend and GPT-Researcher are on same server)
        """
        request_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        if user_id:
            folder_name = f"docs_{user_id}_{timestamp}_{request_id}"
        else:
            folder_name = f"docs_{timestamp}_{request_id}"
        
        temp_base = os.path.join(tempfile.gettempdir(), "gpt_researcher_docs")
        os.makedirs(temp_base, exist_ok=True)
        
        temp_doc_path = os.path.join(temp_base, folder_name)
        os.makedirs(temp_doc_path, exist_ok=True)
        
        return temp_doc_path
    
    def save_files_to_folder(self, files: List[dict], folder_path: str) -> List[str]:
        """
        Save user files to the temporary folder
        
        Args:
            files: List of file objects with 'content' and 'filename'
            folder_path: Path where to save files
            
        Returns:
            List of saved file paths
        """
        saved_files = []
        
        for file_data in files:
            file_path = os.path.join(folder_path, file_data['filename'])
            
            # Save file content
            if isinstance(file_data['content'], bytes):
                with open(file_path, 'wb') as f:
                    f.write(file_data['content'])
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_data['content'])
            
            saved_files.append(file_path)
        
        return saved_files
    
    async def research_with_documents(
        self,
        task: str,
        files: List[dict],
        user_id: Optional[str] = None,
        report_format: str = "markdown",
        total_words: int = 2000,
        language: str = "en",
        report_type: str = "research_report",
        report_source: str = "local"
    ) -> dict:
        """
        Complete workflow: save files and run research
        
        Args:
            task: Research task description
            files: List of file objects
            user_id: User identifier
            report_format: Output format (pdf, docx, markdown)
            total_words: Target word count
            language: Report language
            report_type: Type of report
            report_source: Source type (local, web, hybrid)
            
        Returns:
            Research results
        """
        temp_doc_path = None
        
        try:
            # 1. Create temporary folder
            temp_doc_path = self.create_temp_folder(user_id)
            
            # 2. Save files to folder
            saved_files = self.save_files_to_folder(files, temp_doc_path)
            print(f"Saved {len(saved_files)} files to {temp_doc_path}")
            
            # 3. Make research request
            research_request = {
                "task": task,
                "report_type": report_type,
                "report_source": report_source,
                "tone": "Objective",
                "headers": {},
                "repo_name": "",
                "branch_name": "",
                "generate_in_background": False,  # Wait for result
                "report_format": report_format,
                "total_words": total_words,
                "language": language,
                "user_id": user_id,
                "doc_path": temp_doc_path
            }
            
            # 4. Send request to GPT-Researcher
            response = requests.post(
                f"{self.base_url}/research/",
                json=research_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Research completed: {result.get('research_id')}")
                return result
            else:
                raise Exception(f"Research failed: {response.text}")
                
        except Exception as e:
            # Cleanup on error
            if temp_doc_path and os.path.exists(temp_doc_path):
                shutil.rmtree(temp_doc_path)
            raise e
    
    def cleanup_folder(self, folder_path: str) -> bool:
        """
        Manually cleanup a temporary folder
        """
        try:
            if os.path.exists(folder_path) and "gpt_researcher_docs" in folder_path:
                shutil.rmtree(folder_path)
                return True
        except Exception as e:
            print(f"Cleanup error: {e}")
        return False


# Example usage in your backend
async def main():
    """
    Example of how to use this in your backend
    """
    client = GPTResearcherClient()
    
    # Simulate files from user upload
    example_files = [
        {
            "filename": "market_report.txt",
            "content": "This is a market analysis document with key insights..."
        },
        {
            "filename": "financial_data.csv",
            "content": "Date,Revenue,Profit\n2023-01,100000,20000\n2023-02,120000,25000"
        }
    ]
    
    try:
        # Run research with documents
        result = await client.research_with_documents(
            task="Analyze the market trends and financial performance",
            files=example_files,
            user_id="user_123",
            report_format="pdf",
            total_words=1500,
            language="en"
        )
        
        print("Research Results:")
        print(f"Research ID: {result['research_id']}")
        print(f"Report: {result['report'][:200]}...")  # First 200 chars
        print(f"PDF Path: {result.get('pdf_path')}")
        print(f"DOCX Path: {result.get('docx_path')}")
        
    except Exception as e:
        print(f"Error: {e}")


# Flask/FastAPI integration example
def create_flask_endpoint():
    """
    Example Flask endpoint that uses GPTResearcherClient
    """
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    client = GPTResearcherClient()
    
    @app.route('/research', methods=['POST'])
    def research_endpoint():
        try:
            # Get data from request
            data = request.get_json()
            files = request.files.getlist('files')
            
            # Convert uploaded files to our format
            file_objects = []
            for file in files:
                file_objects.append({
                    'filename': file.filename,
                    'content': file.read()
                })
            
            # Run research
            result = asyncio.run(client.research_with_documents(
                task=data['task'],
                files=file_objects,
                user_id=data.get('user_id'),
                report_format=data.get('report_format', 'markdown'),
                total_words=data.get('total_words', 2000),
                language=data.get('language', 'en')
            ))
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return app


def create_fastapi_endpoint():
    """
    Example FastAPI endpoint that uses GPTResearcherClient
    """
    from fastapi import FastAPI, UploadFile, File, Form
    from typing import List
    
    app = FastAPI()
    client = GPTResearcherClient()
    
    @app.post("/research")
    async def research_endpoint(
        task: str = Form(...),
        user_id: str = Form(None),
        report_format: str = Form("markdown"),
        total_words: int = Form(2000),
        language: str = Form("en"),
        files: List[UploadFile] = File(...)
    ):
        try:
            # Convert uploaded files
            file_objects = []
            for file in files:
                content = await file.read()
                file_objects.append({
                    'filename': file.filename,
                    'content': content
                })
            
            # Run research
            result = await client.research_with_documents(
                task=task,
                files=file_objects,
                user_id=user_id,
                report_format=report_format,
                total_words=total_words,
                language=language
            )
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    return app


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
