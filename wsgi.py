from tracker_service.api import app
from a2wsgi import ASGIMiddleware

# Wrap the FastAPI (ASGI) app to work with WSGI workers like gthread
application = ASGIMiddleware(app)
