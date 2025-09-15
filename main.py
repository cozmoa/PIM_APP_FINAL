import json
from datetime import date

user_notes = {}
user_todos = {}  

def create_note(username: str, title: str, content: str) -> str:
    """
    Create a new note for a user.
    Returns JSON: {"success": bool, "message": str}
    """
    if username not in user_notes:
        user_notes[username] = []
    for note in user_notes[username]:
        if note["title"] == title:
            return json.dumps({"success": False, "message": "Note title already exists"})
    user_notes[username].append({
        "id": len(user_notes[username]) + 1,
        "date": str(date.today()),
        "title": title,
        "content": content
    })
    return json.dumps({"success": True, "message": "Note created"})


def get_note(username: str, title: str) -> str:
    for note in user_notes.get(username, []):
        if note["title"] == title:
            return json.dumps({"success": True, "note": note})
    return json.dumps({"success": False, "note": None})


def in_place_viewer(username: str, title: str) -> str:
    for note in user_notes.get(username, []):
        if note["title"] == title:
            preview = note["content"][:120] + ("…" if len(note["content"]) > 120 else "")
            return json.dumps({
                "success": True,
                "title": note["title"],
                "preview": preview,
                "date": note["date"]
            })
    return json.dumps({"success": False, "message": "Note not found"})


def particle_viewer(username: str, title: str) -> str:
    for note in user_notes.get(username, []):
        if note["title"] == title:
            return json.dumps({
                "success": True,
                "title": note["title"],
                "content": note["content"],
                "date": note["date"],
                "reminder": note.get("reminder"),
                "tags": note.get("tags", [])
            })
    return json.dumps({"success": False, "message": "Note not found"})


def render_markdown(content: str) -> str:
    try:
        html = markdown.markdown(content)
        return json.dumps({"success": True, "html": html})
    except Exception as e:
        return json.dumps({"success": False, "html": "", "message": str(e)})


def edit_note(username: str, title: str, new_content: str) -> str:
    for note in user_notes.get(username, []):
        if note["title"] == title:
            note["content"] = new_content
            return json.dumps({"success": True, "message": "Note updated"})
    return json.dumps({"success": False, "message": "Note not found"})


def delete_note(username: str, title: str) -> str:
    notes = user_notes.get(username, [])
    for i, note in enumerate(notes):
        if note["title"] == title:
            del notes[i]
            return json.dumps({"success": True, "message": "Note deleted"})
    return json.dumps({"success": False, "message": "Note not found"})


def search_notes(username: str, query: str) -> str:
    results = []
    for note in user_notes.get(username, []):
        if query.lower() in note["title"].lower() or query.lower() in note["content"].lower():
            results.append({
                "id": note["id"],
                "date": note["date"],
                "title": note["title"]
            })
    return json.dumps({"success": True, "results": results})


def set_reminder(username: str, title: str, reminder_date: str) -> str:
    """
    Set a reminder date for a specific note.
    """
    for note in user_notes.get(username, []):
        if note["title"] == title:
            note["reminder"] = reminder_date
            return json.dumps({
                "success": True,
                "message": f"Reminder set for {reminder_date}"
            })
    return json.dumps({"success": False, "message": "Note not found"})


def add_tags(username: str, title: str, tags: list[str]) -> str:
    """
    Add tags to a note. Duplicates are ignored.
    """
    for note in user_notes.get(username, []):
        if note["title"] == title:
            if "tags" not in note:
                note["tags"] = []
            note["tags"].extend(tags)
            note["tags"] = list(set(note["tags"]))  # remove duplicates
            return json.dumps({"success": True, "tags": note["tags"]})
    return json.dumps({"success": False, "message": "Note not found"})


def _ensure_user_todos(username: str) -> None:
    if username not in user_todos:
        user_todos[username] = []


def create_todo(
    username: str,
    title: str,
    description: str = "",
    due_date: str | None = None,
    priority: str = "normal",  
    tags: list[str] | None = None,
    note_title: str | None = None
) -> str:
    """
    Create a new todo for a user. Optionally link to an existing note by title.
    Returns JSON: {"success": bool, "id": int, "message": str}
    """
    _ensure_user_todos(username)
    if priority not in {"low", "normal", "high"}:
        return json.dumps({"success": False, "message": "Invalid priority"})
    if note_title:
        if not any(n["title"] == note_title for n in user_notes.get(username, [])):
            return json.dumps({"success": False, "message": "Linked note not found"})

    todo = {
        "id": len(user_todos[username]) + 1,
        "created": str(date.today()),
        "title": title,
        "description": description,
        "due_date": due_date,  
        "priority": priority,
        "completed": False,
        "tags": list(set(tags or [])),
        "note_title": note_title
    }
    user_todos[username].append(todo)
    return json.dumps({"success": True, "id": todo["id"], "message": "Todo created"})


def list_todos(
    username: str,
    status: str | None = None,       
    tag: str | None = None,
    priority: str | None = None,     
    linked_to_note: str | None = None  
) -> str:
    """
    List todos for a user with optional filters.
    """
    _ensure_user_todos(username)
    items = user_todos[username]

    def ok(todo):
        if status == "open" and todo["completed"]:
            return False
        if status == "done" and not todo["completed"]:
            return False
        if tag and tag not in todo["tags"]:
            return False
        if priority and todo["priority"] != priority:
            return False
        if linked_to_note and todo["note_title"] != linked_to_note:
            return False
        return True

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
        for t in items if ok(t)
    ]
    return json.dumps({"success": True, "results": results})


def get_todo(username: str, todo_id: int) -> str:
    _ensure_user_todos(username)
    for t in user_todos[username]:
        if t["id"] == todo_id:
            return json.dumps({"success": True, "todo": t})
    return json.dumps({"success": False, "message": "Todo not found"})


def toggle_todo(username: str, todo_id: int, completed: bool | None = None) -> str:
    """
    Toggle completion. If 'completed' is None, flips the current state.
    """
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


if __name__ == "__main__":
    user = "demo"

    print("== Create Notes ==")
    print(create_note(user, "Sport Cars", "Top 10 new sport cars"))
    print(create_note(user, "Luxury Cars", "Top 10 new luxury cars"))

    print("\n== Search Notes (cars) ==")
    print(search_notes(user, "cars"))

    print("\n== Add Reminder ==")
    print(set_reminder(user, "Sport Cars", "2025-09-01"))
    print(particle_viewer(user, "Sport Cars"))

    print("\n== Add Tags ==")
    print(add_tags(user, "Luxury Cars", ["expensive", "premium", "2025"]))
    print(particle_viewer(user, "Luxury Cars"))

    print("\n== Create Todos ==")
    print(create_todo(user, "Shortlist models", "Pick 5 cars to review",
                      due_date="2025-09-05", priority="high",
                      tags=["cars", "review"], note_title="Sport Cars"))
    print(create_todo(user, "Draft article outline", "Structure sections",
                      priority="normal", tags=["writing"]))
    print(create_todo(user, "Price research", "Collect MSRP data",
                      due_date="2025-09-03", priority="low",
                      tags=["research", "cars"], note_title="Luxury Cars"))

    print("\n== List OPEN Todos ==")
    print(list_todos(user, status="open"))

    print("\n== Toggle completion for #1 ==")
    print(toggle_todo(user, 1))

    print("\n== Get Todo #2 ==")
    print(get_todo(user, 2))

    print("\n== Delete Todo #3 ==")
    print(delete_todo(user, 3))

    print("\n== List all Todos after delete ==")
    print(list_todos(user))
