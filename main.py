from flask import Flask, request, jsonify
import string, secrets, time
import psycopg2
import os

db = psycopg2.connect(os.environ["DATA_URL"])
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    game TEXT NOT NULL,
    ipv4 TEXT NOT NULL,
    port INTEGER NOT NULL,
    last_seen DOUBLE PRECISION NOT NULL
)
""")

db.commit()
db.close()

app = Flask(__name__)

last_cleanup = 0

def cleanup_sessions():
    global last_cleanup

    if time.time() - last_cleanup < 60:
        return  # only run once per minute

    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()

    cursor.execute(
        """
        DELETE FROM sessions
        WHERE last_seen < %s
        """,
        (time.time() - 600,)
    )

    db.commit()
    db.close()

    last_cleanup = time.time()
@app.before_request
def before_request():
    cleanup_sessions()
def generate_session_id():
    return "".join(secrets.choice(string.ascii_uppercase) for i in range(4))+"".join(secrets.choice(string.digits) for i in range(6))
def generate_token():
    return secrets.token_hex(16)
def is_in_data(id_):
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT 1 FROM sessions WHERE id=%s",
    (id_,)
    )
    result = cursor.fetchone()
    db.close()
    return result is not None
def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr
@app.route("/")
def home():
    return "Rendezvous server online!"
@app.route("/create", methods=["POST"])
def create():
    ipv4 = get_client_ip()
    data = request.json
    id_ = generate_session_id()
    token = generate_token()
    while is_in_data(id_):
        id_ = generate_session_id()
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "INSERT INTO sessions VALUES (%s, %s, %s, %s, %s, %s)",
    (id_, token, data["game"], ipv4, data["port"], time.time())
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
    ipv4 = get_client_ip()
    data = request.json
    id_ = data["id"]
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "UPDATE sessions SET ipv4=%s, port=%s, last_seen=%s WHERE id=%s AND token=%s",
    (ipv4, data["port"], time.time(), id_, data["token"])
    )
    db.commit()
    db.close()
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
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT ipv4, port, game FROM sessions WHERE id=%s",
    (data["id"],)
    )
    res = cursor.fetchone()
    db.close()
    if res is None:
        return jsonify({
        "success": False,
        "info": "EDX" # entry doesnt exist
        })
    return jsonify({
        "success": res is not None,
        "ipv4": res[0] if res is not None else None,
        "port": res[1] if res is not None else None,
        "game": res[2] if res is not None else None
    })
@app.route("/delete", methods=["POST"])
def delete():
    data = request.json
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "DELETE FROM sessions WHERE id=%s AND token=%s",
    (data["id"],data["token"])
    )
    db.commit()
    db.close()
    if cursor.rowcount == 0:
        return jsonify({
        "success": False,
        "info": "EDX" # entry doesnt exist
        })
    return jsonify({
        "success": True
    })
