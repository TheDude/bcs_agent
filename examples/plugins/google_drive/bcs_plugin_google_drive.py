"""Example bcs-agent plugin: langchain google drive integration

An example plugin using a prebuilt tool from the langchain community.
In this case, it exposes the GoogleDriveLoader tool.
"""
from __future__ import annotations

import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_googledrive.tools.google_drive.tool import GoogleDriveSearchTool
from langchain_googledrive.utilities.google_drive import GoogleDriveAPIWrapper
from pydantic_ai.ext.langchain import tool_from_langchain

from pydantic_ai import FunctionToolset, ModelRetry

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("google_auth_oauthlib").setLevel(logging.DEBUG)

toolset = FunctionToolset()

lc_drive_tool = GoogleDriveSearchTool(
    api_wrapper=GoogleDriveAPIWrapper(
        mode="documents-markdown",
        folder_id="1yCbi691pLpKqMEhZpGb4XWfq_6Ud4ksE",     # or a specific folder ID
        num_results=5,
        template="gdrive-query-in-folder",  # searches file bodies, not just names
    )
)

def get_toolset() -> FunctionToolset:
    """Plugin entry point: hand the harness this plugin's toolset."""
    return toolset

drive_search = tool_from_langchain(lc_drive_tool)
toolset.add_tool(drive_search)