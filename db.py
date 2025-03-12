import json
import sqlite3
import time
from datetime import datetime
import os
import psycopg2
import psycopg2.extras
from config import DB_TYPE, DATABASE_URL, DB_PATH

def get_db_connection():
    """Create a connection to the database (SQLite or PostgreSQL)"""
    if DB_TYPE == 'postgresql':
        # PostgreSQL connection
        conn = psycopg2.connect(DATABASE_URL)
        # Enable automatic conversion to Python dict
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        # SQLite connection (default)
        def dict_factory(cursor, row):
            """Convert database row objects to dictionaries"""
            d = {}
            for idx, col in enumerate(cursor.description):
                d[col[0]] = row[idx]
            return d
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = dict_factory
        return conn

def init_db():
    """Initialize the database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        # PostgreSQL schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            file_path TEXT NOT NULL,
            webhook_url TEXT,
            api_key_hash TEXT,
            results TEXT,
            error TEXT,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        ''')
    else:
        # SQLite schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            file_path TEXT NOT NULL,
            webhook_url TEXT,
            api_key_hash TEXT,
            results TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
    
    conn.commit()
    conn.close()

def create_job(job_id, file_path, webhook_url=None, api_key_hash=None):
    """Create a new job in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('''
        INSERT INTO jobs (id, status, file_path, webhook_url, api_key_hash, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (job_id, 'pending', file_path, webhook_url, api_key_hash, now, now))
    else:
        cursor.execute('''
        INSERT INTO jobs (id, status, file_path, webhook_url, api_key_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, 'pending', file_path, webhook_url, api_key_hash, now, now))
    
    conn.commit()
    conn.close()
    
    return get_job(job_id)

def get_job(job_id):
    """Get a job by its ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM jobs WHERE id = %s', (job_id,))
    else:
        cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
    job = cursor.fetchone()
    
    conn.close()
    
    if job and job.get('results'):
        try:
            job['results'] = json.loads(job['results'])
        except json.JSONDecodeError:
            # If results is not valid JSON, leave it as a string
            pass
    
    return job

def get_pending_jobs():
    """Get all pending jobs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM jobs WHERE status = %s ORDER BY created_at ASC', ('pending',))
    else:
        cursor.execute('SELECT * FROM jobs WHERE status = ? ORDER BY created_at ASC', ('pending',))
    jobs = cursor.fetchall()
    
    conn.close()
    return jobs

def update_job_status(job_id, status, results=None, error=None):
    """Update a job's status and optionally its results or error message"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    if results:
        if isinstance(results, dict) or isinstance(results, list):
            results = json.dumps(results)
        
        if DB_TYPE == 'postgresql':
            cursor.execute('''
            UPDATE jobs
            SET status = %s, results = %s, updated_at = %s
            WHERE id = %s
            ''', (status, results, now, job_id))
        else:
            cursor.execute('''
            UPDATE jobs
            SET status = ?, results = ?, updated_at = ?
            WHERE id = ?
            ''', (status, results, now, job_id))
    elif error:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
            UPDATE jobs
            SET status = %s, error = %s, updated_at = %s
            WHERE id = %s
            ''', (status, error, now, job_id))
        else:
            cursor.execute('''
            UPDATE jobs
            SET status = ?, error = ?, updated_at = ?
            WHERE id = ?
            ''', (status, error, now, job_id))
    else:
        if DB_TYPE == 'postgresql':
            cursor.execute('''
            UPDATE jobs
            SET status = %s, updated_at = %s
            WHERE id = %s
            ''', (status, now, job_id))
        else:
            cursor.execute('''
            UPDATE jobs
            SET status = ?, updated_at = ?
            WHERE id = ?
            ''', (status, now, job_id))
    
    conn.commit()
    conn.close()
    
    return get_job(job_id)

def get_all_jobs():
    """Get all jobs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    else:
        cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
    jobs = cursor.fetchall()
    
    conn.close()
    
    for job in jobs:
        if job.get('results'):
            try:
                job['results'] = json.loads(job['results'])
            except json.JSONDecodeError:
                # If results is not valid JSON, leave it as a string
                pass
    
    return jobs
