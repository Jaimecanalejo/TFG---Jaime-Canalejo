import sqlite3
import json
import os
import hashlib
import secrets

DB_FILE = "users_db.sqlite"

def get_connection():
    return sqlite3.connect(DB_FILE)

def hash_password(password, salt):
    """
    Función de seguridad (TFG): aplica un hash seguro a la contraseña 
    utilizando SHA-256 junto con un 'salt' aleatorio para evitar ataques.
    """
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def init_db():
    """Crea la tabla de usuarios con columnas dedicadas a seguridad."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            nombre TEXT PRIMARY KEY,
            password_hash TEXT,
            salt TEXT,
            configuracion TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def verificar_login(nombre, password):
    """Comprueba si el usuario existe y la contraseña es correcta comprobando el hash."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password_hash, salt FROM usuarios WHERE nombre = ?", (nombre,))
    row = c.fetchone()
    conn.close()
    
    if row:
        stored_hash = row[0]
        salt = row[1]
        # Comparamos el hash almacenado con el hash de la contraseña introducida calculada con el mismo salt
        if stored_hash == hash_password(password, salt):
            return True
    return False

def obtener_usuario(nombre):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT configuracion FROM usuarios WHERE nombre = ?", (nombre,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None

def crear_usuario(nombre, password):
    usuario_existente = obtener_usuario(nombre)
    if usuario_existente is not None:
        return False
        
    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)
    
    valores_por_defecto = {
        "ticker_1": "AAPL",
        "ticker_2": "MSFT",
        "temporalidad": "1 Semana",
        "sensibilidad_sma": 30
    }
    
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO usuarios (nombre, password_hash, salt, configuracion)
        VALUES (?, ?, ?, ?)
    ''', (nombre, password_hash, salt, json.dumps(valores_por_defecto)))
    conn.commit()
    conn.close()
    return True

def actualizar_usuario(nombre, ajustes):
    usuario_actual = obtener_usuario(nombre)
    if usuario_actual is not None:
        usuario_actual.update(ajustes)
        
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE usuarios 
            SET configuracion = ? 
            WHERE nombre = ?
        ''', (json.dumps(usuario_actual), nombre))
        conn.commit()
        conn.close()
