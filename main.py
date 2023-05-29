from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
from string import ascii_uppercase
import random

# create a Flask web app
app = Flask(__name__)
app.config["SECRET_KEY"] = "0hWbTrJ,4=iKVD"
socketio = SocketIO(app)

# creates a global variable for a dictionary of rooms
rooms = {}

# generates a unique code for a room
def generate_unique_code(length):
    while True:
        code = ""
        # generate a random code of given length parameter
        for i in range(length):
            code += random.choice(ascii_uppercase)

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

        # check if user is creating a room
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

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
        return redirect(url_for("home"))
    
    return render_template("room.html", code=room)

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

    # check if room code and user name are valid
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    # send message to all users in room that a user has joined
    send({"name": name, "message": "has joined the room."}, to = room)
    # add user to room
    rooms[room]["members"] += 1
    print(f"{name} has joined room {room}.")

# socketio event handler for when a user leaves a room
@socketio.on("disconnect")
def disconnect():
    # get room code and user name from session
    room = session.get("room")
    name = session.get("name")

    leave_room(room)

    # check if room code and user name are valid
    if room in rooms:
        rooms[room]["members"] -= 1
        # delete room if no users are in it
        if rooms[room]["members"] <= 0:
            del rooms[room]

    # send message to all users in room that a user has left
    send({"name": name, "message": "has left the room."}, to = room)
    print(f"{name} has left room {room}.")

if __name__ == "__main__":
    # run socketio packaged with Flask web app in debug mode, allows for auto-reload
    socketio.run(app, debug=True)
