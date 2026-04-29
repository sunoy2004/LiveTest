import traceback
import sys

try:
    print("Importing app.db...")
    import app.db
    print("Importing app.models...")
    import app.models
    print("Importing app.services.dashboard_service...")
    from app.services import dashboard_service
    print("Importing app.routes.v1.dashboard...")
    from app.routes.v1 import dashboard
    print("SUCCESS")
except Exception:
    traceback.print_exc()
    sys.exit(1)
