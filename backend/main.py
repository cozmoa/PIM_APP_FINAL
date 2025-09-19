# backend/main.py
import json
import uuid
from typing import Optional, List, Dict, Any
from .database import NoteDatabase


class NoteDatabaseSystem:
    def __init__(self, db_path: str = "notes.db"):
        self.db = NoteDatabase(db_path)
        self.active_sessions: Dict[str, str] = {}  # session_id -> username

    # -------- auth --------
    def register_user(self, username: str, password: str) -> str:
        if not username.strip() or not password:
            return json.dumps({"success": False, "message": "Username and password are required"})
        if self.db.create_user(username.strip(), password):
            return json.dumps({"success": True, "message": "User registered successfully"})
        return json.dumps({"success": False, "message": "Username already exists"})

    def login_user(self, username: str, password: str) -> str:
        if not username.strip() or not password:
            return json.dumps({"success": False, "message": "Username and password are required"})
        if self.db.verify_user(username.strip(), password):
            sid = str(uuid.uuid4())
            self.active_sessions[sid] = username.strip()
            return json.dumps({"success": True, "message": "Login successful", "session_id": sid})
        return json.dumps({"success": False, "message": "Invalid username or password"})

    def logout_user(self, session_id: str) -> str:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return json.dumps({"success": True, "message": "Logout successful"})
        return json.dumps({"success": False, "message": "Invalid session"})

    def _get_username_from_session(self, session_id: str) -> Optional[str]:
        return self.active_sessions.get(session_id)

    def _uid(self, session_id: str) -> Optional[int]:
        uname = self._get_username_from_session(session_id)
        if not uname:
            return None
        return self.db.get_user_id(uname)

    # -------- notes --------
    def create_note(self, session_id: str, title: str, content: str, folder_id: Optional[int] = None) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not title.strip() or not content.strip():
            return json.dumps({"success": False, "message": "Title and content are required"})
        note_id = self.db.create_note(uid, title.strip(), content.strip(), folder_id)
        if note_id:
            return json.dumps({"success": True, "message": "Note created successfully", "note_id": note_id})
        return json.dumps({"success": False, "message": "Note title already exists"})

    def get_note(self, session_id: str, title: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not title.strip():
            return json.dumps({"success": False, "message": "Title is required"})
        note = self.db.get_note_by_title(uid, title.strip())
        if note:
            return json.dumps({"success": True, "note": note})
        return json.dumps({"success": False, "message": "Note not found"})

    def list_notes(self, session_id: str, limit: int = 50) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        notes = self.db.get_user_notes(uid, limit)
        for n in notes:
            n["preview"] = n["content"][:100] + ("..." if len(n["content"]) > 100 else "")
            del n["content"]
        return json.dumps({"success": True, "notes": notes, "count": len(notes)})

    def edit_note(self, session_id: str, title: str, new_content: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not title.strip() or not new_content.strip():
            return json.dumps({"success": False, "message": "Title and content are required"})
        ok = self.db.update_note_content(uid, title.strip(), new_content.strip())
        return json.dumps({"success": ok, "message": "Note updated successfully" if ok else "Note not found"})

    def delete_note(self, session_id: str, title: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not title.strip():
            return json.dumps({"success": False, "message": "Title is required"})
        ok = self.db.delete_note(uid, title.strip())
        return json.dumps({"success": ok, "message": "Note deleted successfully" if ok else "Note not found"})

    def search_notes(self, session_id: str, query: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not query.strip():
            return json.dumps({"success": False, "message": "Search query is required"})
        results = self.db.search_user_notes(uid, query.strip())
        for r in results:
            r["preview"] = r["content"][:150] + ("..." if len(r["content"]) > 150 else "")
            del r["content"]
        return json.dumps({"success": True, "results": results, "count": len(results)})

    def add_tags(self, session_id: str, title: str, tags: List[str]) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not title.strip():
            return json.dumps({"success": False, "message": "Title is required"})
        if not tags or not any(t.strip() for t in tags):
            return json.dumps({"success": False, "message": "At least one valid tag is required"})
        all_tags = self.db.add_note_tags(uid, title.strip(), [t.strip() for t in tags if t.strip()])
        if all_tags is None:
            return json.dumps({"success": False, "message": "Note not found"})
        return json.dumps({"success": True, "tags": all_tags})

    def set_note_folder(self, session_id: str, title: str, folder_id: Optional[int]) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        ok = self.db.set_note_folder(uid, title.strip(), folder_id)
        return json.dumps({"success": ok, "message": "Note moved" if ok else "Note not found"})

    # -------- todos --------
    def create_todo(self, session_id: str, title: str, description: str = "",
                    due_date: str = None, priority: str = "normal",
                    tags: List[str] = None, note_title: str = None) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not title.strip():
            return json.dumps({"success": False, "message": "Title is required"})
        if priority not in {"low", "normal", "high"}:
            priority = "normal"
        todo_id = self.db.create_todo(uid, title.strip(), description.strip() if description else "",
                                      due_date, priority, note_title.strip() if note_title else None)
        if todo_id and tags:
            clean = [t.strip() for t in tags if t.strip()]
            if clean:
                self.db.add_todo_tags(uid, todo_id, clean)
        return json.dumps({"success": True, "id": todo_id, "message": "Todo created"})

    def list_todos(self, session_id: str, status: str = None, tag: str = None,
                   priority: str = None, linked_to_note: str = None) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        todos = self.db.get_user_todos(uid, status, tag, priority, linked_to_note)
        results = [{
            "id": t["id"],
            "title": t["title"],
            "due_date": t["due_date"],
            "priority": t["priority"],
            "completed": t["completed"],
            "tags": t["tags"],
            "note_title": t["note_title"],
        } for t in todos]
        return json.dumps({"success": True, "results": results})

    def toggle_todo(self, session_id: str, todo_id: int) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        ok = self.db.toggle_todo(uid, todo_id)
        return json.dumps({"success": ok, "message": "Todo updated" if ok else "Todo not found"})

    def delete_todo(self, session_id: str, todo_id: int) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        ok = self.db.delete_todo(uid, todo_id)
        return json.dumps({"success": ok, "message": "Todo deleted" if ok else "Todo not found"})

    # -------- folders --------
    def create_folder(self, session_id: str, name: str, parent_id: Optional[int]) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not name.strip():
            return json.dumps({"success": False, "message": "Folder name is required"})
        fid = self.db.create_folder(uid, name.strip(), parent_id)
        return json.dumps({"success": True, "id": fid, "message": "Folder created"})

    def list_folders(self, session_id: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        tree = self.db.list_folders_tree(uid)
        return json.dumps({"success": True, "folders": tree})

    def rename_folder(self, session_id: str, folder_id: int, new_name: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not new_name.strip():
            return json.dumps({"success": False, "message": "Folder name is required"})
        ok = self.db.rename_folder(uid, folder_id, new_name.strip())
        return json.dumps({"success": ok, "message": "Folder renamed" if ok else "Folder not found"})

    def move_folder(self, session_id: str, folder_id: int, new_parent_id: Optional[int]) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        ok = self.db.move_folder(uid, folder_id, new_parent_id)
        return json.dumps({"success": ok, "message": "Folder moved" if ok else "Move failed"})

    def delete_folder(self, session_id: str, folder_id: int) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        ok = self.db.delete_folder(uid, folder_id)
        return json.dumps({"success": ok, "message": "Folder deleted" if ok else "Folder not found"})

    # -------- reminders --------
    def create_reminder(self, session_id: str, text: str, time: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        if not text.strip() or not time:
            return json.dumps({"success": False, "message": "Text and time are required"})
        rid = self.db.create_reminder(uid, text.strip(), time)
        return json.dumps({"success": True, "id": rid, "message": "Reminder created"})

    def list_reminders(self, session_id: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        items = self.db.list_reminders(uid)
        return json.dumps({"success": True, "items": items})

    def delete_reminder(self, session_id: str, reminder_id: int) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        ok = self.db.delete_reminder(uid, reminder_id)
        return json.dumps({"success": ok, "message": "Reminder deleted" if ok else "Reminder not found"})

    # -------- stats --------
    def get_stats(self, session_id: str) -> str:
        uid = self._uid(session_id)
        if not uid:
            return json.dumps({"success": False, "message": "Not logged in"})
        stats = self.db.get_user_stats(uid)
        # Flatten keys to match your stats.html expectations
        data = {
            "notes": stats["total_notes"],
            "todos": stats["total_todos"],
            "folders": stats["total_folders"],
            "reminders": stats["total_reminders"],
            "tags": stats["total_tags"],
            "recent_note": stats["recent_note"],
        }
        return json.dumps({"success": True, "data": data})