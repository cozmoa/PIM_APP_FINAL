from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
import json
from datetime import datetime

# Import your database system
from backend.main import NoteDatabaseSystem

app = FastAPI(title="Notes & Todos API", version="1.0.0")
security = HTTPBearer()

# Initialize system
notes_system = NoteDatabaseSystem()

# ---------- Helpers ----------
def get_session_id(username: str) -> Optional[str]:
    for sid, uname in notes_system.active_sessions.items():
        if uname == username:
            return sid
    return None

def create_response(success: bool, data: Any = None, message: str = ""):
    return {"success": success, "data": data, "message": message}

# ---------- Models ----------
class UserRegister(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        if len(v.strip()) < 3 or len(v.strip()) > 50:
            raise ValueError("Username must be 3-50 characters")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v):
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class NoteCreate(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_must_be_valid(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        if len(v.strip()) > 200:
            raise ValueError("Title must be less than 200 characters")
        return v.strip()

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    @field_validator("title")
    @classmethod
    def title_must_be_valid(cls, v):
        if v is not None:
            if not v.strip() or len(v.strip()) > 200:
                raise ValueError("Title must be 1–200 characters")
            return v.strip()
        return v

class TodoCreate(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[str] = None
    priority: str = "normal"
    tags: Optional[List[str]] = []
    note_title: Optional[str] = None

class TagsAdd(BaseModel):
    tags: List[str]

# ---------- Auth ----------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    session_id = credentials.credentials
    username = notes_system._get_username_from_session(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    return username

# ---------- Endpoints ----------
@app.get("/test")
async def test_endpoint():
    return create_response(True, {"timestamp": datetime.now().isoformat()}, "API working")

@app.get("/health")
async def health_check():
    return create_response(True, {"status": "healthy"}, "Server is healthy")

@app.post("/register")
async def register_user(user: UserRegister):
    result = json.loads(notes_system.register_user(user.username, user.password))
    return create_response(result["success"], {"username": user.username} if result["success"] else None, result["message"])

@app.post("/login")
async def login_user(user: UserLogin):
    result = json.loads(notes_system.login_user(user.username, user.password))
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return create_response(True, {"session_id": result["session_id"], "username": user.username}, result["message"])

@app.post("/logout")
async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    session_id = credentials.credentials
    result = json.loads(notes_system.logout_user(session_id))
    return create_response(result["success"], None, result["message"])

# ---------- Notes ----------
@app.get("/notes")
async def list_notes(limit: int = 50, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.list_notes(session_id, limit))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"notes": result["notes"], "count": result["count"]}, f"Found {result['count']} notes")

@app.post("/notes")
async def create_note(note: NoteCreate, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.create_note(session_id, note.title, note.content))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"note_id": result.get("note_id"), "title": note.title}, result["message"])

@app.get("/notes/{title}")
async def get_note(title: str, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.get_note(session_id, title))
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return create_response(True, {"note": result["note"]}, "Note retrieved")

@app.put("/notes/{title}")
async def update_note(title: str, note_update: NoteUpdate, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)

    # Content update
    result = json.loads(notes_system.edit_note(session_id, title, note_update.content))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Title update if new title provided
    if note_update.title and note_update.title != title:
        rename_result = json.loads(notes_system.update_note_title(session_id, title, note_update.title))
        if not rename_result["success"]:
            raise HTTPException(status_code=400, detail=rename_result["message"])
        return create_response(True, {"title": note_update.title}, "Note updated and renamed")

    return create_response(True, {"title": title}, "Note updated")

@app.delete("/notes/{title}")
async def delete_note(title: str, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.delete_note(session_id, title))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"deleted_title": title}, result["message"])

@app.get("/notes/search/{query}")
async def search_notes(query: str, username: str = Depends(get_current_user)):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Empty search query")
    session_id = get_session_id(username)
    result = json.loads(notes_system.search_notes(session_id, query))
    return create_response(True, {"results": result["results"], "count": result["count"]}, f"Found {result['count']} results")

@app.post("/notes/{title}/tags")
async def add_tags_to_note(title: str, tags: TagsAdd, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.add_tags(session_id, title, tags.tags))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"title": title, "tags": result["tags"]}, "Tags added")

# ---------- Stats ----------
@app.get("/stats")
async def get_user_stats(username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.get_stats(session_id))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"stats": result["stats"]}, "Statistics retrieved")

# ---------- Todos ----------
@app.get("/todos")
async def get_todos(username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.list_todos(session_id))
    return create_response(True, {"todos": result["results"]}, f"Found {len(result['results'])} todos")

@app.post("/todos")
async def create_new_todo(todo: TodoCreate, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.create_todo(
        session_id, todo.title, todo.description, todo.due_date, todo.priority, todo.tags, todo.note_title
    ))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"todo_id": result.get("id")}, result["message"])

@app.delete("/todos/{todo_id}")
async def delete_todo_item(todo_id: int, username: str = Depends(get_current_user)):
    session_id = get_session_id(username)
    result = json.loads(notes_system.delete_todo(session_id, todo_id))
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"deleted_todo_id": todo_id}, result["message"])

# ---------- Root ----------
@app.get("/")
async def root():
    return create_response(True, {"version": "1.0.0", "docs": "/docs"}, "Welcome to Notes & Todos API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)