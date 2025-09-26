# backend/fast_api.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import json
import os
from .main import NoteDatabaseSystem  # package-relative

app = FastAPI(title="Notes & Todos API", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # simple CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
notes_system = NoteDatabaseSystem()

def get_session_id(username: str) -> Optional[str]:
    for sid, uname in notes_system.active_sessions.items():
        if uname == username:
            return sid
    return None

def create_response(success: bool, data: any = None, message: str = ""):
    return {"success": success, "data": data, "message": message}

# ---------- models ----------
class UserRegister(BaseModel):
    username: str
    password: str
    @field_validator("username")
    @classmethod
    def vu(cls, v): 
        v = v.strip()
        if not v or len(v) < 3 or len(v) > 50: 
            raise ValueError("Username must be 3-50 chars")
        return v
    @field_validator("password")
    @classmethod
    def vp(cls, v):
        if not v or len(v) < 6: 
            raise ValueError("Password must be at least 6 chars")
        return v

class UserLogin(BaseModel):
    username: str
    password: str
    @field_validator("username")
    @classmethod
    def vu(cls, v): 
        v = v.strip()
        if not v: raise ValueError("Username cannot be empty")
        return v
    @field_validator("password")
    @classmethod
    def vp(cls, v):
        if not v: raise ValueError("Password cannot be empty")
        return v

class NoteCreate(BaseModel):
    title: str
    content: str
    folder_id: Optional[int] = None
    @field_validator("title")
    @classmethod
    def vt(cls, v):
        v = v.strip()
        if not v or len(v) > 200: 
            raise ValueError("Title must be 1-200 chars")
        return v
    @field_validator("content")
    @classmethod
    def vc(cls, v):
        v = v.strip()
        if not v: raise ValueError("Content cannot be empty")
        return v

class NoteUpdate(BaseModel):
    content: str
    @field_validator("content")
    @classmethod
    def vc(cls, v):
        v = v.strip()
        if not v: raise ValueError("Content cannot be empty")
        return v

class TodoCreate(BaseModel):
    title: str
    description: str = ""
    due_date: Optional[str] = None
    priority: str = "normal"
    tags: Optional[List[str]] = []
    note_title: Optional[str] = None
    @field_validator("title")
    @classmethod
    def vt(cls, v):
        v = v.strip()
        if not v or len(v) > 200: 
            raise ValueError("Title must be 1-200 chars")
        return v
    @field_validator("priority")
    @classmethod
    def vp(cls, v):
        if v not in {"low", "normal", "high"}: 
            raise ValueError("Priority must be low, normal, or high")
        return v
    @field_validator("description")
    @classmethod
    def vd(cls, v): return v.strip() if v else ""

class TagsAdd(BaseModel):
    tags: List[str]
    @field_validator("tags")
    @classmethod
    def vt(cls, v):
        if not v: raise ValueError("Tags list cannot be empty")
        cleaned = [t.strip() for t in v if t.strip()]
        if not cleaned: raise ValueError("No valid tags provided")
        return cleaned

# folders
class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    @field_validator("name")
    @classmethod
    def vn(cls, v):
        v = v.strip()
        if not v: raise ValueError("Folder name is required")
        return v

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None

class AssignNoteFolder(BaseModel):
    title: str
    folder_id: Optional[int] = None
    @field_validator("title")
    @classmethod
    def vt(cls, v):
        v = v.strip()
        if not v: raise ValueError("Title is required")
        return v

# ---------- auth helper ----------
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    session_id = credentials.credentials
    username = notes_system._get_username_from_session(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid session")
    return username

# ---------- basic endpoints ----------
@app.get("/test")
async def test_endpoint():
    return create_response(True, {"timestamp": datetime.now().isoformat(), "version": "1.0.0"}, "API is working!")

@app.get("/health")
async def health_check():
    return create_response(True, {"status": "healthy"}, "Notes & Todos API is running")

# ---------- auth ----------
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

# ---------- notes ----------
@app.get("/notes")
async def list_notes(limit: int = 50, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.list_notes(sid, limit))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"notes": result["notes"], "count": result["count"]}, f"Found {result['count']} notes")

@app.post("/notes")
async def create_note(note: NoteCreate, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.create_note(sid, note.title, note.content, note.folder_id))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"note_id": result.get("note_id"), "title": note.title}, result["message"])

@app.get("/notes/{title}")
async def get_note(title: str, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.get_note(sid, title))
    if not result["success"]: raise HTTPException(status_code=404, detail=result["message"])
    return create_response(True, {"note": result["note"]}, "Note retrieved successfully")

@app.put("/notes/{title}")
async def update_note(title: str, note_update: NoteUpdate, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.edit_note(sid, title, note_update.content))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"title": title}, result["message"])

@app.delete("/notes/{title}")
async def delete_note(title: str, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.delete_note(sid, title))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"deleted_title": title}, result["message"])

@app.get("/notes/search/{query}")
async def search_notes(query: str, username: str = Depends(get_current_user)):
    if not query.strip(): raise HTTPException(status_code=400, detail="Search query cannot be empty")
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.search_notes(sid, query))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"results": result["results"], "count": result["count"], "query": query}, f"Found {result['count']} results")

@app.post("/notes/{title}/tags")
async def add_tags_to_note(title: str, tags: TagsAdd, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.add_tags(sid, title, tags.tags))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"title": title, "all_tags": result["tags"]}, f"Tags added to '{title}'")

# move note into/out of folder
@app.post("/folders/assign-note")
async def assign_note_folder(payload: AssignNoteFolder, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.set_note_folder(sid, payload.title, payload.folder_id))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, None, result["message"])

# ---------- todos ----------
@app.get("/todos")
async def get_todos(status: Optional[str] = None, tag: Optional[str] = None,
                    priority: Optional[str] = None, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.list_todos(sid, status, tag, priority))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    todos = result["results"]
    return create_response(True, {"todos": todos, "count": len(todos), "filters": {"status": status, "tag": tag, "priority": priority}}, f"Found {len(todos)} todos")

@app.post("/todos")
async def create_new_todo(todo: TodoCreate, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.create_todo(sid, todo.title, todo.description, todo.due_date, todo.priority, todo.tags, todo.note_title))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"todo_id": result.get("id"), "title": todo.title}, result["message"])

@app.patch("/todos/{todo_id}/toggle")
async def toggle_todo_completion(todo_id: int, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.toggle_todo(sid, todo_id))
    if not result["success"]: raise HTTPException(status_code=404, detail=result["message"])
    return create_response(True, {"todo_id": todo_id}, result["message"])

@app.delete("/todos/{todo_id}")
async def delete_todo_item(todo_id: int, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.delete_todo(sid, todo_id))
    if not result["success"]: raise HTTPException(status_code=404, detail=result["message"])
    return create_response(True, {"deleted_todo_id": todo_id}, result["message"])

# ---------- folders ----------
@app.get("/folders")
async def list_folders(username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.list_folders(sid))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, result["folders"], "Folders fetched")

@app.post("/folders")
async def create_folder(folder: FolderCreate, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.create_folder(sid, folder.name, folder.parent_id))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, {"id": result["id"]}, result["message"])

@app.patch("/folders/{folder_id}")
async def update_folder(folder_id: int, upd: FolderUpdate, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    if upd.name is not None:
        res = json.loads(notes_system.rename_folder(sid, folder_id, upd.name))
        if not res["success"]: raise HTTPException(status_code=404, detail=res["message"])
    if upd.parent_id is not None:
        res2 = json.loads(notes_system.move_folder(sid, folder_id, upd.parent_id))
        if not res2["success"]: raise HTTPException(status_code=400, detail=res2["message"])
    return create_response(True, {"id": folder_id}, "Folder updated")

@app.delete("/folders/{folder_id}")
async def remove_folder(folder_id: int, username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.delete_folder(sid, folder_id))
    if not result["success"]: raise HTTPException(status_code=404, detail=result["message"])
    return create_response(True, {"deleted_folder_id": folder_id}, result["message"])

# ---------- stats ----------
@app.get("/stats")
async def get_user_stats(username: str = Depends(get_current_user)):
    sid = get_session_id(username)
    if not sid: raise HTTPException(status_code=401, detail="Session not found")
    result = json.loads(notes_system.get_stats(sid))
    if not result["success"]: raise HTTPException(status_code=400, detail=result["message"])
    return create_response(True, result["data"], "Statistics retrieved successfully")

# ---------- root redirect ----------
@app.get("/")
async def root():
    index = os.path.join(FRONTEND_DIR, "loading.html")
    if os.path.exists(index):
        return RedirectResponse(url="/frontend/loading.html")
    return create_response(
        True,
        {
            "version": "1.0.0",
            "endpoints": {
                "auth": ["/register", "/login", "/logout"],
                "notes": ["/notes", "/notes/{title}", "/notes/search/{query}"],
                "todos": ["/todos", "/todos/{todo_id}"],
                "folders": ["/folders", "/folders/{id}", "/folders/assign-note"],
                "other": ["/stats", "/health", "/test"],
            },
            "docs": "/docs",
        },
        "Welcome to Notes & Todos API",
    )

if __name__ == "__main__":
    import uvicorn
    print("Starting Notes & Todos API Server...")
    print("Visit http://localhost:8000/docs for interactive API documentation")
    uvicorn.run(app, host="0.0.0.0", port=8000)
