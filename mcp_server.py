"""
Lab 3.1 — solution/mcp_server.py
=================================
Reference implementation of the MCP server.

Exposes one tool (read_file) and one resource (project directory listing).
The read_file tool is the shared file layer used by both the Coder and QA
agents in the Week 3 pipeline — neither agent imports file I/O directly;
both call it through this server.
"""
