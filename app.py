from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong secret key

# Connect to MongoDB
client = MongoClient("mongodb+srv://sai_shivamani1:12345@cluster0.fhbma.mongodb.net/sai?retryWrites=true&w=majority")  # Ensure MongoDB is running
db = client["sai"]
users_collection = db["sai_shivamani"]

@app.route("/")
def index():
    return render_template("full.html")

@app.route("/dashboard")
def dashboard():
    return "Hello World"

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    user = users_collection.find_one({"username": username})
    
    if user and check_password_hash(user["password"], password):
        session["user"] = username
        return jsonify({"message": "Login successful", "status": "success"})
    else:
        return jsonify({"message": "Invalid credentials", "status": "error"})

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    if users_collection.find_one({"username": username}):
        return jsonify({"message": "User already exists", "status": "error"})
    
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({"username": username, "password": hashed_password})
    
    return jsonify({"message": "Registration successful", "status": "success"})

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
