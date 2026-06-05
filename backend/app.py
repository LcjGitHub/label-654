import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = 'todo.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def task_to_dict(task):
    return {
        'id': task['id'],
        'title': task['title'],
        'description': task['description'],
        'completed': bool(task['completed']),
        'created_at': task['created_at'],
        'updated_at': task['updated_at']
    }

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = cursor.fetchall()
    conn.close()
    return jsonify([task_to_dict(task) for task in tasks])

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task_to_dict(task))

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    title = data['title']
    description = data.get('description', '')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (title, description) VALUES (?, ?)',
        (title, description)
    )
    conn.commit()
    task_id = cursor.lastrowid
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    return jsonify(task_to_dict(task)), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': 'Task not found'}), 404
    
    data = request.get_json()
    title = data.get('title', task['title'])
    description = data.get('description', task['description'])
    completed = data.get('completed', task['completed'])
    
    cursor.execute(
        'UPDATE tasks SET title = ?, description = ?, completed = ?, updated_at = ? WHERE id = ?',
        (title, description, completed, datetime.now().isoformat(), task_id)
    )
    conn.commit()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    updated_task = cursor.fetchone()
    conn.close()
    return jsonify(task_to_dict(updated_task))

@app.route('/api/tasks/<int:task_id>/toggle', methods=['PUT'])
def toggle_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': 'Task not found'}), 404
    
    new_completed = not bool(task['completed'])
    cursor.execute(
        'UPDATE tasks SET completed = ?, updated_at = ? WHERE id = ?',
        (new_completed, datetime.now().isoformat(), task_id)
    )
    conn.commit()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    updated_task = cursor.fetchone()
    conn.close()
    return jsonify(task_to_dict(updated_task))

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return jsonify({'error': 'Task not found'}), 404
    
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Task deleted successfully'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
