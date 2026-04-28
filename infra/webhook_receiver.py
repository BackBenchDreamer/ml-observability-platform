"""
Webhook Receiver for Alertmanager
Phase 5: Alerting Infrastructure

Receives and logs alerts from Alertmanager.
"""

from fastapi import FastAPI, Request
from datetime import datetime
import json
import uvicorn

app = FastAPI(title="Alert Webhook Receiver")


@app.post("/alert")
async def receive_alert(request: Request):
    """
    Receive alerts from Alertmanager and log them.
    
    Expected payload structure:
    {
        "alerts": [
            {
                "labels": {
                    "alertname": "...",
                    "severity": "..."
                },
                "annotations": {
                    "summary": "...",
                    "description": "..."
                },
                "status": "firing" or "resolved",
                "startsAt": "...",
                "endsAt": "..."
            }
        ]
    }
    """
    try:
        payload = await request.json()
        
        # Process each alert in the payload
        for alert in payload.get("alerts", []):
            alert_name = alert.get("labels", {}).get("alertname", "Unknown")
            severity = alert.get("labels", {}).get("severity", "unknown")
            status = alert.get("status", "unknown")
            summary = alert.get("annotations", {}).get("summary", "No summary")
            description = alert.get("annotations", {}).get("description", "No description")
            starts_at = alert.get("startsAt", "")
            
            # Format timestamp
            timestamp = datetime.utcnow().isoformat()
            
            # Log the alert with formatted output
            print("=" * 80)
            print(f"🚨 ALERT RECEIVED")
            print(f"Timestamp: {timestamp}")
            print(f"Alert Name: {alert_name}")
            print(f"Severity: {severity.upper()}")
            print(f"Status: {status.upper()}")
            print(f"Summary: {summary}")
            print(f"Description: {description}")
            print(f"Started At: {starts_at}")
            print("=" * 80)
            print()
        
        return {"status": "success", "message": "Alert received"}
    
    except Exception as e:
        print(f"❌ Error processing alert: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint for container monitoring."""
    return {"status": "healthy", "service": "webhook-receiver"}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Alert Webhook Receiver",
        "version": "1.0.0",
        "endpoints": {
            "alert": "/alert (POST)",
            "health": "/health (GET)"
        }
    }


if __name__ == "__main__":
    print("🚀 Starting Alert Webhook Receiver on port 5000...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )

# Made with Bob
