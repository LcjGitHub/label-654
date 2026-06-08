import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
DATABASE = 'todo.db'

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

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def migrate_db():
    conn = get_db()
    cursor = conn.cursor()
    
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
    
    conn.close()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
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
    conn.commit()
    conn.close()
    
    migrate_db()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
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

def task_to_dict(task, category=None, tags=None):
    result = {
        'id': task['id'],
        'category_id': task['category_id'],
        'title': task['title'],
        'description': task['description'],
        'priority': task['priority'],
        'due_date': task['due_date'],
        'completed': bool(task['completed']),
        'created_at': task['created_at'],
        'updated_at': task['updated_at']
    }
    if category:
        result['category'] = category_to_dict(category)
    if tags is not None:
        result['tags'] = [tag_to_dict(tag) for tag in tags]
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
        ORDER BY t.created_at DESC
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
        result.append(task_to_dict(task, category, tags))
    
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
    
    conn.close()
    return jsonify(task_to_dict(task, category, tags))

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
    tag_ids = data.get('tag_ids', [])
    
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
    
    conn = get_db()
    cursor = conn.cursor()
    
    for tag_id in tag_ids:
        cursor.execute('SELECT * FROM tags WHERE id = ? AND user_id = ?', (tag_id, current_user_id))
        tag = cursor.fetchone()
        if not tag:
            conn.close()
            return jsonify({'error': f'标签 ID {tag_id} 不存在'}), 404
    
    cursor.execute(
        'INSERT INTO tasks (user_id, category_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?, ?)',
        (current_user_id, category_id, title, description, priority, due_date)
    )
    conn.commit()
    task_id = cursor.lastrowid
    
    for tag_id in tag_ids:
        cursor.execute(
            'INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)',
            (task_id, tag_id)
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
    
    conn.close()
    return jsonify(task_to_dict(task, category, tags)), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(current_user_id, task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user_id))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    data = request.get_json()
    title = data.get('title', task['title'])
    description = data.get('description', task['description'])
    completed = data.get('completed', task['completed'])
    category_id = data.get('category_id', task['category_id'])
    priority = data.get('priority', task['priority'])
    
    if 'due_date' in data:
        due_date = format_due_date(data['due_date'])
    else:
        due_date = task['due_date']
    
    if priority not in ['high', 'medium', 'low']:
        priority = task['priority'] or 'medium'
    
    if category_id is not None and category_id != task['category_id']:
        cursor.execute('SELECT * FROM categories WHERE id = ? AND user_id = ?', (category_id, current_user_id))
        category = cursor.fetchone()
        if not category:
            conn.close()
            return jsonify({'error': '分类不存在'}), 404
    
    cursor.execute(
        'UPDATE tasks SET title = ?, description = ?, completed = ?, category_id = ?, priority = ?, due_date = ?, updated_at = ? WHERE id = ?',
        (title, description, completed, category_id, priority, due_date, format_datetime(datetime.now()), task_id)
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
    
    conn.close()
    return jsonify(task_to_dict(updated_task, category, tags))

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
    
    new_completed = not bool(task['completed'])
    cursor.execute(
        'UPDATE tasks SET completed = ?, updated_at = ? WHERE id = ?',
        (new_completed, format_datetime(datetime.now()), task_id)
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
    
    conn.close()
    return jsonify(task_to_dict(updated_task, category, tags))

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
    
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '任务删除成功'})

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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
