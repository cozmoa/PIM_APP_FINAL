import sqlite3
import bcrypt
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

        # Folders
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
          folder_id INTEGER,
          FOREIGN KEY (user_id) REFERENCES users (id),
          UNIQUE(user_id, title)
        )
        """)

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

    # ---------- AUTH ----------
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

    # ---------- FOLDERS ----------
    def create_folder(self, user_id: int, name: str, parent_id: Optional[int] = None) -> int:
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

    def list_folders_tree(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, name, parent_id FROM folders WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        conn.close()
        nodes = {r[0]: {"id": r[0], "name": r[1], "parent_id": r[2], "children": []} for r in rows}
        roots = []
        for node in nodes.values():
            if node["parent_id"] and node["parent_id"] in nodes:
                nodes[node["parent_id"]]["children"].append(node)
            else:
                roots.append(node)
        return roots

    # ---------- NOTES ----------
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

    def get_user_notes(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, folder_id FROM notes WHERE user_id = ?", (user_id,))
        notes = [{"id": r[0], "title": r[1], "content": r[2], "folder_id": r[3]} for r in cur.fetchall()]
        conn.close()
        return notes
