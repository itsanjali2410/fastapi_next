from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from src.app.routes.auth import router as auth_router
from src.app.routes.org_routes import router as org_router
from src.app.routes.users_routes import router as users_router
from src.app.routes.chat_routes import router as chat_router
from src.app.routes.task_routes import router as task_router
from src.app.routes.invite_routes import router as invite_router
from src.app.routes.messages_routes import router as messages_router
from src.app.routes.group_chat_routes import router as group_chat_router
from src.app.routes.user_status_routes import router as user_status_router
from src.app.routes.upload_routes import router as upload_router

from src.app.db.mongo import connect_to_mongo, close_mongo_connection

# ---------------- APP ----------------

app = FastAPI(
    title="ChatApp API",
    version="1.0.0"
)

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DATABASE ----------------

app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# ---------------- ROUTES ----------------

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(org_router, prefix="/org", tags=["organization"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(group_chat_router, prefix="/chat/groups", tags=["group-chat"])
app.include_router(task_router, prefix="/tasks", tags=["tasks"])
app.include_router(invite_router, prefix="/invites", tags=["invites"])
app.include_router(messages_router, prefix="/messages", tags=["messages"])
app.include_router(user_status_router, prefix="/users/status", tags=["user-status"])
app.include_router(upload_router, prefix="/upload", tags=["upload"])
# ---------------- STATIC FILES ----------------

if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ---------------- ROOT ----------------

@app.get("/")
async def root():
    return {"message": "ChatApp backend is live 🚀"}
