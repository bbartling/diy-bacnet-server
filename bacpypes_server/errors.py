import fastapi_jsonrpc as jsonrpc
from fastapi_jsonrpc import BaseError
from pydantic import BaseModel


class DeviceNotFoundError(jsonrpc.BaseError):
    CODE = 1001
    MESSAGE = "BACnet device not found"

    class DataModel(BaseModel):
        instance: int
        detail: str


class WhoIsFailureError(BaseError):
    CODE = 1002
    MESSAGE = "Who-Is scan failed"

    class DataModel(BaseModel):
        detail: str
