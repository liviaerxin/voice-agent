import uvicorn
from app.api import app

if __name__ == "__main__":
    # Run directly with `python main.py` instead of using uvicorn CLI
    uvicorn.run(app, host="0.0.0.0", port=8000)
