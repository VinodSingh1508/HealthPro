from app.config import GEMINI_API_KEY, HOST, PORT

# GEMINI_API_KEY is loaded from project .env
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY is empty")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
