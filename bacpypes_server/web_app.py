# web_app.py
import uvicorn
from fastapi import FastAPI
from routes import register_routes

api_app = FastAPI(
    title="BACnet REST API",
    description="A BACnet Rest API server!!",
    version="1.0",
)

register_routes(api_app)


async def start_api_server():
    config = uvicorn.Config(api_app, host="127.0.0.1", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
