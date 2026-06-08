import sqlite3
import threading
import time
import atexit
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import calendar

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

VALID_REPEAT_PATTERNS = ['none', 'daily', 'weekly', 'monthly', 'yearly']
VALID_TEAM_ROLES = ['admin', 'member']

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

DB_TYPE = os.environ.get('DB_TYPE', 'sqlite').lower()
if DB_TYPE == 'postgresql' and HAS_PSYCOPG2:
    DATABASE_CONFIG = {
        'host': os.environ.get('DB_HOST', 'db'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('DB_NAME', 'todo_app'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'postgres'),
    }
else:
    DATABASE = os.environ.get('DB_PATH', 'todo.db')
    DB_TYPE = 'sqlite'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'zip', 'rar', 'md'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def get_db_connection_string():
    if DB_TYPE == 'postgresql':
        return f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
    return DATABASE

def format_datetime(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_due_date(date_str):
    if not date_str:
        return None
    try:
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(date_str[:16], '%Y-%m-%dT%H:%M')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return None

def parse_datetime(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return None

def calculate_next_repeat_date(current_date_str, repeat_pattern):
    if not repeat_pattern or repeat_pattern == 'none':
        return None
    current_dt = parse_datetime(current_date_str)
    if current_dt is None:
        current_dt = datetime.now()
    if repeat_pattern == 'daily':
        next_dt = current_dt + timedelta(days=1)
    elif repeat_pattern == 'weekly':
        next_dt = current_dt + timedelta(weeks=1)
    elif repeat_pattern == 'monthly':
        year = current_dt.year
        month = current_dt.month + 1
        if month > 12:
            month = 1
            year += 1
        day = min(current_dt.day, calendar.monthrange(year, month)[1])
        next_dt = current_dt.replace(year=year, month=month, day=day)
    elif repeat_pattern == 'yearly':
        try:
            next_dt = current_dt.replace(year=current_dt.year + 1)
        except ValueError:
            next_dt = current_dt.replace(year=current_dt.year + 1, day=28)
    else:
        return None
    return format_datetime(next_dt)

def validate_repeat_pattern(pattern):
    if pattern is None or pattern == '':
        return 'none'
    if pattern in VALID_REPEAT_PATTERNS:
        return pattern
    return 'none'

def get_repeat_root_id(cursor, user_id, task_id):
    if task_id is None:
        return None
    visited = set()
    current_id = task_id
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        cursor.execute(
            'SELECT id, repeat_parent_id FROM tasks WHERE id = ? AND user_id = ?',
            (current_id, user_id)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        if row['repeat_parent_id'] is None:
            return row['id']
        current_id = row['repeat_parent_id']
    return None

def series_has_active_next(cursor, user_id, root_id):
    if root_id is None:
        return False
    cursor.execute('''
        SELECT COUNT(*) as cnt FROM tasks 
        WHERE user_id = ? 
        AND completed = 0
        AND repeat_pattern IS NOT NULL 
        AND repeat_pattern != 'none'
        AND (id = ? OR repeat_parent_id = ?)
    ''', (user_id, root_id, root_id))
    return cursor.fetchone()['cnt'] > 0

class DictRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

    def __iter__(self):
        return super().__iter__()


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
        self._lastrowid = None

    def _convert_params(self, params):
        if params is None:
            return ()
        if isinstance(params, (list, tuple)):
            return tuple(params)
        return params

    def _convert_query(self, query):
        q = query.replace('?', '%s')
        q = q.replace('INSERT OR IGNORE', 'INSERT')
        if 'INSERT' in q.upper() and 'ON CONFLICT' not in q.upper():
            if 'task_tags' in q.lower():
                q = q + ' ON CONFLICT DO NOTHING'
        return q

    @property
    def lastrowid(self):
        return self._lastrowid

    def _try_fetch_last_id(self, query):
        import re
        match = re.search(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            try:
                self._cursor.execute(f"SELECT currval(pg_get_serial_sequence('{table_name}', 'id'))")
                result = self._cursor.fetchone()
                if result:
                    if hasattr(result, 'items'):
                        self._lastrowid = list(dict(result).values())[0]
                    else:
                        self._lastrowid = result[0]
            except Exception:
                pass

    def execute(self, query, params=None):
        pg_query = self._convert_query(query)
        pg_params = self._convert_params(params)
        result = self._cursor.execute(pg_query, pg_params)
        if query.strip().upper().startswith('INSERT'):
            self._try_fetch_last_id(pg_query)
        return result

    def executemany(self, query, seq_of_params):
        pg_query = self._convert_query(query)
        return self._cursor.executemany(pg_query, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, 'items'):
            return DictRow(row)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        result = []
        for row in rows:
            if hasattr(row, 'items'):
                result.append(DictRow(row))
            else:
                result.append(row)
        return result

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __iter__(self):
        for row in self._cursor:
            if hasattr(row, 'items'):
                yield DictRow(row)
            else:
                yield row


class PostgresConnectionWrapper:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return PostgresCursorWrapper(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def rollback(self):
        return self._connection.rollback()

    def close(self):
        return self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


def get_db():
    if DB_TYPE == 'postgresql':
        conn = psycopg2.connect(
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port'],
            database=DATABASE_CONFIG['database'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            cursor_factory=RealDictCursor
        )
        conn.autocommit = False
        return PostgresConnectionWrapper(conn)
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn


def get_postgres_columns(cursor, table_name):
    cursor.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table_name,)
    )
    return [row['column_name'] for row in cursor.fetchall()]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def attachment_to_dict(attachment):
    return {
        'id': attachment['id'],
        'task_id': attachment['task_id'],
        'filename': attachment['filename'],
        'original_filename': attachment['original_filename'],
        'file_path': attachment['file_path'],
        'file_size': attachment['file_size'],
        'mime_type': attachment['mime_type'],
        'created_at': attachment['created_at']
    }

def migrate_db():
    conn = get_db()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        columns = get_postgres_columns(cursor, 'tasks')
    else:
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
    
    if 'category_id' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN category_id INTEGER REFERENCES categories (id) ON DELETE SET NULL
        ''')
        conn.commit()
    
    if 'priority' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'
        ''')
        conn.commit()
    
    if 'due_date' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN due_date TIMESTAMP
        ''')
        conn.commit()
    
    if 'is_pinned' not in columns:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                ALTER TABLE tasks ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE
            ''')
        else:
            cursor.execute('''
                ALTER TABLE tasks ADD COLUMN is_pinned BOOLEAN DEFAULT 0
            ''')
        conn.commit()
    
    if 'repeat_pattern' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN repeat_pattern TEXT DEFAULT 'none'
        ''')
        conn.commit()
    
    if 'repeat_parent_id' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN repeat_parent_id INTEGER REFERENCES tasks (id) ON DELETE SET NULL
        ''')
        conn.commit()
    
    if 'completed_at' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN completed_at TIMESTAMP
        ''')
        conn.commit()
        if DB_TYPE == 'postgresql':
            cursor.execute('''
                UPDATE tasks
                SET completed_at = COALESCE(updated_at, created_at)
                WHERE completed = TRUE AND completed_at IS NULL
            ''')
        else:
            cursor.execute('''
                UPDATE tasks
                SET completed_at = COALESCE(updated_at, created_at)
                WHERE completed = 1 AND completed_at IS NULL
            ''')
        conn.commit()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        ''')
    conn.commit()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            UPDATE tasks
            SET completed_at = COALESCE(updated_at, created_at)
            WHERE completed = TRUE AND completed_at IS NULL
        ''')
    else:
        cursor.execute('''
            UPDATE tasks
            SET completed_at = COALESCE(updated_at, created_at)
            WHERE completed = 1 AND completed_at IS NULL
        ''')
    conn.commit()

    if 'assignee_id' not in columns:
        cursor.execute('''
            ALTER TABLE tasks ADD COLUMN assignee_id INTEGER REFERENCES users (id) ON DELETE SET NULL
        ''')
        conn.commit()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                invite_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(team_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_invitations (
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                invited_by INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_shares (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                team_id INTEGER,
                shared_with_user_id INTEGER,
                can_edit BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (shared_with_user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                invite_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(team_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                invited_by INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                team_id INTEGER,
                shared_with_user_id INTEGER,
                can_edit BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (shared_with_user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
    conn.commit()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_comments (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES task_comments (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_likes (
                id SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES task_comments (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(comment_id, user_id)
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES task_comments (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES task_comments (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(comment_id, user_id)
            )
        ''')
    conn.commit()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_templates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                category_id INTEGER,
                is_pinned BOOLEAN DEFAULT FALSE,
                repeat_pattern TEXT DEFAULT 'none',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_template_tags (
                template_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (template_id, tag_id),
                FOREIGN KEY (template_id) REFERENCES task_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                category_id INTEGER,
                is_pinned BOOLEAN DEFAULT 0,
                repeat_pattern TEXT DEFAULT 'none',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_template_tags (
                template_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (template_id, tag_id),
                FOREIGN KEY (template_id) REFERENCES task_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
    conn.commit()
    
    conn.close()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    if DB_TYPE == 'postgresql':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                due_date TIMESTAMP,
                completed BOOLEAN DEFAULT FALSE,
                is_pinned BOOLEAN DEFAULT FALSE,
                repeat_pattern TEXT DEFAULT 'none',
                repeat_parent_id INTEGER,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                FOREIGN KEY (repeat_parent_id) REFERENCES tasks (id) ON DELETE SET NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_tags (
                task_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_id, tag_id),
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_comments (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES task_comments (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_likes (
                id SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES task_comments (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(comment_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_templates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                category_id INTEGER,
                is_pinned BOOLEAN DEFAULT FALSE,
                repeat_pattern TEXT DEFAULT 'none',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_template_tags (
                template_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (template_id, tag_id),
                FOREIGN KEY (template_id) REFERENCES task_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                due_date TIMESTAMP,
                completed BOOLEAN DEFAULT 0,
                is_pinned BOOLEAN DEFAULT 0,
                repeat_pattern TEXT DEFAULT 'none',
                repeat_parent_id INTEGER,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                FOREIGN KEY (repeat_parent_id) REFERENCES tasks (id) ON DELETE SET NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#667eea',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_tags (
                task_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_id, tag_id),
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                invite_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(team_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                invited_by INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                team_id INTEGER,
                shared_with_user_id INTEGER,
                can_edit BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
                FOREIGN KEY (shared_with_user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                parent_id INTEGER,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES task_comments (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES task_comments (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(comment_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                category_id INTEGER,
                is_pinned BOOLEAN DEFAULT 0,
                repeat_pattern TEXT DEFAULT 'none',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
                UNIQUE(user_id, name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_template_tags (
                template_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (template_id, tag_id),
                FOREIGN KEY (template_id) REFERENCES task_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        ''')
    conn.commit()
    conn.close()
    
    migrate_db()

def team_to_dict(team, member_count=0):
    result = {
        'id': team['id'],
        'name': team['name'],
        'description': team['description'],
        'created_by': team['created_by'],
        'invite_token': team['invite_token'],
        'created_at': team['created_at'],
        'member_count': member_count
    }
    return result

def team_member_to_dict(member, user=None):
    result = {
        'id': member['id'],
        'team_id': member['team_id'],
        'user_id': member['user_id'],
        'role': member['role'],
        'joined_at': member['joined_at']
    }
    if user:
        result['username'] = user['username']
    return result

def task_share_to_dict(share):
    return {
        'id': share['id'],
        'task_id': share['task_id'],
        'team_id': share['team_id'],
        'shared_with_user_id': share['shared_with_user_id'],
        'can_edit': bool(share['can_edit']),
        'created_at': share['created_at']
    }

def comment_to_dict(comment, user=None, like_count=0, is_liked=False, reply_user=None):
    result = {
        'id': comment['id'],
        'task_id': comment['task_id'],
        'user_id': comment['user_id'],
        'parent_id': comment['parent_id'],
        'content': comment['content'],
        'created_at': comment['created_at'],
        'updated_at': comment['updated_at'],
        'like_count': like_count,
        'is_liked': is_liked
    }
    if user:
        result['user'] = user_to_dict(user)
    if reply_user:
        result['reply_user'] = user_to_dict(reply_user)
    return result

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'error': '令牌缺失'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '令牌无效'}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

def user_to_dict(user):
    return {
        'id': user['id'],
        'username': user['username'],
        'created_at': user['created_at']
    }

def category_to_dict(category):
    return {
        'id': category['id'],
        'name': category['name'],
        'color': category['color'],
        'created_at': category['created_at']
    }

def tag_to_dict(tag):
    return {
        'id': tag['id'],
        'name': tag['name'],
        'color': tag['color'],
        'created_at': tag['created_at']
    }

def task_to_dict(task, category=None, tags=None, attachments=None, assignee=None, creator=None):
    result = {
        'id': task['id'],
        'user_id': task['user_id'],
        'category_id': task['category_id'],
        'assignee_id': task['assignee_id'] if 'assignee_id' in task.keys() else None,
        'title': task['title'],
        'description': task['description'],
        'priority': task['priority'],
        'due_date': task['due_date'],
        'completed': bool(task['completed']),
        'is_pinned': bool(task['is_pinned']),
        'repeat_pattern': task['repeat_pattern'] or 'none',
        'repeat_parent_id': task['repeat_parent_id'],
        'completed_at': task['completed_at'],
        'created_at': task['created_at'],
        'updated_at': task['updated_at']
    }
    if category:
        result['category'] = category_to_dict(category)
    if tags is not None:
        result['tags'] = [tag_to_dict(tag) for tag in tags]
    if attachments is not None:
        result['attachments'] = [attachment_to_dict(att) for att in attachments]
    if assignee:
        result['assignee'] = user_to_dict(assignee)
    if creator:
        result['creator'] = user_to_dict(creator)
    return result

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    username = data['username']
    password = data['password']
    
    if len(username) < 3:
        return jsonify({'error': '用户名至少需要 3 个字符'}), 400
    
    if len(password) < 6:
        return jsonify({'error': '密码至少需要 6 个字符'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return jsonify({'error': '用户名已存在'}), 400
    
    password_hash = generate_password_hash(password)
    cursor.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, password_hash)
    )
    conn.commit()
    
    user_id = cursor.lastrowid
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': user_to_dict(user)
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    username = data['username']
    password = data['password']
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    token = jwt.encode({
        'user_id': user['id'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': user_to_dict(user)
    })

@app.route('/api/tasks', methods=['GET'])
@token_required
def get_tasks(current_user_id):
    category_id_raw = request.args.get('category_id', type=str)
    tag_id_raw = request.args.get('tag_id', type=str)
    search = request.args.get('search', type=str)
    
    category_id = None
    category_is_none = False
    if category_id_raw is not None:
        if category_id_raw == 'none':
            category_is_none = True
        else:
            try:
                category_id = int(category_id_raw)
            except (ValueError, TypeError):
                category_id = None
    
    tag_id = None
    tag_is_none = False
    if tag_id_raw is not None:
        if tag_id_raw == 'none':
            tag_is_none = True
        else:
            try:
                tag_id = int(tag_id_raw)
            except (ValueError, TypeError):
                tag_id = None
    
    conn = get_db()
    cursor = conn.cursor()
    
    params = [current_user_id]
    where_clauses = ['t.user_id = ?']
    
    if search:
        search_pattern = f'%{search}%'
        where_clauses.append('(t.title LIKE ? OR t.description LIKE ?)')
        params.extend([search_pattern, search_pattern])
    
    if category_is_none:
        where_clauses.append('t.category_id IS NULL')
    elif category_id is not None:
        where_clauses.append('t.category_id = ?')
        params.append(category_id)
    
    if tag_is_none:
        where_clauses.append('''
            t.id NOT IN (SELECT DISTINCT task_id FROM task_tags)
        ''')
    elif tag_id is not None:
        where_clauses.append('''
            t.id IN (SELECT DISTINCT task_id FROM task_tags WHERE tag_id = ?)
        ''')
        params.append(tag_id)
    
    where_sql = ' AND '.join(where_clauses)
    query = f'''
        SELECT DISTINCT t.* FROM tasks t
        WHERE {where_sql}
        ORDER BY t.is_pinned DESC, t.created_at DESC
    '''
    cursor.execute(query, params)
    
    tasks = cursor.fetchall()
    
    result = []
    for task in tasks:
        category = None
        if task['category_id']:
            cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], current_user_id))
            category = cursor.fetchone()
        cursor.execute('''
            SELECT t.* FROM tags t
            INNER JOIN task_tags tt ON t.id = tt.tag_id
            WHERE tt.task_id = ? AND t.user_id = ?
            ORDER BY t.created_at ASC
        ''', (task['id'], current_user_id))
        tags = cursor.fetchall()
        cursor.execute('''
            SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
        ''', (task['id'],))
        attachments = cursor.fetchall()
        result.append(task_to_dict(task, category, tags, attachments))
    
    conn.close()
    return jsonify(result)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    category = None
    if task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], current_user_id))
        category = cursor.fetchone()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (task['id'], current_user_id))
    tags = cursor.fetchall()
    
    cursor.execute('''
        SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
    ''', (task['id'],))
    attachments = cursor.fetchall()
    
    conn.close()
    return jsonify(task_to_dict(task, category, tags, attachments))

def create_next_repeat_task(cursor, original_task, current_user_id):
    if not original_task['repeat_pattern'] or original_task['repeat_pattern'] == 'none':
        return None

    root_id = get_repeat_root_id(cursor, current_user_id, original_task['id'])
    if root_id is None:
        root_id = original_task['id'] if original_task['repeat_parent_id'] is None else original_task['repeat_parent_id']

    cursor.execute('''
        SELECT MAX(due_date) as latest_due FROM tasks
        WHERE user_id = ? AND (id = ? OR repeat_parent_id = ?)
        AND due_date IS NOT NULL
    ''', (current_user_id, root_id, root_id))
    latest_row = cursor.fetchone()
    base_date = latest_row['latest_due'] if latest_row and latest_row['latest_due'] else original_task['due_date']
    next_due_date = calculate_next_repeat_date(base_date, original_task['repeat_pattern'])

    source_id = root_id if root_id else original_task['id']
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (source_id, current_user_id))
    source_task = cursor.fetchone() or original_task

    cursor.execute(
        'INSERT INTO tasks (user_id, category_id, title, description, priority, due_date, is_pinned, repeat_pattern, repeat_parent_id, completed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)',
        (
            current_user_id,
            source_task['category_id'],
            source_task['title'],
            source_task['description'],
            source_task['priority'],
            next_due_date,
            source_task['is_pinned'],
            source_task['repeat_pattern'],
            root_id,
        )
    )
    new_task_id = cursor.lastrowid
    cursor.execute('''
        SELECT tag_id FROM task_tags WHERE task_id = ?
    ''', (source_id,))
    tag_rows = cursor.fetchall()
    for tag_row in tag_rows:
        cursor.execute(
            'INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)',
            (new_task_id, tag_row['tag_id'])
        )
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (new_task_id,))
    return cursor.fetchone()

@app.route('/api/tasks', methods=['POST'])
@token_required
def create_task(current_user_id):
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': '标题不能为空'}), 400
    
    title = data['title']
    description = data.get('description', '')
    category_id = data.get('category_id')
    priority = data.get('priority', 'medium')
    due_date = format_due_date(data.get('due_date'))
    is_pinned = data.get('is_pinned', False)
    repeat_pattern = validate_repeat_pattern(data.get('repeat_pattern', 'none'))
    tag_ids = data.get('tag_ids', [])
    assignee_id = data.get('assignee_id')
    share_team_id = data.get('share_team_id')
    share_with_user_ids = data.get('share_with_user_ids', [])
    share_can_edit = data.get('share_can_edit', False)
    
    if priority not in ['high', 'medium', 'low']:
        priority = 'medium'
    
    if category_id is not None:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
        category = cursor.fetchone()
        conn.close()
        if not category:
            return jsonify({'error': '分类不存在'}), 404
    
    if assignee_id is not None:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (assignee_id,))
        user = cursor.fetchone()
        conn.close()
        if not user:
            return jsonify({'error': '被分配用户不存在'}), 404
    
    conn = get_db()
    cursor = conn.cursor()
    
    for tag_id in tag_ids:
        cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
        tag = cursor.fetchone()
        if not tag:
            conn.close()
            return jsonify({'error': f'标签 ID {tag_id} 不存在'}), 404
    
    if share_team_id is not None:
        cursor.execute('''
            SELECT tm.* FROM team_members tm
            WHERE tm.team_id = ? AND tm.user_id = ?
        ''', (share_team_id, current_user_id))
        team_member = cursor.fetchone()
        if team_member is None:
            conn.close()
            return jsonify({'error': '您不是该团队成员，无法与该团队共享'}), 403
    
    for shared_uid in share_with_user_ids:
        cursor.execute('SELECT * FROM users WHERE id = ?', (shared_uid,))
        target_user = cursor.fetchone()
        if target_user is None:
            conn.close()
            return jsonify({'error': f'目标用户 ID {shared_uid} 不存在'}), 404
    
    cursor.execute(
        'INSERT INTO tasks (user_id, category_id, title, description, priority, due_date, is_pinned, repeat_pattern, assignee_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (current_user_id, category_id, title, description, priority, due_date, is_pinned, repeat_pattern, assignee_id)
    )
    conn.commit()
    task_id = cursor.lastrowid
    
    for tag_id in tag_ids:
        cursor.execute(
            'INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)',
            (task_id, tag_id)
        )
    conn.commit()
    
    if share_team_id is not None:
        cursor.execute(
            'INSERT INTO task_shares (task_id, team_id, can_edit) VALUES (?, ?, ?)',
            (task_id, share_team_id, 1 if share_can_edit else 0)
        )
        conn.commit()
    
    for shared_uid in share_with_user_ids:
        cursor.execute(
            'INSERT INTO task_shares (task_id, shared_with_user_id, can_edit) VALUES (?, ?, ?)',
            (task_id, shared_uid, 1 if share_can_edit else 0)
        )
    conn.commit()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    category = None
    if task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], current_user_id))
        category = cursor.fetchone()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (task['id'], current_user_id))
    tags = cursor.fetchall()
    
    cursor.execute('''
        SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
    ''', (task['id'],))
    attachments = cursor.fetchall()
    
    assignee = None
    if task['assignee_id']:
        cursor.execute('SELECT * FROM users WHERE id = ?', (task['assignee_id'],))
        assignee = cursor.fetchone()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (current_user_id,))
    creator = cursor.fetchone()
    
    conn.close()
    return jsonify(task_to_dict(task, category, tags, attachments, assignee, creator)), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    
    if task is None:
        cursor.execute('''
            SELECT t.* FROM tasks t
            INNER JOIN task_shares ts ON t.id = ts.task_id
            WHERE t.id = ? AND ts.shared_with_user_id = ? AND ts.can_edit = 1
        ''', (task_id, current_user_id))
        editable_shared = cursor.fetchone()
        
        cursor.execute('SELECT * FROM tasks WHERE id = ? AND assignee_id = ?', (task_id, current_user_id))
        assigned_task = cursor.fetchone()
        
        task = editable_shared or assigned_task
        if task is None:
            conn.close()
            return jsonify({'error': '任务不存在或您无权限编辑'}), 404
    
    data = request.get_json()
    title = data.get('title', task['title'])
    description = data.get('description', task['description'])
    completed = data.get('completed', task['completed'])
    category_id = data.get('category_id', task['category_id'])
    priority = data.get('priority', task['priority'])
    is_pinned = data.get('is_pinned', task['is_pinned'])
    repeat_pattern = validate_repeat_pattern(data.get('repeat_pattern', task['repeat_pattern'] or 'none'))
    assignee_id = data.get('assignee_id', task['assignee_id'] if 'assignee_id' in task.keys() else None)
    
    if 'due_date' in data:
        due_date = format_due_date(data['due_date'])
    else:
        due_date = task['due_date']
    
    if priority not in ['high', 'medium', 'low']:
        priority = task['priority'] or 'medium'
    
    if category_id is not None and category_id != task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, task['user_id']))
        category = cursor.fetchone()
        if not category:
            conn.close()
            return jsonify({'error': '分类不存在'}), 404
    
    if assignee_id is not None and assignee_id != (task['assignee_id'] if 'assignee_id' in task.keys() else None):
        cursor.execute('SELECT * FROM users WHERE id = ?', (assignee_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': '被分配用户不存在'}), 404
    
    old_completed = bool(task['completed'])
    new_completed = bool(completed)
    if new_completed and not old_completed:
        completed_at_val = format_datetime(datetime.now())
    elif not new_completed and old_completed:
        completed_at_val = None
    else:
        completed_at_val = task['completed_at']
    
    cursor.execute(
        'UPDATE tasks SET title = ?, description = ?, completed = ?, completed_at = ?, category_id = ?, priority = ?, due_date = ?, is_pinned = ?, repeat_pattern = ?, updated_at = ?, assignee_id = ? WHERE id = ?',
        (title, description, completed, completed_at_val, category_id, priority, due_date, is_pinned, repeat_pattern, format_datetime(datetime.now()), assignee_id, task_id)
    )
    conn.commit()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    updated_task = cursor.fetchone()
    
    category = None
    if updated_task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (updated_task['category_id'], updated_task['user_id']))
        category = cursor.fetchone()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (updated_task['id'], updated_task['user_id']))
    tags = cursor.fetchall()
    
    cursor.execute('''
        SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
    ''', (updated_task['id'],))
    attachments = cursor.fetchall()
    
    assignee = None
    if updated_task['assignee_id']:
        cursor.execute('SELECT * FROM users WHERE id = ?', (updated_task['assignee_id'],))
        assignee = cursor.fetchone()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (updated_task['user_id'],))
    creator = cursor.fetchone()
    
    conn.close()
    return jsonify(task_to_dict(updated_task, category, tags, attachments, assignee, creator))

@app.route('/api/tasks/<int:task_id>/toggle', methods=['PUT'])
@token_required
def toggle_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    old_completed = bool(task['completed'])
    new_completed = not old_completed
    
    completed_at_val = format_datetime(datetime.now()) if new_completed else None
    cursor.execute(
        'UPDATE tasks SET completed = ?, completed_at = ?, updated_at = ? WHERE id = ?',
        (new_completed, completed_at_val, format_datetime(datetime.now()), task_id)
    )
    conn.commit()
    
    if new_completed and task['repeat_pattern'] and task['repeat_pattern'] != 'none':
        root_id = get_repeat_root_id(cursor, current_user_id, task['id'])
        if not series_has_active_next(cursor, current_user_id, root_id):
            create_next_repeat_task(cursor, task, current_user_id)
            conn.commit()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    updated_task = cursor.fetchone()
    
    category = None
    if updated_task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (updated_task['category_id'], current_user_id))
        category = cursor.fetchone()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (updated_task['id'], current_user_id))
    tags = cursor.fetchall()
    
    cursor.execute('''
        SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
    ''', (updated_task['id'],))
    attachments = cursor.fetchall()
    
    conn.close()
    return jsonify(task_to_dict(updated_task, category, tags, attachments))

@app.route('/api/tasks/<int:task_id>/pin', methods=['PUT'])
@token_required
def toggle_pin_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    new_pinned = not bool(task['is_pinned'])
    cursor.execute(
        'UPDATE tasks SET is_pinned = ?, updated_at = ? WHERE id = ?',
        (new_pinned, format_datetime(datetime.now()), task_id)
    )
    conn.commit()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    updated_task = cursor.fetchone()
    
    category = None
    if updated_task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (updated_task['category_id'], current_user_id))
        category = cursor.fetchone()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (updated_task['id'], current_user_id))
    tags = cursor.fetchall()
    
    cursor.execute('''
        SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
    ''', (updated_task['id'],))
    attachments = cursor.fetchall()
    
    conn.close()
    return jsonify(task_to_dict(updated_task, category, tags, attachments))

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    cursor.execute('SELECT * FROM attachments WHERE task_id = ?', (task_id,))
    attachments = cursor.fetchall()
    for att in attachments:
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], att['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
    
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '任务删除成功'})

@app.route('/api/tasks/<int:task_id>/attachments', methods=['POST'])
@token_required
def upload_attachment(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    if 'file' not in request.files:
        conn.close()
        return jsonify({'error': '未找到文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        conn.close()
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        conn.close()
        return jsonify({'error': '不支持的文件类型'}), 400
    
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}{'.' + ext if ext else ''}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    mime_type = file.mimetype
    
    cursor.execute(
        'INSERT INTO attachments (task_id, filename, original_filename, file_path, file_size, mime_type) VALUES (?, ?, ?, ?, ?, ?)',
        (task_id, unique_filename, original_filename, file_path, file_size, mime_type)
    )
    conn.commit()
    attachment_id = cursor.lastrowid
    
    cursor.execute('SELECT * FROM attachments WHERE id = ?', (attachment_id,))
    attachment = cursor.fetchone()
    
    cursor.execute('SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC', (task_id,))
    all_attachments = cursor.fetchall()
    
    conn.close()
    return jsonify({
        'attachment': attachment_to_dict(attachment),
        'attachments': [attachment_to_dict(a) for a in all_attachments]
    }), 201

@app.route('/api/tasks/attachments/<int:attachment_id>', methods=['GET'])
@token_required
def download_attachment(current_user_id, attachment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.* FROM attachments a
        INNER JOIN tasks t ON a.task_id = t.id
        WHERE a.id = ? AND t.user_id = ?
    ''', (attachment_id, current_user_id))
    attachment = cursor.fetchone()
    conn.close()
    
    if attachment is None:
        return jsonify({'error': '附件不存在'}), 404
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['filename'])
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        attachment['filename'],
        as_attachment=False,
        download_name=attachment['original_filename']
    )

@app.route('/api/tasks/attachments/<int:attachment_id>/download', methods=['GET'])
@token_required
def download_attachment_as_file(current_user_id, attachment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.* FROM attachments a
        INNER JOIN tasks t ON a.task_id = t.id
        WHERE a.id = ? AND t.user_id = ?
    ''', (attachment_id, current_user_id))
    attachment = cursor.fetchone()
    conn.close()
    
    if attachment is None:
        return jsonify({'error': '附件不存在'}), 404
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['filename'])
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        attachment['filename'],
        as_attachment=True,
        download_name=attachment['original_filename']
    )

@app.route('/api/tasks/attachments/<int:attachment_id>', methods=['DELETE'])
@token_required
def delete_attachment(current_user_id, attachment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.* FROM attachments a
        INNER JOIN tasks t ON a.task_id = t.id
        WHERE a.id = ? AND t.user_id = ?
    ''', (attachment_id, current_user_id))
    attachment = cursor.fetchone()
    if attachment is None:
        conn.close()
        return jsonify({'error': '附件不存在'}), 404
    
    task_id = attachment['task_id']
    
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    
    cursor.execute('DELETE FROM attachments WHERE id = ?', (attachment_id,))
    conn.commit()
    
    cursor.execute('SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC', (task_id,))
    all_attachments = cursor.fetchall()
    
    conn.close()
    return jsonify({
        'message': '附件删除成功',
        'attachments': [attachment_to_dict(a) for a in all_attachments]
    })

@app.route('/api/categories', methods=['GET'])
@token_required
def get_categories(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories WHERE user_id = ? ORDER BY created_at ASC', (current_user_id,))
    categories = cursor.fetchall()
    conn.close()
    return jsonify([category_to_dict(cat) for cat in categories])

@app.route('/api/categories/<int:category_id>', methods=['GET'])
@token_required
def get_category(current_user_id, category_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
    category = cursor.fetchone()
    conn.close()
    if category is None:
        return jsonify({'error': '分类不存在'}), 404
    return jsonify(category_to_dict(category))

@app.route('/api/categories', methods=['POST'])
@token_required
def create_category(current_user_id):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': '分类名称不能为空'}), 400
    
    name = data['name'].strip()
    color = data.get('color', '#667eea')
    
    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM categories WHERE user_id = ? AND name = ?', (current_user_id, name))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({'error': '分类名称已存在'}), 400
    
    cursor.execute(
        'INSERT INTO categories (user_id, name, color) VALUES (?, ?, ?)',
        (current_user_id, name, color)
    )
    conn.commit()
    category_id = cursor.lastrowid
    cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    category = cursor.fetchone()
    conn.close()
    return jsonify(category_to_dict(category)), 201

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@token_required
def update_category(current_user_id, category_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
    category = cursor.fetchone()
    if category is None:
        conn.close()
        return jsonify({'error': '分类不存在'}), 404
    
    data = request.get_json()
    name = data.get('name', category['name']).strip()
    color = data.get('color', category['color'])
    
    if not name:
        conn.close()
        return jsonify({'error': '分类名称不能为空'}), 400
    
    if name != category['name']:
        cursor.execute('SELECT * FROM categories WHERE user_id = ? AND name = ? AND id != ?', (current_user_id, name, category_id))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({'error': '分类名称已存在'}), 400
    
    cursor.execute(
        'UPDATE categories SET name = ?, color = ? WHERE id = ?',
        (name, color, category_id)
    )
    conn.commit()
    cursor.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    updated_category = cursor.fetchone()
    conn.close()
    return jsonify(category_to_dict(updated_category))

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@token_required
def delete_category(current_user_id, category_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
    category = cursor.fetchone()
    if category is None:
        conn.close()
        return jsonify({'error': '分类不存在'}), 404
    
    cursor.execute('UPDATE tasks SET category_id = NULL WHERE category_id = ? AND user_id = ?', (category_id, current_user_id))
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '分类删除成功'})

@app.route('/api/tags', methods=['GET'])
@token_required
def get_tags(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, COUNT(tt.task_id) as task_count
        FROM tags t
        LEFT JOIN task_tags tt ON t.id = tt.tag_id
        WHERE t.user_id = ?
        GROUP BY t.id
        ORDER BY t.created_at ASC
    ''', (current_user_id,))
    tags = cursor.fetchall()
    conn.close()
    result = []
    for tag in tags:
        tag_dict = tag_to_dict(tag)
        tag_dict['task_count'] = tag['task_count']
        result.append(tag_dict)
    return jsonify(result)

@app.route('/api/tags/<int:tag_id>', methods=['GET'])
@token_required
def get_tag(current_user_id, tag_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
    tag = cursor.fetchone()
    conn.close()
    if tag is None:
        return jsonify({'error': '标签不存在'}), 404
    return jsonify(tag_to_dict(tag))

@app.route('/api/tags', methods=['POST'])
@token_required
def create_tag(current_user_id):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': '标签名称不能为空'}), 400
    
    name = data['name'].strip()
    color = data.get('color', '#667eea')
    
    if not name:
        return jsonify({'error': '标签名称不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tags WHERE user_id = ? AND name = ?', (current_user_id, name))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({'error': '标签名称已存在'}), 400
    
    cursor.execute(
        'INSERT INTO tags (user_id, name, color) VALUES (?, ?, ?)',
        (current_user_id, name, color)
    )
    conn.commit()
    tag_id = cursor.lastrowid
    cursor.execute('SELECT t.*, 0 as task_count FROM tags t WHERE t.id = ?', (tag_id,))
    tag = cursor.fetchone()
    conn.close()
    tag_dict = tag_to_dict(tag)
    tag_dict['task_count'] = tag['task_count']
    return jsonify(tag_dict), 201

@app.route('/api/tags/<int:tag_id>', methods=['PUT'])
@token_required
def update_tag(current_user_id, tag_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
    tag = cursor.fetchone()
    if tag is None:
        conn.close()
        return jsonify({'error': '标签不存在'}), 404
    
    data = request.get_json()
    name = data.get('name', tag['name']).strip()
    color = data.get('color', tag['color'])
    
    if not name:
        conn.close()
        return jsonify({'error': '标签名称不能为空'}), 400
    
    if name != tag['name']:
        cursor.execute('SELECT * FROM tags WHERE user_id = ? AND name = ? AND id != ?', (current_user_id, name, tag_id))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({'error': '标签名称已存在'}), 400
    
    cursor.execute(
        'UPDATE tags SET name = ?, color = ? WHERE id = ?',
        (name, color, tag_id)
    )
    conn.commit()
    cursor.execute('''
        SELECT t.*, COUNT(tt.task_id) as task_count
        FROM tags t
        LEFT JOIN task_tags tt ON t.id = tt.tag_id
        WHERE t.id = ?
        GROUP BY t.id
    ''', (tag_id,))
    updated_tag = cursor.fetchone()
    conn.close()
    tag_dict = tag_to_dict(updated_tag)
    tag_dict['task_count'] = updated_tag['task_count']
    return jsonify(tag_dict)

@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def delete_tag(current_user_id, tag_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
    tag = cursor.fetchone()
    if tag is None:
        conn.close()
        return jsonify({'error': '标签不存在'}), 404
    
    cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '标签删除成功'})

@app.route('/api/tasks/<int:task_id>/tags', methods=['POST'])
@token_required
def add_tag_to_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    data = request.get_json()
    tag_id = data.get('tag_id')
    if tag_id is None:
        conn.close()
        return jsonify({'error': '标签ID不能为空'}), 400
    
    cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
    tag = cursor.fetchone()
    if tag is None:
        conn.close()
        return jsonify({'error': '标签不存在'}), 404
    
    cursor.execute(
        'INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)',
        (task_id, tag_id)
    )
    conn.commit()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (task_id, current_user_id))
    tags = cursor.fetchall()
    
    conn.close()
    return jsonify([tag_to_dict(tag) for tag in tags])

@app.route('/api/tasks/<int:task_id>/tags/<int:tag_id>', methods=['DELETE'])
@token_required
def remove_tag_from_task(current_user_id, task_id, tag_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
    tag = cursor.fetchone()
    if tag is None:
        conn.close()
        return jsonify({'error': '标签不存在'}), 404
    
    cursor.execute(
        'DELETE FROM task_tags WHERE task_id = ? AND tag_id = ?',
        (task_id, tag_id)
    )
    conn.commit()
    
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (task_id, current_user_id))
    tags = cursor.fetchall()
    
    conn.close()
    return jsonify([tag_to_dict(tag) for tag in tags])

def _process_user_repeat_tasks(cursor, user_id):
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE user_id = ? 
        AND repeat_pattern IS NOT NULL 
        AND repeat_pattern != 'none'
    ''', (user_id,))
    all_repeat_tasks = cursor.fetchall()

    series_map = {}
    for task in all_repeat_tasks:
        root_id = get_repeat_root_id(cursor, user_id, task['id'])
        if root_id is None:
            continue
        if root_id not in series_map:
            series_map[root_id] = []
        series_map[root_id].append(task)

    created_count = 0
    now = datetime.now()

    for root_id, tasks_in_series in series_map.items():
        if series_has_active_next(cursor, user_id, root_id):
            continue

        latest_task = None
        latest_due = None
        for t in tasks_in_series:
            if not t['due_date']:
                continue
            td = parse_datetime(t['due_date'])
            if td is None:
                continue
            if latest_due is None or td > latest_due:
                latest_due = td
                latest_task = t

        if latest_task is None:
            continue

        if latest_due <= now:
            new_task = create_next_repeat_task(cursor, latest_task, user_id)
            if new_task:
                created_count += 1

    return created_count

@app.route('/api/tasks/check-repeat', methods=['POST'])
@token_required
def check_repeat_tasks(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        created_count = _process_user_repeat_tasks(cursor, current_user_id)
        conn.commit()
        return jsonify({
            'message': f'检查完成，创建了 {created_count} 个重复任务',
            'created_count': created_count
        })
    finally:
        conn.close()

_scheduler_stop_event = threading.Event()
_scheduler_thread = None

def _daily_repeat_scheduler_loop():
    while not _scheduler_stop_event.is_set():
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT user_id FROM tasks WHERE repeat_pattern IS NOT NULL AND repeat_pattern != ?', ('none',))
            user_rows = cursor.fetchall()
            total_created = 0
            for row in user_rows:
                created = _process_user_repeat_tasks(cursor, row['user_id'])
                total_created += created
            if total_created > 0:
                conn.commit()
            conn.close()
        except Exception as e:
            try:
                print(f'[daily-repeat-scheduler] error: {e}')
            except Exception:
                pass

        _scheduler_stop_event.wait(24 * 60 * 60)

def start_daily_repeat_scheduler():
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return
    _scheduler_stop_event.clear()
    _scheduler_thread = threading.Thread(target=_daily_repeat_scheduler_loop, daemon=True)
    _scheduler_thread.start()

def stop_daily_repeat_scheduler():
    _scheduler_stop_event.set()

atexit.register(stop_daily_repeat_scheduler)

@app.route('/api/stats', methods=['GET'])
@token_required
def get_stats(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)
    
    week_start = now - timedelta(days=now.weekday())
    week_start = datetime(week_start.year, week_start.month, week_start.day)
    week_end = week_start + timedelta(days=7)
    
    cursor.execute('''
        SELECT COUNT(*) FROM tasks 
        WHERE user_id = ? AND completed = 1 
        AND completed_at >= ? AND completed_at < ?
    ''', (current_user_id, format_datetime(today_start), format_datetime(today_end)))
    today_completed = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM tasks 
        WHERE user_id = ? AND completed = 1 
        AND completed_at >= ? AND completed_at < ?
    ''', (current_user_id, format_datetime(week_start), format_datetime(week_end)))
    week_completed = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (current_user_id,))
    total_tasks = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1', (current_user_id,))
    total_completed = cursor.fetchone()[0]
    
    completion_rate = 0.0
    if total_tasks > 0:
        completion_rate = round((total_completed / total_tasks) * 100, 1)
    
    cursor.execute('''
        SELECT created_at, completed_at FROM tasks 
        WHERE user_id = ? AND completed = 1 
        AND created_at IS NOT NULL AND completed_at IS NOT NULL
    ''', (current_user_id,))
    completed_tasks = cursor.fetchall()
    
    avg_completion_minutes = 0.0
    durations = []
    for row in completed_tasks:
        created = parse_datetime(row['created_at'])
        completed = parse_datetime(row['completed_at'])
        if created and completed:
            duration = (completed - created).total_seconds() / 60
            if duration > 0:
                durations.append(duration)
    
    if durations:
        avg_completion_minutes = round(sum(durations) / len(durations), 1)
    
    daily_trend = []
    for i in range(6, -1, -1):
        day_date = now - timedelta(days=i)
        day_start = datetime(day_date.year, day_date.month, day_date.day)
        day_end = day_start + timedelta(days=1)
        
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE user_id = ? AND completed = 1 
            AND completed_at >= ? AND completed_at < ?
        ''', (current_user_id, format_datetime(day_start), format_datetime(day_end)))
        count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE user_id = ? AND created_at >= ? AND created_at < ?
        ''', (current_user_id, format_datetime(day_start), format_datetime(day_end)))
        created_count = cursor.fetchone()[0]
        
        daily_trend.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'label': day_start.strftime('%m-%d'),
            'completed': count,
            'created': created_count,
        })
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 0', (current_user_id,))
    active_tasks = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM tasks 
        WHERE user_id = ? AND completed = 0 AND due_date IS NOT NULL AND due_date < ?
    ''', (current_user_id, format_datetime(now)))
    overdue_tasks = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'today_completed': today_completed,
        'week_completed': week_completed,
        'total_tasks': total_tasks,
        'total_completed': total_completed,
        'active_tasks': active_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_rate': completion_rate,
        'avg_completion_minutes': avg_completion_minutes,
        'daily_trend': daily_trend,
    })

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/teams', methods=['GET'])
@token_required
def get_teams(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, COUNT(tm.id) as member_count FROM teams t
        INNER JOIN team_members tm ON t.id = tm.team_id
        WHERE tm.user_id = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
    ''', (current_user_id,))
    teams = cursor.fetchall()
    conn.close()
    return jsonify([team_to_dict(team, team['member_count']) for team in teams])

@app.route('/api/teams', methods=['POST'])
@token_required
def create_team(current_user_id):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': '团队名称不能为空'}), 400
    
    name = data['name'].strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'error': '团队名称不能为空'}), 400
    
    invite_token = uuid.uuid4().hex
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO teams (name, description, created_by, invite_token) VALUES (?, ?, ?, ?)',
        (name, description, current_user_id, invite_token)
    )
    team_id = cursor.lastrowid
    
    cursor.execute(
        'INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, ?)',
        (team_id, current_user_id, 'admin')
    )
    conn.commit()
    
    cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
    team = cursor.fetchone()
    conn.close()
    
    return jsonify(team_to_dict(team, 1)), 201

@app.route('/api/teams/<int:team_id>', methods=['GET'])
@token_required
def get_team(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.* FROM teams t
        INNER JOIN team_members tm ON t.id = tm.team_id
        WHERE t.id = ? AND tm.user_id = ?
    ''', (team_id, current_user_id))
    team = cursor.fetchone()
    
    if team is None:
        conn.close()
        return jsonify({'error': '团队不存在或您不是该团队成员'}), 404
    
    cursor.execute('SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?', (team_id,))
    member_count = cursor.fetchone()['cnt']
    
    conn.close()
    return jsonify(team_to_dict(team, member_count))

@app.route('/api/teams/<int:team_id>', methods=['PUT'])
@token_required
def update_team(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ? AND tm.role = ?
    ''', (team_id, current_user_id, 'admin'))
    membership = cursor.fetchone()
    
    if membership is None:
        conn.close()
        return jsonify({'error': '只有管理员可以修改团队信息'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '')
    
    if not name:
        conn.close()
        return jsonify({'error': '团队名称不能为空'}), 400
    
    cursor.execute(
        'UPDATE teams SET name = ?, description = ? WHERE id = ?',
        (name, description, team_id)
    )
    conn.commit()
    
    cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
    team = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?', (team_id,))
    member_count = cursor.fetchone()['cnt']
    
    conn.close()
    return jsonify(team_to_dict(team, member_count))

@app.route('/api/teams/<int:team_id>', methods=['DELETE'])
@token_required
def delete_team(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ? AND tm.role = ?
    ''', (team_id, current_user_id, 'admin'))
    membership = cursor.fetchone()
    
    if membership is None:
        conn.close()
        return jsonify({'error': '只有管理员可以删除团队'}), 403
    
    cursor.execute('DELETE FROM teams WHERE id = ?', (team_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '团队已删除'})

@app.route('/api/teams/<int:team_id>/regenerate-token', methods=['POST'])
@token_required
def regenerate_invite_token(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ? AND tm.role = ?
    ''', (team_id, current_user_id, 'admin'))
    membership = cursor.fetchone()
    
    if membership is None:
        conn.close()
        return jsonify({'error': '只有管理员可以重新生成邀请链接'}), 403
    
    new_token = uuid.uuid4().hex
    cursor.execute('UPDATE teams SET invite_token = ? WHERE id = ?', (new_token, team_id))
    conn.commit()
    
    cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
    team = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?', (team_id,))
    member_count = cursor.fetchone()['cnt']
    
    conn.close()
    return jsonify(team_to_dict(team, member_count))

@app.route('/api/teams/<int:team_id>/members', methods=['GET'])
@token_required
def get_team_members(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.team_id IN (
            SELECT team_id FROM team_members WHERE user_id = ?
        )
    ''', (team_id, current_user_id))
    members = cursor.fetchall()
    
    result = []
    for member in members:
        cursor.execute('SELECT * FROM users WHERE id = ?', (member['user_id'],))
        user = cursor.fetchone()
        result.append(team_member_to_dict(member, user))
    
    conn.close()
    return jsonify(result)

@app.route('/api/teams/<int:team_id>/members/<int:member_user_id>', methods=['PUT'])
@token_required
def update_team_member_role(current_user_id, team_id, member_user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ? AND tm.role = ?
    ''', (team_id, current_user_id, 'admin'))
    admin_membership = cursor.fetchone()
    
    if admin_membership is None:
        conn.close()
        return jsonify({'error': '只有管理员可以修改成员角色'}), 403
    
    data = request.get_json()
    role = data.get('role', 'member')
    
    if role not in VALID_TEAM_ROLES:
        conn.close()
        return jsonify({'error': '无效的角色'}), 400
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ?
    ''', (team_id, member_user_id))
    member = cursor.fetchone()
    
    if member is None:
        conn.close()
        return jsonify({'error': '该用户不是团队成员'}), 404
    
    cursor.execute(
        'UPDATE team_members SET role = ? WHERE team_id = ? AND user_id = ?',
        (role, team_id, member_user_id)
    )
    conn.commit()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ?
    ''', (team_id, member_user_id))
    updated_member = cursor.fetchone()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (member_user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return jsonify(team_member_to_dict(updated_member, user))

@app.route('/api/teams/<int:team_id>/members/<int:member_user_id>', methods=['DELETE'])
@token_required
def remove_team_member(current_user_id, team_id, member_user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ?
    ''', (team_id, current_user_id))
    current_membership = cursor.fetchone()
    
    if current_membership is None:
        conn.close()
        return jsonify({'error': '您不是该团队成员'}), 403
    
    is_admin = current_membership['role'] == 'admin'
    is_self = member_user_id == current_user_id
    
    if not is_admin and not is_self:
        conn.close()
        return jsonify({'error': '只有管理员可以移除其他成员'}), 403
    
    if is_admin and not is_self:
        cursor.execute('''
            SELECT tm.* FROM team_members tm
            WHERE tm.team_id = ? AND tm.user_id = ?
        ''', (team_id, member_user_id))
        target_member = cursor.fetchone()
        if target_member and target_member['role'] == 'admin':
            cursor.execute('SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ? AND role = ?', (team_id, 'admin'))
            admin_count = cursor.fetchone()['cnt']
            if admin_count <= 1:
                conn.close()
                return jsonify({'error': '至少需要保留一名管理员'}), 400
    
    cursor.execute('DELETE FROM team_members WHERE team_id = ? AND user_id = ?', (team_id, member_user_id))
    conn.commit()
    conn.close()
    return jsonify({'message': '成员已移除'})

@app.route('/api/teams/<int:team_id>/invitations', methods=['POST'])
@token_required
def create_invitation(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ? AND tm.role = ?
    ''', (team_id, current_user_id, 'admin'))
    admin_membership = cursor.fetchone()
    
    if admin_membership is None:
        conn.close()
        return jsonify({'error': '只有管理员可以发送邀请'}), 403
    
    data = request.get_json()
    email = data.get('email', '').strip()
    
    if not email:
        conn.close()
        return jsonify({'error': '邮箱不能为空'}), 400
    
    invite_token = uuid.uuid4().hex
    expires_at = format_datetime(datetime.now() + timedelta(days=7))
    
    cursor.execute(
        'INSERT INTO team_invitations (team_id, email, invited_by, token, expires_at) VALUES (?, ?, ?, ?, ?)',
        (team_id, email, current_user_id, invite_token, expires_at)
    )
    conn.commit()
    
    invitation_id = cursor.lastrowid
    cursor.execute('SELECT * FROM team_invitations WHERE id = ?', (invitation_id,))
    invitation = cursor.fetchone()
    
    conn.close()
    return jsonify({
        'id': invitation['id'],
        'team_id': invitation['team_id'],
        'email': invitation['email'],
        'token': invitation['token'],
        'expires_at': invitation['expires_at'],
        'created_at': invitation['created_at']
    }), 201

@app.route('/api/invitations/<token>', methods=['GET'])
def get_invitation(token):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ti.*, t.name as team_name FROM team_invitations ti
        INNER JOIN teams t ON ti.team_id = t.id
        WHERE ti.token = ?
    ''', (token,))
    invitation = cursor.fetchone()
    
    if invitation is None:
        conn.close()
        return jsonify({'error': '邀请链接无效'}), 404
    
    if invitation['status'] != 'pending':
        conn.close()
        return jsonify({'error': '该邀请已被使用或已过期'}), 400
    
    expires_at = parse_datetime(invitation['expires_at'])
    if expires_at and expires_at < datetime.now():
        conn.close()
        return jsonify({'error': '该邀请已过期'}), 400
    
    conn.close()
    return jsonify({
        'team_id': invitation['team_id'],
        'team_name': invitation['team_name'],
        'email': invitation['email'],
        'expires_at': invitation['expires_at']
    })

@app.route('/api/invitations/<token>/accept', methods=['POST'])
@token_required
def accept_invitation(current_user_id, token):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM team_invitations WHERE token = ?', (token,))
    invitation = cursor.fetchone()
    
    if invitation is None:
        conn.close()
        return jsonify({'error': '邀请链接无效'}), 404
    
    if invitation['status'] != 'pending':
        conn.close()
        return jsonify({'error': '该邀请已被使用或已过期'}), 400
    
    expires_at = parse_datetime(invitation['expires_at'])
    if expires_at and expires_at < datetime.now():
        conn.close()
        return jsonify({'error': '该邀请已过期'}), 400
    
    cursor.execute('''
        SELECT * FROM team_members WHERE team_id = ? AND user_id = ?
    ''', (invitation['team_id'], current_user_id))
    existing_member = cursor.fetchone()
    
    if existing_member:
        cursor.execute('UPDATE team_invitations SET status = ? WHERE id = ?', ('accepted', invitation['id']))
        conn.commit()
        conn.close()
        return jsonify({'message': '您已经是该团队成员'})
    
    cursor.execute(
        'INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, ?)',
        (invitation['team_id'], current_user_id, 'member')
    )
    cursor.execute('UPDATE team_invitations SET status = ? WHERE id = ?', ('accepted', invitation['id']))
    conn.commit()
    
    cursor.execute('SELECT * FROM teams WHERE id = ?', (invitation['team_id'],))
    team = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?', (invitation['team_id'],))
    member_count = cursor.fetchone()['cnt']
    
    conn.close()
    return jsonify(team_to_dict(team, member_count))

@app.route('/api/teams/join/<invite_token>', methods=['POST'])
@token_required
def join_team_by_token(current_user_id, invite_token):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM teams WHERE invite_token = ?', (invite_token,))
    team = cursor.fetchone()
    
    if team is None:
        conn.close()
        return jsonify({'error': '邀请链接无效'}), 404
    
    cursor.execute('''
        SELECT * FROM team_members WHERE team_id = ? AND user_id = ?
    ''', (team['id'], current_user_id))
    existing_member = cursor.fetchone()
    
    if existing_member:
        conn.close()
        return jsonify({'message': '您已经是该团队成员'})
    
    cursor.execute(
        'INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, ?)',
        (team['id'], current_user_id, 'member')
    )
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) as cnt FROM team_members WHERE team_id = ?', (team['id'],))
    member_count = cursor.fetchone()['cnt']
    
    conn.close()
    return jsonify(team_to_dict(team, member_count))

@app.route('/api/tasks/<int:task_id>/shares', methods=['GET'])
@token_required
def get_task_shares(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    
    if task is None:
        cursor.execute('''
            SELECT ts.* FROM task_shares ts
            INNER JOIN tasks t ON ts.task_id = t.id
            WHERE ts.task_id = ? AND ts.shared_with_user_id = ? AND ts.can_edit = 1
        ''', (task_id, current_user_id))
        share = cursor.fetchone()
        if share is None:
            conn.close()
            return jsonify({'error': '任务不存在或您无权限'}), 404
    
    cursor.execute('''
        SELECT ts.*, u.username as shared_username, t.name as team_name
        FROM task_shares ts
        LEFT JOIN users u ON ts.shared_with_user_id = u.id
        LEFT JOIN teams t ON ts.team_id = t.id
        WHERE ts.task_id = ?
    ''', (task_id,))
    shares = cursor.fetchall()
    
    result = []
    for share in shares:
        share_dict = task_share_to_dict(share)
        if share['shared_username']:
            share_dict['shared_with_username'] = share['shared_username']
        if share['team_name']:
            share_dict['team_name'] = share['team_name']
        result.append(share_dict)
    
    conn.close()
    return jsonify(result)

@app.route('/api/tasks/<int:task_id>/shares', methods=['POST'])
@token_required
def create_task_share(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在或您不是创建者'}), 404
    
    data = request.get_json()
    team_id = data.get('team_id')
    shared_with_user_id = data.get('shared_with_user_id')
    can_edit = data.get('can_edit', False)
    
    if team_id is None and shared_with_user_id is None:
        conn.close()
        return jsonify({'error': '必须指定团队或用户'}), 400
    
    if team_id is not None:
        cursor.execute('''
            SELECT tm.* FROM team_members tm
            WHERE tm.team_id = ? AND tm.user_id = ?
        ''', (team_id, current_user_id))
        team_member = cursor.fetchone()
        if team_member is None:
            conn.close()
            return jsonify({'error': '您不是该团队成员'}), 403
    
    if shared_with_user_id is not None:
        cursor.execute('SELECT * FROM users WHERE id = ?', (shared_with_user_id,))
        target_user = cursor.fetchone()
        if target_user is None:
            conn.close()
            return jsonify({'error': '目标用户不存在'}), 404
    
    cursor.execute(
        'INSERT INTO task_shares (task_id, team_id, shared_with_user_id, can_edit) VALUES (?, ?, ?, ?)',
        (task_id, team_id, shared_with_user_id, 1 if can_edit else 0)
    )
    conn.commit()
    share_id = cursor.lastrowid
    
    cursor.execute('SELECT * FROM task_shares WHERE id = ?', (share_id,))
    share = cursor.fetchone()
    
    conn.close()
    return jsonify(task_share_to_dict(share)), 201

@app.route('/api/tasks/shares/<int:share_id>', methods=['DELETE'])
@token_required
def delete_task_share(current_user_id, share_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ts.* FROM task_shares ts
        INNER JOIN tasks t ON ts.task_id = t.id
        WHERE ts.id = ? AND t.user_id = ?
    ''', (share_id, current_user_id))
    share = cursor.fetchone()
    
    if share is None:
        conn.close()
        return jsonify({'error': '共享不存在或您无权限删除'}), 404
    
    cursor.execute('DELETE FROM task_shares WHERE id = ?', (share_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '共享已删除'})

@app.route('/api/tasks/assigned', methods=['GET'])
@token_required
def get_assigned_tasks(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT t.* FROM tasks t
        WHERE t.assignee_id = ?
        ORDER BY t.is_pinned DESC, t.created_at DESC
    ''', (current_user_id,))
    tasks = cursor.fetchall()
    
    result = []
    for task in tasks:
        category = None
        if task['category_id']:
            cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], task['user_id']))
            category = cursor.fetchone()
        cursor.execute('''
            SELECT t.* FROM tags t
            INNER JOIN task_tags tt ON t.id = tt.tag_id
            WHERE tt.task_id = ? AND t.user_id = ?
            ORDER BY t.created_at ASC
        ''', (task['id'], task['user_id']))
        tags = cursor.fetchall()
        cursor.execute('''
            SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
        ''', (task['id'],))
        attachments = cursor.fetchall()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (task['user_id'],))
        creator = cursor.fetchone()
        
        result.append(task_to_dict(task, category, tags, attachments, None, creator))
    
    conn.close()
    return jsonify(result)

@app.route('/api/tasks/shared', methods=['GET'])
@token_required
def get_shared_tasks(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT t.* FROM tasks t
        INNER JOIN task_shares ts ON t.id = ts.task_id
        LEFT JOIN team_members tm ON ts.team_id = tm.team_id AND tm.user_id = ?
        WHERE (ts.shared_with_user_id = ? OR tm.user_id IS NOT NULL)
        AND t.user_id != ?
        ORDER BY t.is_pinned DESC, t.created_at DESC
    ''', (current_user_id, current_user_id, current_user_id))
    tasks = cursor.fetchall()
    
    result = []
    for task in tasks:
        category = None
        if task['category_id']:
            cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], task['user_id']))
            category = cursor.fetchone()
        cursor.execute('''
            SELECT t.* FROM tags t
            INNER JOIN task_tags tt ON t.id = tt.tag_id
            WHERE tt.task_id = ? AND t.user_id = ?
            ORDER BY t.created_at ASC
        ''', (task['id'], task['user_id']))
        tags = cursor.fetchall()
        cursor.execute('''
            SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
        ''', (task['id'],))
        attachments = cursor.fetchall()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (task['user_id'],))
        creator = cursor.fetchone()
        
        assignee = None
        if task['assignee_id']:
            cursor.execute('SELECT * FROM users WHERE id = ?', (task['assignee_id'],))
            assignee = cursor.fetchone()
        
        result.append(task_to_dict(task, category, tags, attachments, assignee, creator))
    
    conn.close()
    return jsonify(result)

@app.route('/api/teams/<int:team_id>/tasks', methods=['GET'])
@token_required
def get_team_tasks(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ?
    ''', (team_id, current_user_id))
    membership = cursor.fetchone()
    
    if membership is None:
        conn.close()
        return jsonify({'error': '您不是该团队成员'}), 403
    
    cursor.execute('''
        SELECT DISTINCT t.* FROM tasks t
        INNER JOIN task_shares ts ON t.id = ts.task_id
        WHERE ts.team_id = ?
        UNION
        SELECT DISTINCT t.* FROM tasks t
        WHERE t.user_id IN (SELECT user_id FROM team_members WHERE team_id = ?)
        ORDER BY is_pinned DESC, created_at DESC
    ''', (team_id, team_id))
    tasks = cursor.fetchall()
    
    result = []
    for task in tasks:
        category = None
        if task['category_id']:
            cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], task['user_id']))
            category = cursor.fetchone()
        cursor.execute('''
            SELECT t.* FROM tags t
            INNER JOIN task_tags tt ON t.id = tt.tag_id
            WHERE tt.task_id = ? AND t.user_id = ?
            ORDER BY t.created_at ASC
        ''', (task['id'], task['user_id']))
        tags = cursor.fetchall()
        cursor.execute('''
            SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
        ''', (task['id'],))
        attachments = cursor.fetchall()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (task['user_id'],))
        creator = cursor.fetchone()
        
        assignee = None
        if task['assignee_id']:
            cursor.execute('SELECT * FROM users WHERE id = ?', (task['assignee_id'],))
            assignee = cursor.fetchone()
        
        result.append(task_to_dict(task, category, tags, attachments, assignee, creator))
    
    conn.close()
    return jsonify(result)

@app.route('/api/teams/<int:team_id>/users', methods=['GET'])
@token_required
def get_team_users(current_user_id, team_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tm.* FROM team_members tm
        WHERE tm.team_id = ? AND tm.user_id = ?
    ''', (team_id, current_user_id))
    membership = cursor.fetchone()
    
    if membership is None:
        conn.close()
        return jsonify({'error': '您不是该团队成员'}), 403
    
    cursor.execute('''
        SELECT u.id, u.username, u.created_at, tm.role
        FROM users u
        INNER JOIN team_members tm ON u.id = tm.user_id
        WHERE tm.team_id = ?
        ORDER BY u.username ASC
    ''', (team_id,))
    users = cursor.fetchall()
    
    conn.close()
    return jsonify([{
        'id': user['id'],
        'username': user['username'],
        'created_at': user['created_at'],
        'role': user['role']
    } for user in users])


def _user_can_access_task(cursor, user_id, task_id):
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    if task is None:
        return None
    if task['user_id'] == user_id:
        return task
    if task['assignee_id'] == user_id:
        return task
    cursor.execute('''
        SELECT 1 FROM task_shares
        WHERE task_id = ? AND (shared_with_user_id = ? OR team_id IN (
            SELECT team_id FROM team_members WHERE user_id = ?
        ))
    ''', (task_id, user_id, user_id))
    shared = cursor.fetchone()
    if shared:
        return task
    return None


@app.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
@token_required
def get_task_comments(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()

    task = _user_can_access_task(cursor, current_user_id, task_id)
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在或您无权限访问'}), 404

    cursor.execute('''
        SELECT c.* FROM task_comments c
        WHERE c.task_id = ?
        ORDER BY c.created_at ASC
    ''', (task_id,))
    comments = cursor.fetchall()

    result = []
    for comment in comments:
        cursor.execute('SELECT * FROM users WHERE id = ?', (comment['user_id'],))
        user = cursor.fetchone()
        cursor.execute('SELECT COUNT(*) as cnt FROM comment_likes WHERE comment_id = ?', (comment['id'],))
        like_count = cursor.fetchone()['cnt']
        cursor.execute('SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?', (comment['id'], current_user_id))
        is_liked = cursor.fetchone() is not None
        reply_user = None
        if comment['parent_id']:
            cursor.execute('SELECT user_id FROM task_comments WHERE id = ?', (comment['parent_id'],))
            parent_comment = cursor.fetchone()
            if parent_comment:
                cursor.execute('SELECT * FROM users WHERE id = ?', (parent_comment['user_id'],))
                reply_user = cursor.fetchone()
        result.append(comment_to_dict(comment, user, like_count, is_liked, reply_user))

    conn.close()
    return jsonify(result)


@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@token_required
def create_task_comment(current_user_id, task_id):
    data = request.get_json()
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({'error': '评论内容不能为空'}), 400

    content = data['content'].strip()
    parent_id = data.get('parent_id')

    if len(content) > 2000:
        return jsonify({'error': '评论内容不能超过 2000 个字符'}), 400

    conn = get_db()
    cursor = conn.cursor()

    task = _user_can_access_task(cursor, current_user_id, task_id)
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在或您无权限访问'}), 404

    if parent_id is not None:
        cursor.execute('SELECT * FROM task_comments WHERE id = ? AND task_id = ?', (parent_id, task_id))
        parent_comment = cursor.fetchone()
        if parent_comment is None:
            conn.close()
            return jsonify({'error': '回复的评论不存在'}), 404

    cursor.execute(
        'INSERT INTO task_comments (task_id, user_id, parent_id, content) VALUES (?, ?, ?, ?)',
        (task_id, current_user_id, parent_id, content)
    )
    conn.commit()
    comment_id = cursor.lastrowid

    cursor.execute('SELECT * FROM task_comments WHERE id = ?', (comment_id,))
    comment = cursor.fetchone()

    cursor.execute('SELECT * FROM users WHERE id = ?', (current_user_id,))
    user = cursor.fetchone()

    reply_user = None
    if comment['parent_id']:
        cursor.execute('SELECT user_id FROM task_comments WHERE id = ?', (comment['parent_id'],))
        parent_comment = cursor.fetchone()
        if parent_comment:
            cursor.execute('SELECT * FROM users WHERE id = ?', (parent_comment['user_id'],))
            reply_user = cursor.fetchone()

    conn.close()
    return jsonify(comment_to_dict(comment, user, 0, False, reply_user)), 201


@app.route('/api/comments/<int:comment_id>', methods=['PUT'])
@token_required
def update_comment(current_user_id, comment_id):
    data = request.get_json()
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({'error': '评论内容不能为空'}), 400

    content = data['content'].strip()
    if len(content) > 2000:
        return jsonify({'error': '评论内容不能超过 2000 个字符'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM task_comments WHERE id = ?', (comment_id,))
    comment = cursor.fetchone()
    if comment is None:
        conn.close()
        return jsonify({'error': '评论不存在'}), 404

    if comment['user_id'] != current_user_id:
        conn.close()
        return jsonify({'error': '您只能编辑自己的评论'}), 403

    cursor.execute(
        'UPDATE task_comments SET content = ?, updated_at = ? WHERE id = ?',
        (content, format_datetime(datetime.now()), comment_id)
    )
    conn.commit()

    cursor.execute('SELECT * FROM task_comments WHERE id = ?', (comment_id,))
    updated_comment = cursor.fetchone()

    cursor.execute('SELECT * FROM users WHERE id = ?', (comment['user_id'],))
    user = cursor.fetchone()

    cursor.execute('SELECT COUNT(*) as cnt FROM comment_likes WHERE comment_id = ?', (comment_id,))
    like_count = cursor.fetchone()['cnt']

    cursor.execute('SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?', (comment_id, current_user_id))
    is_liked = cursor.fetchone() is not None

    reply_user = None
    if updated_comment['parent_id']:
        cursor.execute('SELECT user_id FROM task_comments WHERE id = ?', (updated_comment['parent_id'],))
        parent_comment = cursor.fetchone()
        if parent_comment:
            cursor.execute('SELECT * FROM users WHERE id = ?', (parent_comment['user_id'],))
            reply_user = cursor.fetchone()

    conn.close()
    return jsonify(comment_to_dict(updated_comment, user, like_count, is_liked, reply_user))


@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@token_required
def delete_comment(current_user_id, comment_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM task_comments WHERE id = ?', (comment_id,))
    comment = cursor.fetchone()
    if comment is None:
        conn.close()
        return jsonify({'error': '评论不存在'}), 404

    if comment['user_id'] != current_user_id:
        conn.close()
        return jsonify({'error': '您只能删除自己的评论'}), 403

    cursor.execute('DELETE FROM task_comments WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '评论删除成功'})


@app.route('/api/comments/<int:comment_id>/like', methods=['POST'])
@token_required
def like_comment(current_user_id, comment_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT c.*, t.user_id as task_user_id FROM task_comments c INNER JOIN tasks t ON c.task_id = t.id WHERE c.id = ?', (comment_id,))
    comment = cursor.fetchone()
    if comment is None:
        conn.close()
        return jsonify({'error': '评论不存在'}), 404

    task = _user_can_access_task(cursor, current_user_id, comment['task_id'])
    if task is None:
        conn.close()
        return jsonify({'error': '您无权限操作此评论'}), 403

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO comment_likes (comment_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        ''', (comment_id, current_user_id))
    else:
        cursor.execute('INSERT OR IGNORE INTO comment_likes (comment_id, user_id) VALUES (?, ?)', (comment_id, current_user_id))
    conn.commit()

    cursor.execute('SELECT COUNT(*) as cnt FROM comment_likes WHERE comment_id = ?', (comment_id,))
    like_count = cursor.fetchone()['cnt']

    conn.close()
    return jsonify({'like_count': like_count, 'is_liked': True})


@app.route('/api/comments/<int:comment_id>/like', methods=['DELETE'])
@token_required
def unlike_comment(current_user_id, comment_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT c.* FROM task_comments c WHERE c.id = ?', (comment_id,))
    comment = cursor.fetchone()
    if comment is None:
        conn.close()
        return jsonify({'error': '评论不存在'}), 404

    task = _user_can_access_task(cursor, current_user_id, comment['task_id'])
    if task is None:
        conn.close()
        return jsonify({'error': '您无权限操作此评论'}), 403

    cursor.execute('DELETE FROM comment_likes WHERE comment_id = ? AND user_id = ?', (comment_id, current_user_id))
    conn.commit()

    cursor.execute('SELECT COUNT(*) as cnt FROM comment_likes WHERE comment_id = ?', (comment_id,))
    like_count = cursor.fetchone()['cnt']

    conn.close()
    return jsonify({'like_count': like_count, 'is_liked': False})


@app.route('/api/tasks/<int:task_id>/mention-users', methods=['GET'])
@token_required
def get_task_mention_users(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()

    task = _user_can_access_task(cursor, current_user_id, task_id)
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在或您无权限访问'}), 404

    user_ids = set()
    user_ids.add(task['user_id'])
    if task['assignee_id']:
        user_ids.add(task['assignee_id'])

    cursor.execute('''
        SELECT DISTINCT shared_with_user_id FROM task_shares
        WHERE task_id = ? AND shared_with_user_id IS NOT NULL
    ''', (task_id,))
    for row in cursor.fetchall():
        if row['shared_with_user_id']:
            user_ids.add(row['shared_with_user_id'])

    cursor.execute('''
        SELECT DISTINCT tm.user_id FROM task_shares ts
        INNER JOIN team_members tm ON ts.team_id = tm.team_id
        WHERE ts.task_id = ?
    ''', (task_id,))
    for row in cursor.fetchall():
        user_ids.add(row['user_id'])

    cursor.execute('''
        SELECT DISTINCT c.user_id FROM task_comments c
        WHERE c.task_id = ?
    ''', (task_id,))
    for row in cursor.fetchall():
        user_ids.add(row['user_id'])

    result = []
    for uid in user_ids:
        cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (uid,))
        user = cursor.fetchone()
        if user:
            result.append(user_to_dict(user))

    conn.close()
    return jsonify(result)


def wait_for_db():
    if DB_TYPE == 'postgresql':
        import time
        max_retries = 30
        retry_interval = 2
        for i in range(max_retries):
            try:
                conn = get_db()
                conn.close()
                print('[db] Database connection successful')
                return True
            except Exception as e:
                print(f'[db] Waiting for database... attempt {i + 1}/{max_retries}')
                time.sleep(retry_interval)
        print('[db] Could not connect to database after maximum retries')
        return False
    return True


def task_template_to_dict(template, category=None, tags=None):
    result = {
        'id': template['id'],
        'user_id': template['user_id'],
        'name': template['name'],
        'title': template['title'],
        'description': template['description'],
        'priority': template['priority'],
        'category_id': template['category_id'],
        'is_pinned': bool(template['is_pinned']),
        'repeat_pattern': template['repeat_pattern'] or 'none',
        'created_at': template['created_at'],
        'updated_at': template['updated_at'],
    }
    if category:
        result['category'] = category_to_dict(category)
    if tags is not None:
        result['tags'] = [tag_to_dict(tag) for tag in tags]
    return result


@app.route('/api/templates', methods=['GET'])
@token_required
def get_templates(current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM task_templates WHERE user_id = ? ORDER BY created_at DESC',
        (current_user_id,)
    )
    templates = cursor.fetchall()
    result = []
    for template in templates:
        category = None
        if template['category_id']:
            cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (template['category_id'], current_user_id))
            category = cursor.fetchone()
        cursor.execute('''
            SELECT t.* FROM tags t
            INNER JOIN task_template_tags ttt ON t.id = ttt.tag_id
            WHERE ttt.template_id = ? AND t.user_id = ?
            ORDER BY t.created_at ASC
        ''', (template['id'], current_user_id))
        tags = cursor.fetchall()
        result.append(task_template_to_dict(template, category, tags))
    conn.close()
    return jsonify(result)


@app.route('/api/templates/<int:template_id>', methods=['GET'])
@token_required
def get_template(current_user_id, template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task_templates WHERE id = ? AND user_id = ?', (template_id, current_user_id))
    template = cursor.fetchone()
    if template is None:
        conn.close()
        return jsonify({'error': '模板不存在'}), 404
    category = None
    if template['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (template['category_id'], current_user_id))
        category = cursor.fetchone()
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_template_tags ttt ON t.id = ttt.tag_id
        WHERE ttt.template_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (template['id'], current_user_id))
    tags = cursor.fetchall()
    conn.close()
    return jsonify(task_template_to_dict(template, category, tags))


@app.route('/api/templates', methods=['POST'])
@token_required
def create_template(current_user_id):
    data = request.get_json()
    if not data or 'name' not in data or not data['name'].strip():
        return jsonify({'error': '模板名称不能为空'}), 400
    if 'title' not in data or not data['title'].strip():
        return jsonify({'error': '任务标题不能为空'}), 400

    name = data['name'].strip()
    title = data['title'].strip()
    description = data.get('description', '')
    category_id = data.get('category_id')
    priority = data.get('priority', 'medium')
    is_pinned = data.get('is_pinned', False)
    repeat_pattern = validate_repeat_pattern(data.get('repeat_pattern', 'none'))
    tag_ids = data.get('tag_ids', [])

    if priority not in ['high', 'medium', 'low']:
        priority = 'medium'

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM task_templates WHERE user_id = ? AND name = ?', (current_user_id, name))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({'error': '模板名称已存在'}), 400

    if category_id is not None:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
        category = cursor.fetchone()
        if not category:
            conn.close()
            return jsonify({'error': '分类不存在'}), 404

    for tag_id in tag_ids:
        cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
        tag = cursor.fetchone()
        if not tag:
            conn.close()
            return jsonify({'error': f'标签 ID {tag_id} 不存在'}), 404

    cursor.execute(
        'INSERT INTO task_templates (user_id, name, title, description, priority, category_id, is_pinned, repeat_pattern) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (current_user_id, name, title, description, priority, category_id, 1 if is_pinned else 0, repeat_pattern)
    )
    conn.commit()
    template_id = cursor.lastrowid

    for tag_id in tag_ids:
        cursor.execute(
            'INSERT OR IGNORE INTO task_template_tags (template_id, tag_id) VALUES (?, ?)',
            (template_id, tag_id)
        )
    conn.commit()

    cursor.execute('SELECT * FROM task_templates WHERE id = ?', (template_id,))
    template = cursor.fetchone()
    category = None
    if template['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (template['category_id'], current_user_id))
        category = cursor.fetchone()
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_template_tags ttt ON t.id = ttt.tag_id
        WHERE ttt.template_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (template['id'], current_user_id))
    tags = cursor.fetchall()
    conn.close()
    return jsonify(task_template_to_dict(template, category, tags)), 201


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
@token_required
def update_template(current_user_id, template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task_templates WHERE id = ? AND user_id = ?', (template_id, current_user_id))
    template = cursor.fetchone()
    if template is None:
        conn.close()
        return jsonify({'error': '模板不存在'}), 404

    data = request.get_json()
    name = data.get('name', template['name']).strip() if 'name' in data else template['name']
    title = data.get('title', template['title']).strip() if 'title' in data else template['title']
    description = data.get('description', template['description']) if 'description' in data else template['description']
    priority = data.get('priority', template['priority']) if 'priority' in data else template['priority']
    category_id = data.get('category_id', template['category_id']) if 'category_id' in data else template['category_id']
    is_pinned = data.get('is_pinned', bool(template['is_pinned'])) if 'is_pinned' in data else bool(template['is_pinned'])
    repeat_pattern = validate_repeat_pattern(data.get('repeat_pattern', template['repeat_pattern'] or 'none')) if 'repeat_pattern' in data else template['repeat_pattern'] or 'none'
    tag_ids = data.get('tag_ids', None)

    if not name:
        conn.close()
        return jsonify({'error': '模板名称不能为空'}), 400
    if not title:
        conn.close()
        return jsonify({'error': '任务标题不能为空'}), 400
    if priority not in ['high', 'medium', 'low']:
        priority = template['priority'] or 'medium'

    if name != template['name']:
        cursor.execute('SELECT * FROM task_templates WHERE user_id = ? AND name = ? AND id != ?', (current_user_id, name, template_id))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({'error': '模板名称已存在'}), 400

    if category_id is not None and category_id != template['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
        category = cursor.fetchone()
        if not category:
            conn.close()
            return jsonify({'error': '分类不存在'}), 404

    cursor.execute(
        'UPDATE task_templates SET name = ?, title = ?, description = ?, priority = ?, category_id = ?, is_pinned = ?, repeat_pattern = ?, updated_at = ? WHERE id = ?',
        (name, title, description, priority, category_id, 1 if is_pinned else 0, repeat_pattern, format_datetime(datetime.now()), template_id)
    )
    conn.commit()

    if tag_ids is not None:
        cursor.execute('DELETE FROM task_template_tags WHERE template_id = ?', (template_id,))
        for tag_id in tag_ids:
            cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
            tag = cursor.fetchone()
            if tag:
                cursor.execute(
                    'INSERT OR IGNORE INTO task_template_tags (template_id, tag_id) VALUES (?, ?)',
                    (template_id, tag_id)
                )
        conn.commit()

    cursor.execute('SELECT * FROM task_templates WHERE id = ?', (template_id,))
    updated_template = cursor.fetchone()
    category = None
    if updated_template['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (updated_template['category_id'], current_user_id))
        category = cursor.fetchone()
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_template_tags ttt ON t.id = ttt.tag_id
        WHERE ttt.template_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (updated_template['id'], current_user_id))
    tags = cursor.fetchall()
    conn.close()
    return jsonify(task_template_to_dict(updated_template, category, tags))


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@token_required
def delete_template(current_user_id, template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task_templates WHERE id = ? AND user_id = ?', (template_id, current_user_id))
    template = cursor.fetchone()
    if template is None:
        conn.close()
        return jsonify({'error': '模板不存在'}), 404
    cursor.execute('DELETE FROM task_template_tags WHERE template_id = ?', (template_id,))
    cursor.execute('DELETE FROM task_templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()
    return '', 204


@app.route('/api/templates/<int:template_id>/apply', methods=['POST'])
@token_required
def create_task_from_template(current_user_id, template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM task_templates WHERE id = ? AND user_id = ?', (template_id, current_user_id))
    template = cursor.fetchone()
    if template is None:
        conn.close()
        return jsonify({'error': '模板不存在'}), 404

    data = request.get_json() or {}
    title = data.get('title', template['title']).strip() or template['title']
    description = data.get('description', template['description']) if 'description' in data else template['description']
    category_id = data.get('category_id', template['category_id']) if 'category_id' in data else template['category_id']
    priority = data.get('priority', template['priority']) if 'priority' in data else template['priority']
    is_pinned = data.get('is_pinned', bool(template['is_pinned'])) if 'is_pinned' in data else bool(template['is_pinned'])
    repeat_pattern = validate_repeat_pattern(data.get('repeat_pattern', template['repeat_pattern'] or 'none')) if 'repeat_pattern' in data else template['repeat_pattern'] or 'none'
    due_date = format_due_date(data.get('due_date')) if 'due_date' in data else None
    assignee_id = data.get('assignee_id')
    share_team_id = data.get('share_team_id')
    share_with_user_ids = data.get('share_with_user_ids', [])
    share_can_edit = data.get('share_can_edit', False)

    if priority not in ['high', 'medium', 'low']:
        priority = 'medium'

    if category_id is not None:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
        category = cursor.fetchone()
        if not category:
            conn.close()
            return jsonify({'error': '分类不存在'}), 404

    if assignee_id is not None:
        cursor.execute('SELECT * FROM users WHERE id = ?', (assignee_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': '被分配用户不存在'}), 404

    if share_team_id is not None:
        cursor.execute('''
            SELECT tm.* FROM team_members tm
            WHERE tm.team_id = ? AND tm.user_id = ?
        ''', (share_team_id, current_user_id))
        team_member = cursor.fetchone()
        if team_member is None:
            conn.close()
            return jsonify({'error': '您不是该团队成员，无法与该团队共享'}), 403

    for shared_uid in share_with_user_ids:
        cursor.execute('SELECT * FROM users WHERE id = ?', (shared_uid,))
        target_user = cursor.fetchone()
        if target_user is None:
            conn.close()
            return jsonify({'error': f'目标用户 ID {shared_uid} 不存在'}), 404

    cursor.execute(
        'INSERT INTO tasks (user_id, category_id, title, description, priority, due_date, is_pinned, repeat_pattern, assignee_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (current_user_id, category_id, title, description, priority, due_date, 1 if is_pinned else 0, repeat_pattern, assignee_id)
    )
    conn.commit()
    task_id = cursor.lastrowid

    cursor.execute('''
        SELECT tag_id FROM task_template_tags WHERE template_id = ?
    ''', (template_id,))
    template_tag_rows = cursor.fetchall()
    for tag_row in template_tag_rows:
        cursor.execute(
            'INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)',
            (task_id, tag_row['tag_id'])
        )
    conn.commit()

    if share_team_id is not None:
        cursor.execute(
            'INSERT INTO task_shares (task_id, team_id, can_edit) VALUES (?, ?, ?)',
            (task_id, share_team_id, 1 if share_can_edit else 0)
        )
        conn.commit()

    for shared_uid in share_with_user_ids:
        cursor.execute(
            'INSERT INTO task_shares (task_id, shared_with_user_id, can_edit) VALUES (?, ?, ?)',
            (task_id, shared_uid, 1 if share_can_edit else 0)
        )
        conn.commit()

    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()

    category = None
    if task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (task['category_id'], current_user_id))
        category = cursor.fetchone()

    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_tags tt ON t.id = tt.tag_id
        WHERE tt.task_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (task['id'], current_user_id))
    tags = cursor.fetchall()

    cursor.execute('''
        SELECT * FROM attachments WHERE task_id = ? ORDER BY created_at ASC
    ''', (task['id'],))
    attachments = cursor.fetchall()

    assignee = None
    if task['assignee_id']:
        cursor.execute('SELECT * FROM users WHERE id = ?', (task['assignee_id'],))
        assignee = cursor.fetchone()

    cursor.execute('SELECT * FROM users WHERE id = ?', (current_user_id,))
    creator = cursor.fetchone()

    conn.close()
    return jsonify(task_to_dict(task, category, tags, attachments, assignee, creator)), 201


@app.route('/api/tasks/<int:task_id>/save-as-template', methods=['POST'])
@token_required
def save_task_as_template(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404

    data = request.get_json()
    if not data or 'name' not in data or not data['name'].strip():
        return jsonify({'error': '模板名称不能为空'}), 400

    name = data['name'].strip()

    cursor.execute('SELECT * FROM task_templates WHERE user_id = ? AND name = ?', (current_user_id, name))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return jsonify({'error': '模板名称已存在'}), 400

    cursor.execute(
        'INSERT INTO task_templates (user_id, name, title, description, priority, category_id, is_pinned, repeat_pattern) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (current_user_id, name, task['title'], task['description'], task['priority'], task['category_id'], 1 if bool(task['is_pinned']) else 0, task['repeat_pattern'] or 'none')
    )
    conn.commit()
    template_id = cursor.lastrowid

    cursor.execute('''
        SELECT tag_id FROM task_tags WHERE task_id = ?
    ''', (task_id,))
    task_tag_rows = cursor.fetchall()
    for tag_row in task_tag_rows:
        cursor.execute(
            'INSERT OR IGNORE INTO task_template_tags (template_id, tag_id) VALUES (?, ?)',
            (template_id, tag_row['tag_id'])
        )
    conn.commit()

    cursor.execute('SELECT * FROM task_templates WHERE id = ?', (template_id,))
    template = cursor.fetchone()
    category = None
    if template['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (template['category_id'], current_user_id))
        category = cursor.fetchone()
    cursor.execute('''
        SELECT t.* FROM tags t
        INNER JOIN task_template_tags ttt ON t.id = ttt.tag_id
        WHERE ttt.template_id = ? AND t.user_id = ?
        ORDER BY t.created_at ASC
    ''', (template['id'], current_user_id))
    tags = cursor.fetchall()
    conn.close()
    return jsonify(task_template_to_dict(template, category, tags)), 201


wait_for_db()
init_db()
start_daily_repeat_scheduler()


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)
