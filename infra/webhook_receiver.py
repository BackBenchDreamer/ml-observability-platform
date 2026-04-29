from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="Alert Webhook Receiver")


@app.post("/alert")
async def receive_alert(request: Request):
    try:
        payload = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {error}")

    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        print(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "alertname": labels.get("alertname"),
                "severity": labels.get("severity"),
                "status": alert.get("status"),
                "summary": annotations.get("summary"),
                "description": annotations.get("description"),
                "startsAt": alert.get("startsAt"),
            }
        )

    return {"status": "success", "message": "Alert received"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "webhook-receiver"}


@app.get("/")
async def root():
    return {
        "service": "Alert Webhook Receiver",
        "version": "1.0.0",
        "endpoints": {"alert": "/alert (POST)", "health": "/health (GET)"},
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
