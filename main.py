import json
import uuid
import time
import threading
from typing import Optional, List, Dict, Any
from database import NoteDatabase
from datetime import date, datetime, timedelta


class NoteDatabaseSystem:
    def __init__(self, db_path: str = "notes.db"):
        self.db = NoteDatabase(db_path)
        self.active_sessions = {}  # session_id -> username

    def register_user(self, username: str, password: str) -> str:
        """Register a new user"""
        if self.db.create_user(username, password):
            return json.dumps({"success": True, "message": "User registered successfully"})
        else:
            return json.dumps({"success": False, "message": "Username already exists"})

    def login_user(self, username: str, password: str) -> str:
        """Login user and create session"""
        if self.db.verify_user(username, password):
            session_id = str(uuid.uuid4())
            self.active_sessions[session_id] = username
            return json.dumps({
                "success": True,
                "message": "Login successful",
                "session_id": session_id
            })
        else:
            return json.dumps({"success": False, "message": "Invalid username or password"})

    def logout_user(self, session_id: str) -> str:
        """Logout user"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return json.dumps({"success": True, "message": "Logout successful"})
        return json.dumps({"success": False, "message": "Invalid session"})

    def _get_username_from_session(self, session_id: str) -> Optional[str]:
        """Get username from session ID"""
        return self.active_sessions.get(session_id)

    def _validate_session(self, session_id: str) -> Optional[int]:
        """Validate session and return user_id"""
        username = self._get_username_from_session(session_id)
        if not username:
            return None
        return self.db.get_user_id(username)

    def create_note(self, session_id: str, title: str, content: str) -> str:
        """Create a new note"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        note_id = self.db.create_note(user_id, title, content)
        if note_id:
            return json.dumps({
                "success": True,
                "message": "Note created successfully",
                "note_id": note_id
            })
        else:
            return json.dumps({"success": False, "message": "Note title already exists"})

    def get_note(self, session_id: str, title: str) -> str:
        """Get a specific note by title"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        note = self.db.get_note_by_title(user_id, title)
        if note:
            return json.dumps({"success": True, "note": note})
        else:
            return json.dumps({"success": False, "message": "Note not found"})

    def list_notes(self, session_id: str, limit: int = 50) -> str:
        """List all notes for the user"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        notes = self.db.get_user_notes(user_id, limit)

        for note in notes:
            note["preview"] = note["content"][:100] + ("..." if len(note["content"]) > 100 else "")
            del note["content"]

        return json.dumps({"success": True, "notes": notes, "count": len(notes)})

    def edit_note(self, session_id: str, title: str, new_content: str) -> str:
        """Edit note content"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        if self.db.update_note_content(user_id, title, new_content):
            return json.dumps({"success": True, "message": "Note updated successfully"})
        else:
            return json.dumps({"success": False, "message": "Note not found"})

    def delete_note(self, session_id: str, title: str) -> str:
        """Delete a note"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        if self.db.delete_note(user_id, title):
            return json.dumps({"success": True, "message": "Note deleted successfully"})
        else:
            return json.dumps({"success": False, "message": "Note not found"})

    def search_notes(self, session_id: str, query: str) -> str:
        """Search notes by keyword"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        results = self.db.search_user_notes(user_id, query)

        for result in results:
            result["preview"] = result["content"][:150] + ("..." if len(result["content"]) > 150 else "")
            del result["content"]

        return json.dumps({"success": True, "results": results, "count": len(results)})

    def add_tags(self, session_id: str, title: str, tags: List[str]) -> str:
        """Add tags to a note"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        all_tags = self.db.add_note_tags(user_id, title, tags)
        if all_tags is not None:
            return json.dumps({"success": True, "tags": all_tags})
        else:
            return json.dumps({"success": False, "message": "Note not found"})

    def get_stats(self, session_id: str) -> str:
        """Get user statistics"""
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})

        stats = self.db.get_user_stats(user_id)
        return json.dumps({"success": True, "stats": stats})


user_todos: Dict[str, List[Dict[str, Any]]] = {}  # username -> list of todos

def _ensure_user_todos(username: str) -> None:
    if username not in user_todos:
        user_todos[username] = []

def _reminder_worker(username: str, title: str, remind_time: datetime):
    while datetime.now() < remind_time:
        time.sleep(10)
    print(f"\n=== Reminder for {username} ===\nTask: {title}\nTime: {datetime.now()}\n")

def create_todo(
    username: str,
    title: str,
    description: str = "",
    due_date: str | None = None,
    priority: str = "normal",
    tags: list[str] | None = None,
    note_title: str | None = None,
    reminder_minutes: int | None = None
) -> str:
    _ensure_user_todos(username)

    if priority not in {"low", "normal", "high"}:
        return json.dumps({"success": False, "message": "Invalid priority"})

    due_date_parsed = None
    if due_date:
        try:
            due_date_parsed = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        except ValueError:
            return json.dumps({"success": False, "message": "Due date must be YYYY-MM-DD HH:MM"})

    todo = {
        "id": len(user_todos[username]) + 1,
        "created": str(date.today()),
        "title": title,
        "description": description,
        "due_date": due_date_parsed.isoformat() if due_date_parsed else None,
        "priority": priority,
        "completed": False,
        "tags": list(set(tags or [])),
        "note_title": note_title
    }
    user_todos[username].append(todo)

    if reminder_minutes:
        remind_time = datetime.now() + timedelta(minutes=reminder_minutes)
        threading.Thread(target=_reminder_worker, args=(username, title, remind_time)).start()

    return json.dumps({"success": True, "id": todo["id"], "message": "Todo created"})

def list_todos(username: str, status: str | None = None, tag: str | None = None,
               priority: str | None = None, linked_to_note: str | None = None) -> str:
    _ensure_user_todos(username)
    items = user_todos[username]

    results = []
    for t in items:
        overdue = False
        if t["due_date"]:
            due_dt = datetime.fromisoformat(t["due_date"])
            if not t["completed"] and datetime.now() > due_dt:
                overdue = True
        results.append({
            "id": t["id"],
            "title": t["title"],
            "due_date": t["due_date"],
            "priority": t["priority"],
            "completed": t["completed"],
            "tags": t["tags"],
            "note_title": t["note_title"],
            "overdue": overdue
        })
    return json.dumps({"success": True, "results": results})

def get_todo(username: str, todo_id: int) -> str:
    _ensure_user_todos(username)
    for t in user_todos[username]:
        if t["id"] == todo_id:
            return json.dumps({"success": True, "todo": t})
    return json.dumps({"success": False, "message": "Todo not found"})

def toggle_todo(username: str, todo_id: int, completed: bool | None = None) -> str:
    _ensure_user_todos(username)
    for t in user_todos[username]:
        if t["id"] == todo_id:
            t["completed"] = (not t["completed"]) if completed is None else bool(completed)
            return json.dumps({"success": True, "message": "Todo updated", "completed": t["completed"]})
    return json.dumps({"success": False, "message": "Todo not found"})

def delete_todo(username: str, todo_id: int) -> str:
    _ensure_user_todos(username)
    for i, t in enumerate(user_todos[username]):
        if t["id"] == todo_id:
            del user_todos[username][i]
            return json.dumps({"success": True, "message": "Todo deleted"})
    return json.dumps({"success": False, "message": "Todo not found"})


def main():
    system = NoteDatabaseSystem()
    current_session = None

    print("=== Note Taking System (Database Edition) ===")

    while True:
        if not current_session:
            print("\n1. Register")
            print("2. Login")
            print("3. Exit")
            choice = input("Choose option: ")

            if choice == "1":
                username = input("Username: ")
                password = input("Password: ")
                result = json.loads(system.register_user(username, password))
                print(result["message"])

            elif choice == "2":
                username = input("Username: ")
                password = input("Password: ")
                result = json.loads(system.login_user(username, password))
                print(result["message"])
                if result["success"]:
                    current_session = result["session_id"]

            elif choice == "3":
                break

        else:
            print(f"\n=== Notes Menu ===")
            print("1. Create Note")
            print("2. List Notes")
            print("3. View Note")
            print("4. Edit Note")
            print("5. Delete Note")
            print("6. Search Notes")
            print("7. Add Tags")
            print("8. View Stats")
            print("9. Todo List")
            print("10. Logout")

            choice = input("Choose option: ")

            if choice == "9":
                while True:
                    print(f"\n=== Todos Menu ({username}) ===")
                    print("1. Create Todo")
                    print("2. List Todos")
                    print("3. Toggle Todo Completion")
                    print("4. Delete Todo")
                    print("5. Back to Main Menu")

                    choice3 = input("Choose option: ")

                    if choice3 == "1":
                        title = input("Todo title: ")
                        desc = input("Description: ")
                        due = input("Due date (YYYY-MM-DD HH:MM or blank): ") or None
                        prio = input("Priority (low/normal/high): ") or "normal"
                        tags_input = input("Tags (comma-separated): ")
                        tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                        reminder = input("Reminder in minutes (blank for none): ")
                        reminder_minutes = int(reminder) if reminder.strip() else None
                        result = json.loads(create_todo(username, title, desc, due, prio, tags, reminder_minutes=reminder_minutes))
                        print(result["message"])

                    elif choice3 == "2":
                        result = json.loads(list_todos(username))
                        print(f"\n=== Todos ({len(result['results'])}) ===")
                        for todo in result["results"]:
                            status = "X" if todo["completed"] else " "
                            overdue_mark = " (OVERDUE!)" if todo["overdue"] else ""
                            print(f"[{status}] {todo['id']}. {todo['title']} "
                                  f"(Priority: {todo['priority']}, Due: {todo['due_date']}){overdue_mark}")

                    elif choice3 == "3":
                        todo_id = int(input("Todo ID to toggle: "))
                        result = json.loads(toggle_todo(username, todo_id))
                        print(result["message"])

                    elif choice3 == "4":
                        todo_id = int(input("Todo ID to delete: "))
                        result = json.loads(delete_todo(username, todo_id))
                        print(result["message"])

                    elif choice3 == "5":
                        break
                    else:
                        print("Invalid choice")

            elif choice == "10":
                system.logout_user(current_session)
                current_session = None
                print("Logged out successfully")


if __name__ == "__main__":
    main()
