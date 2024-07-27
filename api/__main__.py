import uvicorn

from api.main import app
from api.settings.settings import settings

uvicorn.run(app, host=settings.server.host, port=settings.server.port)