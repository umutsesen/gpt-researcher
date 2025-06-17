from fastapi import WebSocket
from typing import Any
import os

from gpt_researcher import GPTResearcher


class BasicReport:
    def __init__(
        self,
        query: str,
        query_domains: list,
        report_type: str,
        report_source: str,
        source_urls,
        document_urls,
        tone: Any,
        config_path: str,
        websocket: WebSocket,
        headers=None,
        mcp_configs=None,
        mcp_strategy=None,        report_format: str = None,  # Added
        total_words: int = None,    # Added
        language: str = None,       # Added
        doc_path: str = None,       # Added
    ):
        self.query = query
        self.query_domains = query_domains
        self.report_type = report_type
        self.report_source = report_source
        self.source_urls = source_urls
        self.document_urls = document_urls
        self.tone = tone
        self.config_path = config_path
        self.websocket = websocket
        self.headers = headers or {}

        # Debug logging for language parameter
        if language:
            print(f"[DEBUG] BasicReport received language parameter: {language}")
        if doc_path:
            print(f"[DEBUG] BasicReport received doc_path parameter: {doc_path}")

        # Initialize researcher with optional MCP parameters
        gpt_researcher_params = {
            "query": self.query,
            "query_domains": self.query_domains,
            "report_type": self.report_type,
            "report_source": self.report_source,
            "source_urls": self.source_urls,
            "document_urls": self.document_urls,
            "tone": self.tone,
            "config_path": self.config_path,
            "websocket": self.websocket,
            "headers": self.headers,
            "report_format": report_format,  # Added
            "total_words": total_words,      # Added
            "language": language,            # Added
        }
        
        # Override doc_path in config if provided
        if doc_path:
            gpt_researcher_params["config_path"] = self._create_temp_config(doc_path)
        
        # Add MCP parameters if provided
        if mcp_configs is not None:
            gpt_researcher_params["mcp_configs"] = mcp_configs
        if mcp_strategy is not None:
            gpt_researcher_params["mcp_strategy"] = mcp_strategy
            
        self.gpt_researcher = GPTResearcher(**gpt_researcher_params)

    def _create_temp_config(self, doc_path: str) -> str:
        """Create a temporary config with custom DOC_PATH"""
        import json
        import tempfile
        from gpt_researcher.config.variables.default import DEFAULT_CONFIG
        
        # Create a copy of default config
        temp_config = DEFAULT_CONFIG.copy()
        temp_config["DOC_PATH"] = doc_path
        
        # Create temporary config file
        temp_config_fd, temp_config_path = tempfile.mkstemp(suffix='.json', prefix='gpt_researcher_config_')
        try:
            with os.fdopen(temp_config_fd, 'w') as f:
                json.dump(temp_config, f, indent=2)
            return temp_config_path
        except:
            os.close(temp_config_fd)
            raise

    async def run(self):
        """Run the research process"""
        await self.gpt_researcher.conduct_research()
        return await self.gpt_researcher.write_report()
