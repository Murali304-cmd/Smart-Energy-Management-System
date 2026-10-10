import os
import sys
import traceback

if __name__ == "__main__":
    try:
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        print(f"==> [SEMS Production] Starting Uvicorn on 0.0.0.0:{port}...")
        uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"FATAL: Application failed to start: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
