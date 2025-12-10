from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.app.models.message import SendMessageRequest
from src.app.core.config import settings
# Imports the router aggregator we defined earlier
from src.app.routes.auth import router as auth_router
from src.app.routes.org_routes import router as org_router
from src.app.routes.users_routes import router as users_router
from src.app.routes.chat_routes import router as chat_router
from src.app.routes.task_routes import router as task_router
from src.app.routes.invite_routes import router as invite_router
from src.app.routes.messages_routes import router as messages_router
from src.app.routes.group_chat_routes import router as group_chat_router
from src.app.routes.user_status_routes import router as user_status_router
# Imports MongoDB connection handlers
from src.app.db.mongo import connect_to_mongo, close_mongo_connection
# Import Socket.io manager
from src.app.socketio_manager import socketio_manager

# API prefix
API_V1_STR = "/api/v1"

app = FastAPI(
    title="SaaS Organization Platform API",
    version="1.0.0",
    # Set the root path of the API for documentation
    openapi_url=f"{API_V1_STR}/openapi.json"
)

# --- 1. CORS Middleware Setup ---
# This allows your Next.js frontend (e.g., running on localhost:3000) to communicate 
# with your FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"], # Allow your frontend and potentially other origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Database Event Handlers ---
# Ensures the MongoDB connection is established before the app starts 
# and properly closed when the app shuts down.
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)

# --- 3. Route Inclusion ---
# Includes all the endpoints defined in auth.py, admin.py, etc., 
# under the /api/v1 prefix.
app.include_router(auth_router, prefix=f"{API_V1_STR}/auth", tags=["auth"])
app.include_router(org_router, prefix=f"{API_V1_STR}/org", tags=["organization"])
app.include_router(users_router, prefix=f"{API_V1_STR}/users", tags=["users"])
app.include_router(chat_router, prefix=f"{API_V1_STR}/chat", tags=["chat"])
app.include_router(group_chat_router, prefix=f"{API_V1_STR}/chat/groups", tags=["group-chat"])
app.include_router(task_router, prefix=f"{API_V1_STR}/tasks", tags=["tasks"])
app.include_router(invite_router, prefix=f"{API_V1_STR}/invites", tags=["invites"])
app.include_router(messages_router, prefix=f"{API_V1_STR}/messages", tags=["messages"])
app.include_router(user_status_router, prefix=f"{API_V1_STR}/users/status", tags=["user-status"])
@app.post("/test/send")
async def test_send(request: SendMessageRequest):
    message = {
        "sender_id": request.sender_id,
        "receiver_id": request.receiver_id,
        "text": request.text
    }
    await socketio_manager.emit_new_message(request.receiver_id, message)
    return {"status": "sent"}


# --- 4. Root Endpoint (Health Check) ---
@app.get("/")
async def root():
    return {"message": "SaaS Backend is operational!"}

# --- 5. Socket.io Initialization ---
# Initialize Socket.io for real-time messaging after all routes are registered
socketio_manager.initialize(app)

# Replace app with Socket.io wrapped app so Socket.io routes work
# This allows Socket.io to handle /socket.io routes and FastAPI to handle others
app = socketio_manager.socketio_app