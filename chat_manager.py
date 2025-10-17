import sqlite3
import os
from datetime import datetime

DB_FILE = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codebase_id TEXT,
            role TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS codebases (
            id TEXT PRIMARY KEY,
            name TEXT,
            path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    
def register_codebase(codebase_id, name, path):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO codebases (id, name, path)
        VALUES (?, ?, ?)
    ''', (codebase_id, name, path))
    conn.commit()
    conn.close()

def list_codebases():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, name, path FROM codebases ORDER BY created_at DESC')
    result = c.fetchall()
    conn.close()
    return result

def delete_codebase(codebase_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM chat WHERE codebase_id=?', (codebase_id,))
    c.execute('DELETE FROM codebases WHERE id=?', (codebase_id,))
    conn.commit()
    conn.close()

def save_message(codebase_id, role, message):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO chat (codebase_id, role, message)
        VALUES (?, ?, ?)
    ''', (codebase_id, role, message))
    conn.commit()
    conn.close()

def get_chat_history(codebase_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT role, message, timestamp FROM chat
        WHERE codebase_id = ?
        ORDER BY timestamp ASC
    ''', (codebase_id,))
    history = c.fetchall()
    conn.close()
    return history

def clear_chat_history(codebase_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM chat WHERE codebase_id = ?', (codebase_id,))
    conn.commit()
    conn.close()
