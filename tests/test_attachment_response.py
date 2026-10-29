import asyncio
import io
import pytest
from starlette.requests import ClientDisconnect
from app.api.routes.attachments import PrivateFileResponse


def test_disconnect_before_stream_iteration_closes_private_file():
    stream = io.BytesIO(b"private bytes")
    response = PrivateFileResponse(stream, iter([b"unused"]), media_type="text/plain")
    async def send(_message): raise OSError("Disconnected before body iteration")
    async def receive(): return {"type": "http.disconnect"}
    with pytest.raises(ClientDisconnect):
        asyncio.run(response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send))
    assert stream.closed
