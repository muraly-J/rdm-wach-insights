"""
Vercel Serverless Function for WACH Insight Backend

This file converts Vercel's Lambda event format to ASGI (FastAPI) and back.
It uses a custom wrapper to bridge Vercel's event structure with FastAPI.

For production deployment on Vercel, this handler forwards all /api/* requests
to the FastAPI application in backend/main.py.
"""

import os
import sys

# Ensure backend is on the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.main import app
from backend.config import load_env_files

# Initialize config (load env files)
load_env_files()


def handler(event, context):
    """
    Vercel Lambda handler - converts incoming event to ASGI and returns response.
    
    This is a bridge between Vercel's Lambda event format and FastAPI's ASGI app.
    """
    try:
        # Get the base path from Vercel headers or default to empty
        multi_value_headers = event.get("multiValueHeaders", {})
        host = multi_value_headers.get("host", [""])[0] if multi_value_headers else ""
        path = event.get("path", "")
        
        # Extract method
        http_method = event.get("httpMethod", event.get("method", "GET"))
        
        # Get query string parameters
        query_string_parameters = event.get("queryStringParameters", {}) or {}
        
        # Get headers
        headers = event.get("headers", {}) or {}
        if multi_value_headers:
            # Merge multiValueHeaders into headers if present
            for key, values in multi_value_headers.items():
                if key not in headers:
                    headers[key] = ",".join(values) if isinstance(values, list) else values
        
        # Get body
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)
        
        if is_base64 and body:
            import base64
            try:
                body = base64.b64decode(body).decode("utf-8")
            except Exception:
                pass
        
        # Create ASGI scope
        scope = {
            "type": "http",
            "method": http_method,
            "path": path,
            "query_string": (
                "&".join(f"{k}={v}" for k, v in query_string_parameters.items())
                if query_string_parameters
                else b""
            ).encode("utf-8") if query_string_parameters else b"",
            "headers": [(k.encode("utf-8"), v.encode("utf-8")) for k, v in headers.items()],
            "server": (host.split(":")[0], int(host.split(":")[1]) if ":" in host else 80),
            "scheme": "https" if headers.get("x-forwarded-proto", "").startswith("https") else "http",
            "root_path": "",
            "asgi": {"version": "3.0"},
        }
        
        # Collect response
        response = {
            "statusCode": 200,
            "headers": {},
            "body": "",
            "isBase64Encoded": False,
        }
        
        response_received = asyncio_run(_send_request(app, scope, body, response))
        
        return response_received
        
    except Exception as e:
        import traceback
        error_body = {
            "error": str(e),
            "detail": traceback.format_exc(),
        }
        import json
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(error_body),
            "isBase64Encoded": False,
        }


import asyncio


def asyncio_run(coro):
    """Helper to run async code in Vercel's event loop context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def _send_request(app, scope, body, response):
    """Send request to FastAPI app and collect response."""
    receive = _create_receive(body)
    send = _create_send(response, scope)
    
    try:
        await app(scope, receive, send)
    except Exception as e:
        # If send raised an error (like connection closed), we may not have a response yet
        if response["statusCode"] == 200:
            import json
            response["statusCode"] = 500
            response["body"] = json.dumps({"error": str(e)})
    
    return response


async def _create_receive(body):
    """Create ASGI receive callable."""
    if body:
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = b""
    
    received = False
    
    async def receive():
        nonlocal received
        if not received:
            received = True
            return {
                "type": "http.request",
                "body": body_bytes,
                "more_body": False,
            }
        return {
            "type": "http.request",
            "body": b"",
            "more_body": False,
        }
    
    return receive


async def _create_send(response, scope):
    """Create ASGI send callable that populates the response dict."""
    
    async def send(message):
        if message["type"] == "http.response.start":
            response["statusCode"] = message.get("status", 200)
            response["headers"] = {}
            for header, value in message.get("headers", []):
                decoded_header = header.decode("utf-8").lower()
                decoded_value = value.decode("utf-8")
                response["headers"][decoded_header] = decoded_value
                
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            response["body"] += body
    
    return send
