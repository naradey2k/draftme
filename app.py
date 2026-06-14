import uvicorn

from config import get_settings
from ui.server import create_app

settings = get_settings()
app = create_app(settings)


if __name__ == "__main__":
    uvicorn.run("app:app", reload=False)

