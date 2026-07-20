from flask import Flask, request, jsonify
import string, secrets, time
import psycopg2
import os

db = pyscopg2.connect(os.environ["DATA_URL"])
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    game TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    last_seen DOUBLE PRECISION NOT NULL
)
""")

db.commit()

app = Flask(__name__)

def generate_session_id():
    return "".join(secrets.choice(string.ascii_uppercase) for i in range(4))+"".join(secrets.choice(string.digits) for i in range(6))
def generate_token():
    return secrets.token_hex(16)
def is_in_data(id_):
    result = cursor.execute(
    "SELECT 1 FROM sessions WHERE id=%s",
    (id_,)
    ).fetchone()
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
    cursor.execute(
    "INSERT INTO sessions VALUES (%s, %s, %s, %s, %s, %s)",
    (id_, token, data["game"], ipv6, data["port"], time.time())
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
    cursor = cursor.execute(
    "UPDATE sessions SET ip=%s, port=%s, last_seen=%s WHERE id=%s AND token=%s",
    (ipv6, data["port"], time.time(), id_, data["token"])
    )
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({
        "success": False,
        "info": "EDX" # entry doesn't exist, make a new one or people cant join
        })
    return jsonify({
        "success": True,
        "id": id_
    })
    
@app.route("/join", methods=["POST"])
def join():
    data = request.json
    res = cursor.execute(
    "SELECT ip, port, game FROM sessions WHERE id=%s",
    (data["id"],)
    ).fetchone()
    if res is None:
        return jsonify({
        "success": False,
        "info": "EDX" # entry doesnt exist
        })
    return jsonify({
        "success": res is not None,
        "ip": res[0] if res is not None else None,
        "port": res[1] if res is not None else None,
        "game": res[2] if res is not None else None
    })
@app.route("/delete", methods=["POST"])
def delete():
    data = request.json
    cursor = cursor.execute(
    "DELETE FROM sessions WHERE id=%s AND token=%s",
    (data["id"],data["token"])
    )
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({
        "success": False,
        "info": "EDX" # entry doesnt exist
        })
    return jsonify({
        "success": True
    })
