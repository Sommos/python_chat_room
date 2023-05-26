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

@app.route("/room")
def room():
    return render_template("room.html")

if __name__ == "__main__":
    # run socketio packaged with Flask web app in debug mode, allows for auto-reload
    socketio.run(app, debug=True)
