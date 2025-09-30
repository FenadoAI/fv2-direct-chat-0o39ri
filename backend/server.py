"""FastAPI server exposing AI agent endpoints."""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from ai_agents.agents import AgentConfig, ChatAgent, SearchAgent


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
security = HTTPBearer()


# Auth Models
class UserSignup(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Chat Models
class ChatRoomCreate(BaseModel):
    pass


class ChatRoomResponse(BaseModel):
    id: str
    invite_token: str
    participants: List[str]
    created_at: datetime
    is_active: bool
    other_user: Optional[UserResponse] = None


class JoinChatRequest(BaseModel):
    invite_token: str


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    sender_username: str
    content: str
    created_at: datetime


class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusCheckCreate(BaseModel):
    client_name: str


class ChatRequest(BaseModel):
    message: str
    agent_type: str = "chat"
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    agent_type: str
    capabilities: List[str]
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResponse(BaseModel):
    success: bool
    query: str
    summary: str
    search_results: Optional[dict] = None
    sources_count: int
    error: Optional[str] = None


def _ensure_db(request: Request):
    try:
        return request.app.state.db
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=503, detail="Database not ready") from exc


def _get_agent_cache(request: Request) -> Dict[str, object]:
    if not hasattr(request.app.state, "agent_cache"):
        request.app.state.agent_cache = {}
    return request.app.state.agent_cache


async def _get_or_create_agent(request: Request, agent_type: str):
    cache = _get_agent_cache(request)
    if agent_type in cache:
        return cache[agent_type]

    config: AgentConfig = request.app.state.agent_config

    if agent_type == "search":
        cache[agent_type] = SearchAgent(config)
    elif agent_type == "chat":
        cache[agent_type] = ChatAgent(config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent type '{agent_type}'")

    return cache[agent_type]


# Auth utilities
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        db = _ensure_db(request)
        user = await db.users.find_one({"_id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT_DIR / ".env")

    mongo_url = os.getenv("MONGO_URL")
    db_name = os.getenv("DB_NAME")

    if not mongo_url or not db_name:
        missing = [name for name, value in {"MONGO_URL": mongo_url, "DB_NAME": db_name}.items() if not value]
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    client = AsyncIOMotorClient(mongo_url)

    try:
        app.state.mongo_client = client
        app.state.db = client[db_name]
        app.state.agent_config = AgentConfig()
        app.state.agent_cache = {}
        logger.info("AI Agents API starting up")
        yield
    finally:
        client.close()
        logger.info("AI Agents API shutdown complete")


app = FastAPI(
    title="AI Agents API",
    description="Minimal AI Agents API with LangGraph and MCP support",
    lifespan=lifespan,
)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate, request: Request):
    db = _ensure_db(request)
    status_obj = StatusCheck(**input.model_dump())
    await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks(request: Request):
    db = _ensure_db(request)
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(chat_request: ChatRequest, request: Request):
    try:
        agent = await _get_or_create_agent(request, chat_request.agent_type)
        response = await agent.execute(chat_request.message)

        return ChatResponse(
            success=response.success,
            response=response.content,
            agent_type=chat_request.agent_type,
            capabilities=agent.get_capabilities(),
            metadata=response.metadata,
            error=response.error,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error in chat endpoint")
        return ChatResponse(
            success=False,
            response="",
            agent_type=chat_request.agent_type,
            capabilities=[],
            error=str(exc),
        )


@api_router.post("/search", response_model=SearchResponse)
async def search_and_summarize(search_request: SearchRequest, request: Request):
    try:
        search_agent = await _get_or_create_agent(request, "search")
        search_prompt = (
            f"Search for information about: {search_request.query}. "
            "Provide a comprehensive summary with key findings."
        )
        result = await search_agent.execute(search_prompt, use_tools=True)

        if result.success:
            metadata = result.metadata or {}
            return SearchResponse(
                success=True,
                query=search_request.query,
                summary=result.content,
                search_results=metadata,
                sources_count=int(metadata.get("tool_run_count", metadata.get("tools_used", 0)) or 0),
            )

        return SearchResponse(
            success=False,
            query=search_request.query,
            summary="",
            sources_count=0,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error in search endpoint")
        return SearchResponse(
            success=False,
            query=search_request.query,
            summary="",
            sources_count=0,
            error=str(exc),
        )


@api_router.get("/agents/capabilities")
async def get_agent_capabilities(request: Request):
    try:
        search_agent = await _get_or_create_agent(request, "search")
        chat_agent = await _get_or_create_agent(request, "chat")

        return {
            "success": True,
            "capabilities": {
                "search_agent": search_agent.get_capabilities(),
                "chat_agent": chat_agent.get_capabilities(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Error getting capabilities")
        return {"success": False, "error": str(exc)}


# Auth endpoints
@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup, request: Request):
    db = _ensure_db(request)

    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"email": user_data.email}, {"username": user_data.username}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email or username already exists")

    # Create user
    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(user_data.password)

    user = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password": hashed_pw,
        "created_at": datetime.now(timezone.utc),
    }

    await db.users.insert_one(user)

    # Create token
    access_token = create_access_token({"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(id=user_id, username=user_data.username, email=user_data.email),
    )


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin, request: Request):
    db = _ensure_db(request)

    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": user["_id"]})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(id=user["_id"], username=user["username"], email=user["email"]),
    )


# Chat endpoints
@api_router.post("/chats/create", response_model=ChatRoomResponse)
async def create_chat_room(chat_data: ChatRoomCreate, request: Request, current_user: dict = Depends(get_current_user)):
    db = _ensure_db(request)

    chat_id = str(uuid.uuid4())
    invite_token = str(uuid.uuid4())

    chat_room = {
        "_id": chat_id,
        "invite_token": invite_token,
        "participants": [current_user["_id"]],
        "created_by": current_user["_id"],
        "created_at": datetime.now(timezone.utc),
        "is_active": True,
    }

    await db.chat_rooms.insert_one(chat_room)

    return ChatRoomResponse(
        id=chat_id,
        invite_token=invite_token,
        participants=[current_user["_id"]],
        created_at=chat_room["created_at"],
        is_active=True,
    )


@api_router.post("/chats/join/{invite_token}", response_model=ChatRoomResponse)
async def join_chat_room(invite_token: str, request: Request, current_user: dict = Depends(get_current_user)):
    db = _ensure_db(request)

    chat_room = await db.chat_rooms.find_one({"invite_token": invite_token})
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    if len(chat_room["participants"]) >= 2:
        if current_user["_id"] in chat_room["participants"]:
            # User already in chat
            other_user_id = [p for p in chat_room["participants"] if p != current_user["_id"]][0]
            other_user = await db.users.find_one({"_id": other_user_id})
            other_user_data = (
                UserResponse(id=other_user["_id"], username=other_user["username"], email=other_user["email"])
                if other_user
                else None
            )

            return ChatRoomResponse(
                id=chat_room["_id"],
                invite_token=chat_room["invite_token"],
                participants=chat_room["participants"],
                created_at=chat_room["created_at"],
                is_active=chat_room["is_active"],
                other_user=other_user_data,
            )
        else:
            raise HTTPException(status_code=400, detail="Chat room is full")

    if current_user["_id"] in chat_room["participants"]:
        raise HTTPException(status_code=400, detail="You are already in this chat room")

    # Add user to chat
    await db.chat_rooms.update_one({"_id": chat_room["_id"]}, {"$push": {"participants": current_user["_id"]}})

    chat_room["participants"].append(current_user["_id"])

    # Get other user details
    other_user_id = [p for p in chat_room["participants"] if p != current_user["_id"]][0]
    other_user = await db.users.find_one({"_id": other_user_id})
    other_user_data = (
        UserResponse(id=other_user["_id"], username=other_user["username"], email=other_user["email"])
        if other_user
        else None
    )

    return ChatRoomResponse(
        id=chat_room["_id"],
        invite_token=chat_room["invite_token"],
        participants=chat_room["participants"],
        created_at=chat_room["created_at"],
        is_active=chat_room["is_active"],
        other_user=other_user_data,
    )


@api_router.get("/chats/my-chats", response_model=List[ChatRoomResponse])
async def get_my_chats(request: Request, current_user: dict = Depends(get_current_user)):
    db = _ensure_db(request)

    chat_rooms = await db.chat_rooms.find({"participants": current_user["_id"]}).to_list(1000)

    result = []
    for chat_room in chat_rooms:
        other_user_data = None
        if len(chat_room["participants"]) == 2:
            other_user_id = [p for p in chat_room["participants"] if p != current_user["_id"]][0]
            other_user = await db.users.find_one({"_id": other_user_id})
            if other_user:
                other_user_data = UserResponse(
                    id=other_user["_id"], username=other_user["username"], email=other_user["email"]
                )

        result.append(
            ChatRoomResponse(
                id=chat_room["_id"],
                invite_token=chat_room["invite_token"],
                participants=chat_room["participants"],
                created_at=chat_room["created_at"],
                is_active=chat_room["is_active"],
                other_user=other_user_data,
            )
        )

    return result


@api_router.post("/messages/{chat_id}", response_model=MessageResponse)
async def send_message(
    chat_id: str, message_data: MessageCreate, request: Request, current_user: dict = Depends(get_current_user)
):
    db = _ensure_db(request)

    # Verify user is in chat
    chat_room = await db.chat_rooms.find_one({"_id": chat_id})
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    if current_user["_id"] not in chat_room["participants"]:
        raise HTTPException(status_code=403, detail="You are not a participant in this chat")

    message_id = str(uuid.uuid4())
    message = {
        "_id": message_id,
        "chat_id": chat_id,
        "sender_id": current_user["_id"],
        "content": message_data.content,
        "created_at": datetime.now(timezone.utc),
    }

    await db.messages.insert_one(message)

    return MessageResponse(
        id=message_id,
        chat_id=chat_id,
        sender_id=current_user["_id"],
        sender_username=current_user["username"],
        content=message_data.content,
        created_at=message["created_at"],
    )


@api_router.get("/messages/{chat_id}", response_model=List[MessageResponse])
async def get_messages(
    chat_id: str, request: Request, current_user: dict = Depends(get_current_user), limit: int = 100, before: str = None
):
    db = _ensure_db(request)

    # Verify user is in chat
    chat_room = await db.chat_rooms.find_one({"_id": chat_id})
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    if current_user["_id"] not in chat_room["participants"]:
        raise HTTPException(status_code=403, detail="You are not a participant in this chat")

    # Build query
    query = {"chat_id": chat_id}
    if before:
        query["created_at"] = {"$lt": datetime.fromisoformat(before.replace("Z", "+00:00"))}

    messages = await db.messages.find(query).sort("created_at", -1).limit(limit).to_list(limit)

    # Get sender usernames
    result = []
    for msg in reversed(messages):
        sender = await db.users.find_one({"_id": msg["sender_id"]})
        result.append(
            MessageResponse(
                id=msg["_id"],
                chat_id=msg["chat_id"],
                sender_id=msg["sender_id"],
                sender_username=sender["username"] if sender else "Unknown",
                content=msg["content"],
                created_at=msg["created_at"],
            )
        )

    return result


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
