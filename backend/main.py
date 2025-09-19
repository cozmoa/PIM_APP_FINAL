# main_pim_final.py
import json
import uuid
from typing import Optional, List, Dict, Any
from database import NoteDatabase

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
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is require and cannot be empty"})
            
            if not password:
                return json.dumps({"success": False, "message": "Password is required and cannot be empty"})
            if not password.strip():
                return json.dumps({"success": False, "message": "Password cannot be only whitespace"})
            
            if len(password.strip()) < 3:
                return json.dumps({"success": False, "message": "Password must be at least 3 characters long"})
            
            clean_username = username.strip()
            clean_password = password.strip()
            if self.db.create_user(clean_username, clean_password):
                return json.dumps({"success": True, "message": "User registered successfully"})
            else:
                return json.dumps({"success": False, "message": "User registration failed"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Registration failed: {str(e)}"})

    def login_user(self, username: str, password: str) -> str:
        """Login user and create session"""
        try:
            if not username or not username.strip():
                return json.dumps({"success": False, "message": "Username is required and cannot be empty"})
            
            if not password:
                return json.dumps({"success": False, "message": "Password is required and cannot be empty"})

            if not password.strip():
                return json.dumps({"success": False, "message": "Password cannot be only whitespace"})
            
            clean_username = username.strip()
            clean_password = password.strip()
            
            if self.db.verify_user(clean_username, clean_password):
                session_id = str(uuid.uuid4())
                self.active_sessions[session_id] = clean_username
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

    def create_note(self, session_id: str, title: str, content: str) -> str:
        """Create a new note"""
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
            else:
                return json.dumps({"success": False, "message": "Note title already exists"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create note: {str(e)}"})

    def get_note(self, session_id: str, title: str) -> str:
        """Get a specific note by title"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            note = self.db.get_note_by_title(user_id, title.strip())
            if note:
                return json.dumps({"success": True, "note": note})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get note: {str(e)}"})

    def list_notes(self, session_id: str, limit: int = 50) -> str:
        """List all notes for the user"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            notes = self.db.get_user_notes(user_id, limit)

            # Create preview for each note
            for note in notes:
                note["preview"] = note["content"][:100] + ("..." if len(note["content"]) > 100 else "")
                # Remove full content from list view
                del note["content"]

            return json.dumps({"success": True, "notes": notes, "count": len(notes)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to list notes: {str(e)}"})

    def edit_note(self, session_id: str, title: str, new_content: str) -> str:
        """Edit note content"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip() or not new_content.strip():
                return json.dumps({"success": False, "message": "Title and content are required"})

            if self.db.update_note_content(user_id, title.strip(), new_content.strip()):
                return json.dumps({"success": True, "message": "Note updated successfully"})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to edit note: {str(e)}"})
        

         
                   
    def update_note_title(self, session_id: str, old_title: str, new_title: str) -> str:
        """Update note title"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not old_title.strip() or not new_title.strip():
                return json.dumps({"success": False, "message": "Both titles are required"})
            
            existing_note = self.db.get_note_by_title(user_id, new_title.strip())
            if existing_note:
                return json.dumps({"success": False, "message": "Original note not found"})
    
            if self.db.update_note_title(user_id, old_title.strip(), new_title.strip()):
                return json.dumps({"success": True, "message": "Note title updated successfully"})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to update note title: {str(e)}"})       
                   

    def delete_note(self, session_id: str, title: str) -> str:
        """Delete a note"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})

            if self.db.delete_note(user_id, title.strip()):
                return json.dumps({"success": True, "message": "Note deleted successfully"})
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to delete note: {str(e)}"})

    def search_notes(self, session_id: str, query: str) -> str:
        """Search notes by keyword"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if not query.strip():
                return json.dumps({"success": False, "message": "Search query is required"})

            results = self.db.search_user_notes(user_id, query.strip())

            # Create preview for each result
            for result in results:
                result["preview"] = result["content"][:150] + ("..." if len(result["content"]) > 150 else "")
                # Remove full content from search results
                del result["content"]

            return json.dumps({"success": True, "results": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Search failed: {str(e)}"})

    def add_tags(self, session_id: str, title: str, tags: List[str]) -> str:
        """Add tags to a note"""
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
            else:
                return json.dumps({"success": False, "message": "Note not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to add tags: {str(e)}"})

    def get_stats(self, session_id: str) -> str:
        """Get user statistics"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            stats = self.db.get_user_stats(user_id)
            return json.dumps({"success": True, "stats": stats})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to get stats: {str(e)}"})

    # Todo methods using database
    def create_todo(self, session_id: str, title: str, description: str = "", 
                   due_date: str = None, priority: str = "normal", 
                   tags: List[str] = None, note_title: str = None) -> str:
        """Create a new todo"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})
            
            if not title.strip():
                return json.dumps({"success": False, "message": "Title is required"})
            
            if priority not in {"low", "normal", "high"}:
                priority = "normal"  # Default to normal if invalid
            
            todo_id = self.db.create_todo(user_id, title.strip(), description.strip() if description else "", 
                                        due_date, priority, note_title.strip() if note_title else None)
            
            if todo_id and tags:
                # Add tags to the todo
                clean_tags = [tag.strip() for tag in tags if tag.strip()]
                if clean_tags:
                    self.db.add_todo_tags(user_id, todo_id, clean_tags)
            
            return json.dumps({"success": True, "id": todo_id, "message": "Todo created"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to create todo: {str(e)}"})

    def list_todos(self, session_id: str, status: str = None, tag: str = None,
                  priority: str = None, linked_to_note: str = None) -> str:
        """List todos for the user"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            todos = self.db.get_user_todos(user_id, status, tag, priority, linked_to_note)
            
            # Format response similar to original
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
        """Toggle todo completion status"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if self.db.toggle_todo(user_id, todo_id):
                return json.dumps({"success": True, "message": "Todo updated"})
            else:
                return json.dumps({"success": False, "message": "Todo not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to toggle todo: {str(e)}"})

    def delete_todo(self, session_id: str, todo_id: int) -> str:
        """Delete a todo"""
        try:
            user_id = self._validate_session(session_id)
            if not user_id:
                return json.dumps({"success": False, "message": "Not logged in"})

            if self.db.delete_todo(user_id, todo_id):
                return json.dumps({"success": True, "message": "Todo deleted"})
            else:
                return json.dumps({"success": False, "message": "Todo not found"})
        except Exception as e:
            return json.dumps({"success": False, "message": f"Failed to delete todo: {str(e)}"})

# ADD THESE METHODS at the end of NoteDatabaseSystem class

def create_folder(self, session_id: str, name: str, parent_id: int = None) -> str:
    """Create a new folder"""
    try:
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})
        
        folder_id = self.db.create_folder(user_id, name.strip(), parent_id)
        if folder_id:
            return json.dumps({"success": True, "folder_id": folder_id})
        else:
            return json.dumps({"success": False, "message": "Folder name already exists"})
    except Exception as e:
        return json.dumps({"success": False, "message": f"Failed to create folder: {str(e)}"})

def get_user_folders(self, session_id: str) -> str:
    """Get all folders for user as tree structure"""
    try:
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})
        
        folders = self.db.get_user_folders_tree(user_id)
        return json.dumps({"success": True, "folders": folders})
    except Exception as e:
        return json.dumps({"success": False, "message": f"Failed to get folders: {str(e)}"})

def link_note_to_folder(self, session_id: str, note_title: str, folder_id: int) -> str:
    """Link a note to a folder"""
    try:
        user_id = self._validate_session(session_id)
        if not user_id:
            return json.dumps({"success": False, "message": "Not logged in"})
        
        success = self.db.link_note_to_folder(user_id, note_title, folder_id)
        if success:
            return json.dumps({"success": True, "message": "Note linked to folder"})
        else:
            return json.dumps({"success": False, "message": "Note or folder not found"})
    except Exception as e:
        return json.dumps({"success": False, "message": f"Failed to link note: {str(e)}"})
    
def run_cli():
    """CLI interface for the database-powered note system - call this function to start CLI"""
    system = NoteDatabaseSystem()
    current_session = None

    print("=== Note Taking System (Database Edition) ===")

    while True:
        try:
            if not current_session:
                print("\n1. Register")
                print("2. Login")
                print("3. Exit")
                choice = input("Choose option: ").strip()

                if choice == "1":
                    username = input("Username: ").strip()
                    password = input("Password: ").strip()
                    if username and password:
                        result = json.loads(system.register_user(username, password))
                        print(result["message"])
                    else:
                        print("Username and password cannot be empty")

                elif choice == "2":
                    username = input("Username: ").strip()
                    password = input("Password: ").strip()
                    if username and password:
                        result = json.loads(system.login_user(username, password))
                        print(result["message"])
                        if result["success"]:
                            current_session = result["session_id"]
                    else:
                        print("Username and password cannot be empty")

                elif choice == "3":
                    print("Goodbye!")
                    break

                else:
                    print("Invalid choice")

            else:
                username = system._get_username_from_session(current_session)
                print(f"\n=== Notes Menu ({username}) ===")
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
               
                choice = input("Choose option: ").strip()

                if choice == "1":
                    title = input("Note title: ").strip()
                    if not title:
                        print("Title cannot be empty")
                        continue
                    print("Enter content (type 'END' on a new line to finish):")
                    content_lines = []
                    while True:
                        line = input()
                        if line == "END":
                            break
                        content_lines.append(line)
                    content = "\n".join(content_lines)
                    result = json.loads(system.create_note(current_session, title, content))
                    print(result["message"])

                elif choice == "2":
                    result = json.loads(system.list_notes(current_session))
                    if result["success"]:
                        print(f"\n=== Your Notes ({result['count']}) ===")
                        if result["notes"]:
                            for note in result["notes"]:
                                tags_str = ", ".join(note["tags"]) if note["tags"] else "No tags"
                                print(f"• {note['title']} (Modified: {note['modified_at']})")
                                print(f"  Tags: {tags_str}")
                                print(f"  {note['preview']}\n")
                        else:
                            print("No notes found")
                    else:
                        print(result["message"])

                elif choice == "3":
                    title = input("Note title to view: ").strip()
                    if not title:
                        print("Title cannot be empty")
                        continue
                    result = json.loads(system.get_note(current_session, title))
                    if result["success"]:
                        note = result["note"]
                        print(f"\n=== {note['title']} ===")
                        print(f"Created: {note['created_at']}")
                        print(f"Modified: {note['modified_at']}")
                        if note["tags"]:
                            print(f"Tags: {', '.join(note['tags'])}")
                        print(f"\n{note['content']}\n")
                    else:
                        print(result["message"])

                elif choice == "4":
                    title = input("Note title to edit: ").strip()
                    if not title:
                        print("Title cannot be empty")
                        continue
                    print("Enter new content (type 'END' on a new line to finish):")
                    content_lines = []
                    while True:
                        line = input()
                        if line == "END":
                            break
                        content_lines.append(line)
                    new_content = "\n".join(content_lines)
                    result = json.loads(system.edit_note(current_session, title, new_content))
                    print(result["message"])

                elif choice == "5":
                    title = input("Note title to delete: ").strip()
                    if not title:
                        print("Title cannot be empty")
                        continue
                    confirm = input(f"Are you sure you want to delete '{title}'? (y/N): ")
                    if confirm.lower() == 'y':
                        result = json.loads(system.delete_note(current_session, title))
                        print(result["message"])
                    else:
                        print("Deletion cancelled")

                elif choice == "6":
                    query = input("Search query: ").strip()
                    if not query:
                        print("Search query cannot be empty")
                        continue
                    result = json.loads(system.search_notes(current_session, query))
                    if result["success"] and result["results"]:
                        print(f"\n=== Search Results ({result['count']}) ===")
                        for note in result["results"]:
                            print(f"• {note['title']} (Modified: {note['modified_at']})")
                            print(f"  {note['preview']}\n")
                    else:
                        print("No results found")

                elif choice == "7":
                    title = input("Note title to add tags to: ").strip()
                    if not title:
                        print("Title cannot be empty")
                        continue
                    tags_input = input("Tags (comma-separated): ").strip()
                    if not tags_input:
                        print("Tags cannot be empty")
                        continue
                    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
                    if not tags:
                        print("No valid tags provided")
                        continue
                    result = json.loads(system.add_tags(current_session, title, tags))
                    if result["success"]:
                        print(f"All tags: {', '.join(result['tags'])}")
                    else:
                        print(result["message"])

                elif choice == "8":
                    result = json.loads(system.get_stats(current_session))
                    if result["success"]:
                        stats = result["stats"]
                        print(f"\n=== Your Statistics ===")
                        print(f"Total Notes: {stats['total_notes']}")
                        print(f"Unique Tags: {stats['total_tags']}")
                        print(f"Total Todos: {stats['total_todos']}")
                        if stats["recent_note"]["title"]:
                            print(f"Most Recent: {stats['recent_note']['title']}")
                            print(f"Last Modified: {stats['recent_note']['modified_at']}")
                    else:
                        print(result["message"])

                elif choice == "9":
                    while True:
                        print(f"\n=== Todos Menu ({username}) ===")
                        print("1. Create Todo")
                        print("2. List Todos")
                        print("3. Toggle Todo Completion")
                        print("4. Delete Todo")
                        print("5. Back to Main Menu")

                        todo_choice = input("Choose option: ").strip()

                        if todo_choice == "1":
                            title = input("Todo title: ").strip()
                            if not title:
                                print("Title cannot be empty")
                                continue
                            desc = input("Description: ").strip()
                            due = input("Due date (YYYY-MM-DD or blank): ").strip() or None
                            prio = input("Priority (low/normal/high): ").strip() or "normal"
                            if prio not in {"low", "normal", "high"}:
                                print("Invalid priority, using 'normal'")
                                prio = "normal"
                            tags_input = input("Tags (comma-separated): ").strip()
                            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else None
                            note_title = input("Link to note title (or blank): ").strip() or None
                            result = json.loads(system.create_todo(current_session, title, desc, due, prio, tags, note_title))
                            print(result["message"])

                        elif todo_choice == "2":
                            result = json.loads(system.list_todos(current_session))
                            if result["success"]:
                                print(f"\n=== Todos ({len(result['results'])}) ===")
                                if result["results"]:
                                    for todo in result["results"]:
                                        status = "✓" if todo["completed"] else " "
                                        note_info = f" -> {todo['note_title']}" if todo['note_title'] else ""
                                        tags_info = f" [{', '.join(todo['tags'])}]" if todo['tags'] else ""
                                        print(f"[{status}] {todo['id']}. {todo['title']}{note_info}{tags_info}")
                                        print(f"    Priority: {todo['priority']}, Due: {todo['due_date'] or 'No due date'}")
                                else:
                                    print("No todos found")
                            else:
                                print(result["message"])

                        elif todo_choice == "3":
                            try:
                                todo_id = int(input("Todo ID to toggle: ").strip())
                                result = json.loads(system.toggle_todo(current_session, todo_id))
                                print(result["message"])
                            except ValueError:
                                print("Invalid todo ID")

                        elif todo_choice == "4":
                            try:
                                todo_id = int(input("Todo ID to delete: ").strip())
                                confirm = input(f"Are you sure you want to delete todo {todo_id}? (y/N): ")
                                if confirm.lower() == 'y':
                                    result = json.loads(system.delete_todo(current_session, todo_id))
                                    print(result["message"])
                                else:
                                    print("Deletion cancelled")
                            except ValueError:
                                print("Invalid todo ID")

                        elif todo_choice == "5":
                            break
                        else:
                            print("Invalid choice")

                elif choice == "10":
                    system.logout_user(current_session)
                    current_session = None
                    print("Logged out successfully")

                else:
                    print("Invalid choice")
                    
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")


# Example usage and main entry point
if __name__ == "__main__":
    # The CLI will only run when this file is executed directly
    run_cli()