from flask import Flask, request, jsonify
import string, secrets, time
import psycopg2
import os

db = psycopg2.connect(os.environ["DATA_URL"])
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    room_code TEXT PRIMARY KEY
    peer_id TEXT NOT NULL
)
""")

db.commit()
db.close()

app = Flask(__name__)

def generate_room_code():
    return "".join(secrets.choice(string.ascii_uppercase+string.digits) for i in range(3))+"-"+"".join(secrets.choice(string.ascii_uppercase+string.digits) for i in range(3))+"-"+"".join(secrets.choice(string.ascii_uppercase+string.digits) for i in range(3))
def is_in_data(code):
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT peer_id FROM rooms WHERE room_code=%s",
    (code,)
    )
    result = cursor.fetchone()
    db.close()
    return result[0] if result is not None else None
def is_in_data2(id_):
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "SELECT room_code FROM rooms WHERE peer_id=%s",
    (id_,)
    )
    result = cursor.fetchone()
    db.close()
    return result[0] if result is not None else None
@app.route("/")
def home():
    return "Rendezvous server online!"
@app.route("/create", methods=["POST"])
def create():
    if room_code := is_in_data2(request.json["peer_id"]):
        return jsonify({
        "success": True,
        "room_code": room_code 
        })
    id_ = generate_room_code()
    while is_in_data(id_):
        id_ = generate_room_code()
    db = psycopg2.connect(os.environ["DATA_URL"])
    cursor = db.cursor()
    cursor.execute(
    "INSERT INTO rooms VALUES (%s, %s)",
    (id_, request.json["peer_id"])
    )
    db.commit()
    db.close()
    return jsonify({
        "success": True,
        "room_code": id_
    })

    

@app.route("/join", methods=["POST"])
def join():
    data = request.json
    return jsonify({
    "success": True,
    "peer_id": is_in_data(data["room_code"])
    })
