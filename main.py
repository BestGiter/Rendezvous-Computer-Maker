from flask import Flask, request, jsonify
import sqlite3, string, secrets, time

db = sqlite3.connect("sessions.db")

db.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    last_seen REAL NOT NULL
)
""")

db.commit()

db.close()

app = Flask(__name__)

def generate_session_id():
    return "".join(secrets.choice(string.ascii_uppercase) for i in range(4))+"".join(secrets.choice(string.digits) for i in range(6))
def generate_token():
    return secrets.token_hex(16)
def is_in_data(id_):
    db = sqlite3.connect("sessions.db")
    result = db.execute(
    "SELECT 1 FROM sessions WHERE id=?",
    (id_,)
    ).fetchone()
    db.close()
    return result is not None
@app.route("/")
def home():
    return "Rendezvous server online!"
@app.route("/create", methods=["POST"])
def create():
    ipv6 = request.remote_addr
    data = request.json
    id_ = generate_session_id()
    token = generate_token()
    while is_in_data(id_):
        id_ = generate_session_id()
    db = sqlite3.connect("sessions.db")
    db.execute(
    "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
    (id_, token, ipv6, data["port"], time.time())
    )
    db.commit()
    db.close()
    return jsonify({
        "success": True,
        "id": id_,
        "token": token
    })
@app.route("/update", methods=["POST"])
def update():
    ipv6 = request.remote_addr
    data = request.json
    id_ = data["id"]
    db = sqlite3.connect("sessions.db")
    cursor = db.execute(
    "UPDATE sessions SET ip=?, port=?, last_seen=? WHERE id=? AND token=?",
    (ipv6, data["port"], time.time(), id_, data["token"])
    )
    db.commit()
    db.close()
    return jsonify({
        "success": cursor.rowcount>0,
        "id": id_
    })
    
@app.route("/join", methods=["POST"])
def join():
    data = request.json
    db = sqlite3.connect("sessions.db")
    res = db.execute(
    "SELECT ip, port FROM sessions WHERE id=?",
    (data["id"],)
    ).fetchone()
    db.close()
    return jsonify({
        "success": res is not None,
        "ip": res[0] if res is not None else None,
        "port": res[1] if res is not None else None
    })
@app.route("/delete", methods=["POST"])
def delete():
    data = request.json
    db = sqlite3.connect("sessions.db")
    cursor = db.execute(
    "DELETE FROM sessions WHERE id=? AND token=?",
    (data["id"],data["token"])
    )
    db.commit()
    db.close()
    return jsonify({
        "success": cursor.rowcount>0
    })
