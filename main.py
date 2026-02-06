import os

import uvicorn


def run() -> None:
    port = int(os.getenv("PORT", "8000"))
    reload_flag = os.getenv("UVICORN_RELOAD", "false").lower() in {"1", "true", "yes", "on"}
    uvicorn.run(app="app.app:app", host="0.0.0.0", port=port, reload=reload_flag)


if __name__ == "__main__":
    run()
