from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Uptime Monitor API"}

@app.get("/health")
async def get_health():
    return {"status": "ok"}