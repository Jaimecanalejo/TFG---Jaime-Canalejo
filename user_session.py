import json
import os

DB_FILE = "users_db.json"

def cargar_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def obtener_usuario(nombre):
    db = cargar_db()
    return db.get(nombre)

def crear_usuario(nombre):
    db = cargar_db()
    if nombre in db:
        return False
    # Valores por defecto para un nuevo usuario que coinciden EXACTAMENTE con app.py
    db[nombre] = {
        "ticker_1": "AAPL",
        "ticker_2": "MSFT",
        "temporalidad": "1 Semana",
        "sensibilidad_sma": 30
    }
    guardar_db(db)
    return True

def actualizar_usuario(nombre, ajustes):
    db = cargar_db()
    if nombre in db:
        db[nombre].update(ajustes)
        guardar_db(db)
