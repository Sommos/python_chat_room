from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
from string import ascii_uppercase
import random
import regex as re
import secrets
import string
import sqlite3

# create a Flask web app
app = Flask(__name__)
app.config["SECRET_KEY"] = "0hWbTrJ,4=iKVD"
socketio = SocketIO(app)

# creates a global variable for a dictionary of rooms
rooms = {}

# creates a connection to an sql database called rooms.db
conn = sqlite3.connect('rooms.db')
# creates a cursor object to execute sql commands
conn.execute('''
            CREATE TABLE IF NOT EXISTS rooms
                (code TEXT PRIMARY KEY,
                members INTEGER,
                messages TEXT)
            ''')

# load existing room data from the database into the rooms dictionary
cursor = conn.execute("SELECT code, members, messages FROM rooms")
# iterate through each row in the database
for row in cursor:
    # add room to dictionary
    rooms[row[0]] = {"members": row[1], "messages": row[2].split(";")}
# close the cursor object
cursor.close()

# generates a unique code for a room
def generate_unique_code(length):
    # define the characters to choose from for the code
    characters = string.ascii_uppercase

    # generate a unique code using secrets.choice to randomly select characters
    while True:
        code = ''.join(secrets.choice(characters) for i in range(length))

        # check if code is already in use
        if code not in rooms:
            break

    return code

# makes a route for app that allows for get and post requests
@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        # get variables from form
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # check if name has been entered
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        # check if name is alphanumeric
        elif not re.match(r'^[a-zA-Z0-9]+$', name):
            return render_template("home.html", error="Invalid name. Name must be alphanumeric.", code=code, name=name)
        
        # check if user is creating a room
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        # check if room code is alphanumeric
        elif not re.match(r'^[A-Z]+$', code):
            return render_template("home.html", error="Invalid room code. Room code must be uppercase.", code=code, name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            # add room to dictionary
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        
        return redirect(url_for("room"))
        
    return render_template("home.html")

# makes a route for app to a room
@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"), error="Invalid room or user name. Please try again.")
    
    # returns message history of room
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

# socketio event handler for when a user sends a message
@socketio.on("message")
def message(data):
    # get room code from session
    room = session.get("room")
    # check if room code is valid
    if room not in rooms:
        return
    
    # create a dictionary of the message content
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    
    # send message to all users in room
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

# socketio event handler for when a user joins a room
@socketio.on("connect")
def connect(auth):
    # get room code and user name from session
    room = session.get("room")
    name = session.get("name")

    # check if room code and name are valid
    if not room or not name or room in rooms:
        return

    # add user to room
    join_room(room)
    rooms[room]["members"] += 1
    # send message to all users in room that a user has joined
    send({"name": name, "message": "has joined the room."}, to=room)
    # update the rooms dictionary and database when adding a room or when a user join
    conn.execute("UPDATE rooms SET members = ? WHERE code = ?", (rooms[room]["members"], room))
    conn.commit()
    # print message to consoles
    print(f"{name} has joined room {room}.")

# socketio event handler for when a user leaves a room
@socketio.on("disconnect")
def disconnect():
    # get room code and user name from session
    room = session.get("room")
    name = session.get("name")

    # check if room code and user name are valid
    if not room or not name or room not in rooms:
        return
    
    # remove user from room
    leave_room(room)
    rooms[room]["members"] -= 1

    # remove the room from the rooms dictionary and database when no users are in it
    if rooms[room]["members"] <= 0:
        del rooms[room]
        conn.execute("DELETE FROM rooms WHERE code = ?", (room,))
        conn.commit()
    else:
        # send message to all users in room that a user has left
        send({"name": name, "message": "has left the room."}, to=room)
    # print message to consoles
    print(f"{name} has left room {room}.")

if __name__ == "__main__":
    # run socketio packaged with Flask web app in debug mode, allows for auto-reload
    socketio.run(app, debug=True)
