"""
Lab 3.1 — solution/mcp_server.py
=================================
Reference implementation of the MCP server.

Exposes one tool (read_file) and one resource (project directory listing).
The read_file tool is the shared file layer used by both the Coder and QA
agents in the Week 3 pipeline — neither agent imports file I/O directly;
both call it through this server.
"""

import asyncio
import pathlib
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions

# ---------------------------------------------------------------------------
# Constants -- do not change this block
# ---------------------------------------------------------------------------
import os as _os
_here = pathlib.Path(__file__).resolve().parent
_candidate = _here / "project_files"
if not _candidate.exists():
    _candidate = _here.parent / "project_files"
PROJECT_DIR = pathlib.Path(_os.environ.get("LAB31_PROJECT_DIR", str(_candidate)))

# ---------------------------------------------------------------------------
# TODO 1 -- Server instance
# ---------------------------------------------------------------------------
server = Server("lab3-mcp-server")


# ---------------------------------------------------------------------------
# TODO 2 -- list_tools handler
# ---------------------------------------------------------------------------
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Advertise the read_file tool."""
    return [
        types.Tool(
            name="read_file",
            description="Reads a file from the project_files directory",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )
    ]


# ---------------------------------------------------------------------------
# TODO 3 -- call_tool handler
# ---------------------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Dispatch a tool request to the relevant implementation."""
    if name != "read_file":
        return [
            types.TextContent(
                type="text",
                text=f"ERROR: unknown tool {name}",
            )
        ]

    path = arguments.get("path")

    if not isinstance(path, str):
        return [
            types.TextContent(
                type="text",
                text="ERROR: 'path' must be a string",
            )
        ]

    return await _read_file(path)


# ---------------------------------------------------------------------------
# TODO 4 -- list_resources handler
# ---------------------------------------------------------------------------
@server.list_resources()
async def list_resources() -> list[types.Resource]:
    """Advertise the project directory listing resource."""
    return [
        types.Resource(
            uri="file://project/listing",
            name="Project Directory Listing",
            mimeType="text/plain",
            description="Newline-separated filenames in project_files/",
        )
    ]


# ---------------------------------------------------------------------------
# TODO 5 -- read_resource handler
# ---------------------------------------------------------------------------
@server.read_resource()
async def read_resource(uri: types.AnyUrl) -> str:
    """Return the directory listing for the known project resource."""
    if str(uri) != "file://project/listing":
        return f"ERROR: unknown resource {uri}"

    try:
        return "\n".join(sorted(file.name for file in PROJECT_DIR.iterdir()))
    except Exception as exc:
        return f"ERROR: unable to list project directory: {exc}"


# ---------------------------------------------------------------------------
# TODO 6 -- _read_file helper
# ---------------------------------------------------------------------------
async def _read_file(path: str) -> list[types.TextContent]:
    """Read a file from PROJECT_DIR with path traversal protection.

    - Reject paths with ".." or starting with "/".
    - Resolve and verify path stays inside PROJECT_DIR.
    - Return TextContent with file contents on success.
    - Return TextContent starting "ERROR:" on any error. Never raise.
    """
    try:
        requested_path = pathlib.Path(path)

        if path.startswith("/") or ".." in requested_path.parts:
            return [
                types.TextContent(
                    type="text",
                    text="ERROR: path traversal denied",
                )
            ]

        project_root = PROJECT_DIR.resolve()
        target_path = (project_root / requested_path).resolve()

        try:
            target_path.relative_to(project_root)
        except ValueError:
            return [
                types.TextContent(
                    type="text",
                    text="ERROR: path traversal denied",
                )
            ]

        if not target_path.exists() or not target_path.is_file():
            return [
                types.TextContent(
                    type="text",
                    text=f"ERROR: file not found: {path}",
                )
            ]

        return [
            types.TextContent(
                type="text",
                text=target_path.read_text(encoding="utf-8"),
            )
        ]

    except Exception as exc:
        return [
            types.TextContent(
                type="text",
                text=f"ERROR: unable to read file: {exc}",
            )
        ]


# ---------------------------------------------------------------------------
# Entry point -- do not modify
# ---------------------------------------------------------------------------
async def main() -> None:
    options = server.create_initialization_options()
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    asyncio.run(main())
