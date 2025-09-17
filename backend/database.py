# backend/database.py
import sqlite3
import bcrypt
from datetime import datetime
from typing import Optional, List, Dict, Any


class NoteDatabase:
    def __init__(self, db_path: str = "notes.db"):
        self.db_path = db_path
        self._init_database()

    # ---------- helpers ----------
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, decl: str):
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            conn.commit()

    # ---------- schema ----------
    def _init_database(self):
        conn = self._connect()
        c = conn.cursor()

        # Users
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Folders (self-referencing; cascade deletes subfolders)
        c.execute("""
        CREATE TABLE IF NOT EXISTS folders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          parent_id INTEGER,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(parent_id) REFERENCES folders(id) ON DELETE CASCADE
        )
        """)

        # Notes
        c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          reminder_date TEXT,
          FOREIGN KEY (user_id) REFERENCES users (id),
          UNIQUE(user_id, title)
        )
        """)

        # add folder_id to notes if not present
        self._ensure_column(conn, "notes", "folder_id", "INTEGER")

        # add FK after column exists (SQLite doesn’t add FK retroactively; we’ll enforce logically)
        # (We still keep SET NULL behavior in our Python delete logic)

        # Tags
        c.execute("""
        CREATE TABLE IF NOT EXISTS tags (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT UNIQUE NOT NULL
        )
        """)

        # Note-Tag
        c.execute("""
        CREATE TABLE IF NOT EXISTS note_tags (
          note_id INTEGER,
          tag_id INTEGER,
          PRIMARY KEY (note_id, tag_id),
          FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
          FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """)

        # Todos
        c.execute("""
        CREATE TABLE IF NOT EXISTS todos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          title TEXT NOT NULL,
          description TEXT DEFAULT '',
          due_date TEXT,
          priority TEXT DEFAULT 'normal',
          completed BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          note_id INTEGER,
          FOREIGN KEY (user_id) REFERENCES users (id),
          FOREIGN KEY (note_id) REFERENCES notes (id)
        )
        """)

        # Todo-Tag
        c.execute("""
        CREATE TABLE IF NOT EXISTS todo_tags (
          todo_id INTEGER,
          tag_id INTEGER,
          PRIMARY KEY (todo_id, tag_id),
          FOREIGN KEY (todo_id) REFERENCES todos(id) ON DELETE CASCADE,
          FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """)

        # Reminders
        c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          text TEXT NOT NULL,
          time TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # Indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_notes_folder_id ON notes(folder_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id)')

        conn.commit()
        conn.close()

    # ---------- auth ----------
    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, password: str, hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hash.encode("utf-8"))

    def create_user(self, username: str, password: str) -> bool:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, self._hash_password(password)),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def verify_user(self, username: str, password: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        return bool(row and self._verify_password(password, row[0]))

    def get_user_id(self, username: str) -> Optional[int]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    # ---------- notes ----------
    def create_note(self, user_id: int, title: str, content: str, folder_id: Optional[int] = None) -> Optional[int]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notes (user_id, title, content, folder_id) VALUES (?, ?, ?, ?)",
                (user_id, title, content, folder_id),
            )
            note_id = cur.lastrowid
            conn.commit()
            return note_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_note_by_title(self, user_id: int, title: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, title, content, created_at, modified_at, reminder_date, folder_id
               FROM notes WHERE user_id = ? AND title = ?""",
            (user_id, title),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        # tags
        cur.execute(
            """SELECT t.name FROM tags t
               JOIN note_tags nt ON t.id = nt.tag_id
               WHERE nt.note_id = ?""",
            (row[0],),
        )
        tags = [r[0] for r in cur.fetchall()]
        conn.close()
        return {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "created_at": row[3],
            "modified_at": row[4],
            "reminder_date": row[5],
            "folder_id": row[6],
            "tags": tags,
        }

    def get_user_notes(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, title, content, created_at, modified_at, folder_id
               FROM notes WHERE user_id = ? ORDER BY modified_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = cur.fetchall()
        notes = []
        for r in rows:
            note_id = r[0]
            # tags
            cur.execute(
                """SELECT t.name FROM tags t
                   JOIN note_tags nt ON t.id = nt.tag_id
                   WHERE nt.note_id = ?""",
                (note_id,),
            )
            tags = [x[0] for x in cur.fetchall()]
            notes.append(
                {
                    "id": r[0],
                    "title": r[1],
                    "content": r[2],
                    "created_at": r[3],
                    "modified_at": r[4],
                    "folder_id": r[5],
                    "tags": tags,
                }
            )
        conn.close()
        return notes

    def update_note_content(self, user_id: int, title: str, new_content: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """UPDATE notes SET content = ?, modified_at = CURRENT_TIMESTAMP
               WHERE user_id = ? AND title = ?""",
            (new_content, user_id, title),
        )
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def set_note_folder(self, user_id: int, title: str, folder_id: Optional[int]) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE notes SET folder_id = ? WHERE user_id = ? AND title = ?",
            (folder_id, user_id, title),
        )
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def delete_note(self, user_id: int, title: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE user_id = ? AND title = ?", (user_id, title))
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def search_user_notes(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        like = f"%{query}%"
        cur.execute(
            """SELECT id, title, content, created_at, modified_at
               FROM notes WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)
               ORDER BY modified_at DESC""",
            (user_id, like, like),
        )
        results = [
            {"id": r[0], "title": r[1], "content": r[2], "created_at": r[3], "modified_at": r[4]}
            for r in cur.fetchall()
        ]
        conn.close()
        return results

    def add_note_tags(self, user_id: int, title: str, tags: List[str]) -> Optional[List[str]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM notes WHERE user_id = ? AND title = ?", (user_id, title))
        note = cur.fetchone()
        if not note:
            conn.close()
            return None
        note_id = note[0]
        try:
            for name in tags:
                cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
                cur.execute("SELECT id FROM tags WHERE name = ?", (name,))
                tag_id = cur.fetchone()[0]
                cur.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
            cur.execute(
                """SELECT t.name FROM tags t
                   JOIN note_tags nt ON t.id = nt.tag_id
                   WHERE nt.note_id = ?""",
                (note_id,),
            )
            all_tags = [r[0] for r in cur.fetchall()]
            conn.commit()
            return all_tags
        except Exception:
            return None
        finally:
            conn.close()

    # ---------- todos ----------
    def create_todo(
        self,
        user_id: int,
        title: str,
        description: str = "",
        due_date: Optional[str] = None,
        priority: str = "normal",
        note_title: Optional[str] = None,
    ) -> Optional[int]:
        conn = self._connect()
        cur = conn.cursor()
        note_id = None
        if note_title:
            cur.execute("SELECT id FROM notes WHERE user_id = ? AND title = ?", (user_id, note_title))
            row = cur.fetchone()
            if row:
                note_id = row[0]
        cur.execute(
            """INSERT INTO todos (user_id, title, description, due_date, priority, note_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, title, description, due_date, priority, note_id),
        )
        todo_id = cur.lastrowid
        conn.commit()
        conn.close()
        return todo_id

    def get_user_todos(
        self, user_id: int, status: Optional[str] = None, tag: Optional[str] = None,
        priority: Optional[str] = None, linked_to_note: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        q = """
        SELECT t.id, t.title, t.description, t.due_date, t.priority, t.completed, t.created_at, n.title
        FROM todos t
        LEFT JOIN notes n ON n.id = t.note_id
        WHERE t.user_id = ?
        """
        params = [user_id]
        if status == "open":
            q += " AND t.completed = 0"
        elif status == "done":
            q += " AND t.completed = 1"
        if priority:
            q += " AND t.priority = ?"
            params.append(priority)
        if linked_to_note:
            q += " AND n.title = ?"
            params.append(linked_to_note)
        q += " ORDER BY t.created_at DESC"
        cur.execute(q, params)
        todos = []
        for row in cur.fetchall():
            todo_id = row[0]
            # tags for todo
            cur.execute(
                """SELECT t.name FROM tags t
                   JOIN todo_tags tt ON t.id = tt.tag_id
                   WHERE tt.todo_id = ?""",
                (todo_id,),
            )
            tags = [x[0] for x in cur.fetchall()]
            if tag and tag not in tags:
                continue
            todos.append(
                {
                    "id": todo_id,
                    "title": row[1],
                    "description": row[2],
                    "due_date": row[3],
                    "priority": row[4],
                    "completed": bool(row[5]),
                    "created_at": row[6],
                    "note_title": row[7],
                    "tags": tags,
                }
            )
        conn.close()
        return todos

    def toggle_todo(self, user_id: int, todo_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT completed FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        new_val = 0 if row[0] else 1
        cur.execute("UPDATE todos SET completed = ? WHERE id = ? AND user_id = ?", (new_val, todo_id, user_id))
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def delete_todo(self, user_id: int, todo_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def add_todo_tags(self, user_id: int, todo_id: int, tags: List[str]) -> Optional[List[str]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
        if not cur.fetchone():
            conn.close()
            return None
        try:
            for name in tags:
                cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
                cur.execute("SELECT id FROM tags WHERE name = ?", (name,))
                tag_id = cur.fetchone()[0]
                cur.execute("INSERT OR IGNORE INTO todo_tags (todo_id, tag_id) VALUES (?, ?)", (todo_id, tag_id))
            cur.execute(
                """SELECT t.name FROM tags t
                   JOIN todo_tags tt ON t.id = tt.tag_id
                   WHERE tt.todo_id = ?""",
                (todo_id,),
            )
            all_tags = [r[0] for r in cur.fetchall()]
            conn.commit()
            return all_tags
        except Exception:
            return None
        finally:
            conn.close()

    # ---------- folders ----------
    def create_folder(self, user_id: int, name: str, parent_id: Optional[int]) -> int:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO folders (user_id, name, parent_id) VALUES (?, ?, ?)",
            (user_id, name, parent_id),
        )
        folder_id = cur.lastrowid
        conn.commit()
        conn.close()
        return folder_id

    def rename_folder(self, user_id: int, folder_id: int, new_name: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "UPDATE folders SET name = ? WHERE id = ? AND user_id = ?",
            (new_name, folder_id, user_id),
        )
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def move_folder(self, user_id: int, folder_id: int, new_parent_id: Optional[int]) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        # prevent setting parent to itself
        if new_parent_id == folder_id:
            conn.close()
            return False
        cur.execute(
            "UPDATE folders SET parent_id = ? WHERE id = ? AND user_id = ?",
            (new_parent_id, folder_id, user_id),
        )
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def delete_folder(self, user_id: int, folder_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        # detach notes from this folder (and its descendants)
        descendants = self._collect_descendants(conn, user_id, folder_id)
        ids = [folder_id] + descendants
        cur.execute(
            f"UPDATE notes SET folder_id = NULL WHERE user_id = ? AND folder_id IN ({','.join('?'*len(ids))})",
            (user_id, *ids),
        )
        # delete folders (children are deleted by ON DELETE CASCADE)
        cur.execute("DELETE FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    def _collect_descendants(self, conn: sqlite3.Connection, user_id: int, folder_id: int) -> List[int]:
        cur = conn.cursor()
        cur.execute("SELECT id FROM folders WHERE user_id = ? AND parent_id = ?", (user_id, folder_id))
        children = [r[0] for r in cur.fetchall()]
        all_ids = []
        for cid in children:
            all_ids.append(cid)
            all_ids.extend(self._collect_descendants(conn, user_id, cid))
        return all_ids

    def list_folders_tree(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, name, parent_id FROM folders WHERE user_id = ? ORDER BY name", (user_id,))
        rows = cur.fetchall()
        conn.close()
        nodes = {r[0]: {"id": r[0], "name": r[1], "parent_id": r[2], "children": []} for r in rows}
        roots: List[Dict[str, Any]] = []
        for node in nodes.values():
            pid = node["parent_id"]
            if pid and pid in nodes:
                nodes[pid]["children"].append(node)
            else:
                roots.append(node)
        return roots

    # ---------- reminders ----------
    def create_reminder(self, user_id: int, text: str, time: str) -> int:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO reminders (user_id, text, time) VALUES (?, ?, ?)", (user_id, text, time))
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        return rid

    def list_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, text, time, created_at FROM reminders WHERE user_id = ? ORDER BY time ASC",
            (user_id,),
        )
        items = [{"id": r[0], "text": r[1], "time": r[2], "created_at": r[3]} for r in cur.fetchall()]
        conn.close()
        return items

    def delete_reminder(self, user_id: int, reminder_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        ok = cur.rowcount > 0
        conn.commit()
        conn.close()
        return ok

    # ---------- stats ----------
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM notes WHERE user_id = ?", (user_id,))
        notes_cnt = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(DISTINCT t.id)
            FROM tags t
            JOIN note_tags nt ON t.id = nt.tag_id
            JOIN notes n ON n.id = nt.note_id
            WHERE n.user_id = ?
        """, (user_id,))
        tags_cnt = cur.fetchone()[0]

        cur.execute("""
            SELECT title, modified_at FROM notes
            WHERE user_id = ?
            ORDER BY modified_at DESC LIMIT 1
        """, (user_id,))
        recent = cur.fetchone()

        cur.execute("SELECT COUNT(*) FROM todos WHERE user_id = ?", (user_id,))
        todos_cnt = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM folders WHERE user_id = ?", (user_id,))
        folders_cnt = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM reminders WHERE user_id = ?", (user_id,))
        reminders_cnt = cur.fetchone()[0]

        conn.close()
        return {
            "total_notes": notes_cnt,
            "total_tags": tags_cnt,
            "total_todos": todos_cnt,
            "total_folders": folders_cnt,
            "total_reminders": reminders_cnt,
            "recent_note": {
                "title": recent[0] if recent else None,
                "modified_at": recent[1] if recent else None,
            },
        }