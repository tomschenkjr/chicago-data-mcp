#!/usr/bin/env python
"""
HTTP server wrapper for Chicago Open Data MCP.
Exposes the MCP server over HTTP with FastAPI + SSE transport.
"""
import os
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from mcp.server.sse import SseServerTransport
from server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Chicago Open Data MCP", lifespan=lifespan)
sse_transport = SseServerTransport("/messages/")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chicago-data-mcp"}


@app.get("/sse")
async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp._mcp_server.run(
            streams[0], streams[1],
            mcp._mcp_server.create_initialization_options()
        )


@app.post("/messages/")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


def run():
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run()
