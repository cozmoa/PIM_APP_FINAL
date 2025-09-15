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


