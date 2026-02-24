"""
Vercel Serverless Function for WACH Insight Backend
"""

def handler(event, context):
    """Lambda-style handler as fallback."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status":"ok","from":"vercel"}'
    }
