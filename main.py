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
    last_seen DOUBLE PRECISION NOT NULL,
    ipv6 TEXT NOT NULL,
    port6 INTEGER NOT NULL
)
""")

db.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS joining (
    id TEXT NOT NULL,
    ipv4 TEXT NOT NULL,
    port INTEGER NOT NULL,
    game TEXT NOT NULL,
    last_seen DOUBLE PRECISION NOT NULL,
    start DOUBLE PRECISION NOT NULL,
    ipv6 TEXT NOT NULL,
    port6 INTEGER NOT NULL
)
""")

db.commit()
db.close()

app = Flask(__name__)

last_cleanup = 0
latest_player = None

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

    cursor.execute(
        """
        DELETE FROM joining
        WHERE last_seen < %s
        """,
        (time.time() - 30,)
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
    ipv6 = data["ipv6"]
    id_ = generate_session_id()
    token = generate_token()
    while is_in_data(id_):
        id_ = generate_session_id()
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "INSERT INTO sessions VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
    (id_, token, data["game"], ipv4, data["port"], time.time(), ipv6, data["port6"])
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
    ipv6 = data["ipv6"]
    id_ = data["id"]
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "UPDATE sessions SET ipv4=%s, port=%s, ipv6=%s, port6=%s, last_seen=%s WHERE id=%s AND token=%s",
    (ipv4, data["port"], ipv6, data["port6"], time.time(), id_, data["token"])
    )
    db.commit()
    db.close()
    if cursor.rowcount == 0:
        return jsonify({
        "success": False,
        "info": "SDX" # entry doesn't exist, make a new one or people cant join
        })
    return jsonify({
        "success": True,
        "id": id_
    })
    
@app.route("/info", methods=["POST"])
def info():
    data = request.json
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT 1 FROM sessions WHERE id=%s AND token=%s",
    (data["id"], data["token"])
    )
    res = cursor.fetchone()
    if res is None:
        db.close()
        return jsonify({
        "success": False,
        "info": "SDX"
        })
    cursor.execute(
    "SELECT ipv4, port, start, ipv6, port6 FROM joining WHERE id=%s AND game=%s ORDER BY last_seen LIMIT 1",
    (data["id"], data["game"])
    )
    res = cursor.fetchone()
    if res is None:
        db.close()
        return jsonify({
        "success": False,
        "info": "JDX",
        })
    cursor.execute(
    "DELETE FROM joining WHERE ipv4=%s AND port=%s AND id=%s AND game=%s AND ipv6=%s AND port6=%s",
    (res[0], res[1], data["id"], data["game"], res[3], res[4])
    )
    db.commit()
    db.close()
    return jsonify({
    "success": True,
    "ipv4": res[0],
    "ipv6": res[3],
    "port": res[1],
    "port6": res[4],
    "start": res[2]
    })
def isinjoining():
    ipv4 = get_client_ip()
    ipv6 = request.json["ipv6"]
    id_ = request.json["id"]
    game = request.json["game"]
    port = request.json["port"]
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT start FROM joining WHERE ipv4=%s AND ipv6=%s AND port=%s AND port6=%s AND id=%s AND game=%s",
    (ipv4, ipv6, port, request.json["port6"], id_, game)
    )
    res = cursor.fetchone()
    db.close()
    if res is not None:
        return res[0]
    return None
@app.route("/join", methods=["POST"])
def join():
    data = request.json
    ipv6 = data["ipv6"]
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT ipv4, port, ipv6, port6 FROM sessions WHERE id=%s AND game=%s",
    (data["id"],data["game"])
    )
    res = cursor.fetchone()
    db.close()
    if res is None:
        return jsonify({
        "success": False,
        "info": "SDX" # entry doesnt exist
        })
    if not isinjoining():
        db = psycopg2.connect(os.environ["DATA_URL"])
        cursor = db.cursor()
        timing = time.time()+10
        cursor.execute(
        "INSERT INTO joining VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (data["id"], get_client_ip(), data["port"], data["game"], time.time(), timing, ipv6, data["port6"])
        )
        db.commit()
        db.close()
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT * FROM joining WHERE id=%s AND ipv4=%s AND ipv6=%s AND port=%s AND port6=%s AND game=%s",
    (data["id"], get_client_ip(), ipv6, data["port"], data["port6"], data["game"])
    )
    res2 = cursor.fetchone()
    db.close()
    if res2 is None:
        return jsonify({
        "success": False,
        "info": "JDX"
        })
    return jsonify({
        "success": True,
        "ipv4": res[0],
        "ipv6": res[2],
        "port": res[1],
        "port6": res[3],
        "start": res2[5]
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
        "info": "SDX" # entry doesnt exist
        })
    return jsonify({
        "success": True
    })
