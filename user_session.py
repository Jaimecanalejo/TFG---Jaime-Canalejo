import sqlite3
import json
import os

DB_FILE = "users_db.sqlite"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():

    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            nombre TEXT PRIMARY KEY,
            configuracion TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def obtener_usuario(nombre):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT configuracion FROM usuarios WHERE nombre = ?", (nombre,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return None

def crear_usuario(nombre):
    usuario_existente = obtener_usuario(nombre)
    if usuario_existente is not None:
        return False
        
    valores_por_defecto = {
        "ticker_1": "AAPL",
        "ticker_2": "MSFT",
        "temporalidad": "1 Semana",
        "sensibilidad_sma": 30
    }
    
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO usuarios (nombre, configuracion)
        VALUES (?, ?)
    ''', (nombre, json.dumps(valores_por_defecto)))
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
