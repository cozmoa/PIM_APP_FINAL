# main.py
import json
import uuid
from typing import Optional, List, Dict, Any
from backend.database import NoteDatabase   # ✅ corrected import path

class NoteDatabaseSystem:
    def __init__(self, db_path: str = "notes.db"):
        try:
            self.db = NoteDatabase(db_path)
            self.active_sessions = {}  # session_id -> username
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")

    def register_user(self, username: str, password: str) -> str:
        """Register a new user"""
        try:
            if not username.strip() or not password:
                return json.dumps({"success": False, "message": "Username and password are required"})
            
            if self.db.create_user(username.strip(), password):
                return json.dumps({"success": True, "message": "User registered successfully"})
            else:
                return json.dumps({"success": False, "message": "Username already exists"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Registration failed: {str(e)}"})

    def login_user(self, username: str, password: str) -> str:
        """Login user and create session"""
        try:
            if not username.strip() or not password:
                return json.dumps({"success": False, "message": "Username and password are required"})
            
            if self.db.verify_user(username.strip(), password):
                session_id = str(uuid.uuid4())
                self.active_sessions[session_id] = username.strip()
                return json.dumps({
                    "success": True,
                    "message": "Login successful",
                    "session_id": session_id
                })
            else:
                return json.dumps({"success": False, "message": "Invalid username or password"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Login failed: {str(e)}"})

    def logout_user(self, session_id: str) -> str:
        """Logout user"""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                return json.dumps({"success": True, "message": "Logout successful"})
            return json.dumps({"success": False, "message": "Invalid session"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Logout failed: {str(e)}"})

    def _get_username_from_session(self, session_id: str) -> Optional[str]:
        """Get username from session ID"""
        return self.active_sessions.get(session_id)

    def _validate_session(self, session_id: str) -> Optional[int]:
        """Validate session and return user_id"""
        try:
            username = self._get_username_from_session(session_id)
            if not username:
                return None
            return self.db.get_user_id(username)
        except Exception:
            return None

    # ------------------------
    # NOTES METHODS
    # ------------------------
    def create_note(self, session_id: str, title: str, content: str) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not title.strip() or not content.strip():
                return json.dumps({"success": False, "message": "Title and content are required"})

            note_id = self.db.create_note(user_id, title.strip(), content.strip())
            if note_id:
                return json.dumps({
                    "success": True,
                    "message": "Note created successfully",
                    "note_id": note_id
                })
            return json.dumps({"success": False, "message": "Note title already exists"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create note: {str(e)}"})

    def get_note(self, session_id: str, title: str) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            note = self.db.get_note_by_title(user_id, title.strip())
            if note:
                return json.dumps({"success": True, "note": note})
            return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get note: {str(e)}"})

    def list_notes(self, session_id: str, limit: int = 50) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            notes = self.db.get_user_notes(user_id, limit)
            for note in notes:
                note["preview"] = note["content"][:100] + ("..." if len(note["content"]) > 100 else "")
                del note["content"]
            return json.dumps({"success": True, "notes": notes, "count": len(notes)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to list notes: {str(e)}"})

    def edit_note(self, session_id: str, title: str, new_content: str) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not title.strip() or not new_content.strip():
                return json.dumps({"success": False, "message": "Title and content are required"})
            if self.db.update_note_content(user_id, title.strip(), new_content.strip()):
                return json.dumps({"success": True, "message": "Note updated successfully"})
            return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to edit note: {str(e)}"})

    def delete_note(self, session_id: str, title: str) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})
            if self.db.delete_note(user_id, title.strip()):
                return json.dumps({"success": True, "message": "Note deleted successfully"})
            return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to delete note: {str(e)}"})

    def search_notes(self, session_id: str, query: str) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not query.strip():
                return json.dumps({"success": False, "message": "Search query is required"})
            results = self.db.search_user_notes(user_id, query.strip())
            for result in results:
                result["preview"] = result["content"][:150] + ("..." if len(result["content"]) > 150 else "")
                del result["content"]
            return json.dumps({"success": True, "results": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Search failed: {str(e)}"})

    def add_tags(self, session_id: str, title: str, tags: List[str]) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})
            if not tags or not any(tag.strip() for tag in tags):
                return json.dumps({"success": False, "message": "At least one valid tag is required"})
            clean_tags = [tag.strip() for tag in tags if tag.strip()]
            all_tags = self.db.add_note_tags(user_id, title.strip(), clean_tags)
            if all_tags is not None:
                return json.dumps({"success": True, "tags": all_tags})
            return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to add tags: {str(e)}"})

    def get_stats(self, session_id: str) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            stats = self.db.get_user_stats(user_id)
            return json.dumps({"success": True, "stats": stats})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get stats: {str(e)}"})

    # ------------------------
    # TODOS METHODS
    # ------------------------
    def create_todo(self, session_id: str, title: str, description: str = "", 
                   due_date: str = None, priority: str = "normal", 
                   tags: List[str] = None, note_title: str = None) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})
            if priority not in {"low", "normal", "high"}:
                priority = "normal"
            todo_id = self.db.create_todo(user_id, title.strip(), description.strip() if description else "", 
                                          due_date, priority, note_title.strip() if note_title else None)
            if todo_id and tags:
                clean_tags = [tag.strip() for tag in tags if tag.strip()]
                if clean_tags:
                    self.db.add_todo_tags(user_id, todo_id, clean_tags)
            return json.dumps({"success": True, "id": todo_id, "message": "Todo created"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create todo: {str(e)}"})

    def list_todos(self, session_id: str, status: str = None, tag: str = None,
                   priority: str = None, linked_to_note: str = None) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            todos = self.db.get_user_todos(user_id, status, tag, priority, linked_to_note)
            results = [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "due_date": t["due_date"],
                    "priority": t["priority"],
                    "completed": t["completed"],
                    "tags": t["tags"],
                    "note_title": t["note_title"]
                }
                for t in todos
            ]
            return json.dumps({"success": True, "results": results})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to list todos: {str(e)}"})

    def toggle_todo(self, session_id: str, todo_id: int) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if self.db.toggle_todo(user_id, todo_id):
                return json.dumps({"success": True, "message": "Todo updated"})
            return json.dumps({"success": False, "message": "Todo not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to toggle todo: {str(e)}"})

    def delete_todo(self, session_id: str, todo_id: int) -> str:
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            if self.db.delete_todo(user_id, todo_id):
                return json.dumps({"success": True, "message": "Todo deleted"})
            return json.dumps({"success": False, "message": "Todo not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to delete todo: {str(e)}"})