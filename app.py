from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  # Added missing import
import base64  # Added missing import
from datetime import datetime
import os  # Added for environment variables

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key")  # Use environment variable

# Connect to MongoDB - Use environment variables for credentials
mongo_uri = "mongodb+srv://sai_shivamani1:12345@cluster0.fhbma.mongodb.net/sai?retryWrites=true&w=majority"
client = MongoClient(mongo_uri)
db = client["sai"]
users_collection = db["sai_shivamani"]
events_collection = db["events"]

@app.route("/")
def index():
    username = session.get("user", "")
    return render_template("full.html", username_final=username)

@app.route("/joinevent")
def joinevent():
    return render_template("join2.html")

@app.route("/createevent")
def createevent():
    return render_template("CREATE.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("hero.html", username_final=session["user"])

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/addevent", methods=["POST"])
def add_event():
    try:
        # Check if user is logged in
        if "user" not in session:
            return jsonify({
                "success": False,
                "message": "User not logged in"
            }), 401
            
        # Handle form data with file upload
        if 'eventPoster' not in request.files:
            return jsonify({
                "success": False,
                "message": "No event poster provided"
            }), 400
            
        file = request.files['eventPoster']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "No file selected"
            }), 400
            
        if file and allowed_file(file.filename):
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Read file data and encode as base64 for MongoDB storage
            file_data = file.read()
            encoded_file = base64.b64encode(file_data).decode('utf-8')
            
            # Extract form data
            event_data = {
                "eventName": request.form.get("eventName"),
                "eventCategory": request.form.get("eventCategory"),
                "eventDescription": request.form.get("eventDescription"),
                "eventDateTime": request.form.get("eventDateTime"),
                "eventLocation": request.form.get("eventLocation"),
                "hostName": request.form.get("hostName"),
                "contactEmail": request.form.get("contactEmail"),
                "phoneNumber": request.form.get("phoneNumber"),
                "ticketPrice": request.form.get("ticketPrice"),
                "ticketQuantity": request.form.get("ticketQuantity"),
                "termsAccepted": True if request.form.get("termsAccepted") else False,
                
                # Image data
                "eventPoster": {
                    "filename": filename,
                    "contentType": file.content_type,
                    "data": encoded_file
                },
                
                # Metadata
                "created_at": datetime.now(),
                "created_by": session.get("user", "Anonymous")
            }
            
            # Insert the event into MongoDB
            result = events_collection.insert_one(event_data)
            
            # Check if insertion was successful
            if result.inserted_id:
                return jsonify({
                    "success": True,
                    "message": "Event created successfully",
                    "event_id": str(result.inserted_id)
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Failed to create event"
                }), 500
        else:
            return jsonify({
                "success": False,
                "message": "File type not allowed. Please upload an image file (png, jpg, jpeg, gif)"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@app.route("/send_data")
def send_data():
    try:
        # Retrieve all events from the events collection
        events = list(events_collection.find({}, {
            '_id': 0,  # Exclude MongoDB ID for JSON serialization
            'eventName': 1,
            'eventCategory': 1,
            'eventDescription': 1,
            'eventDateTime': 1,
            'eventLocation': 1,
            'hostName': 1,
            'contactEmail': 1,
            'phoneNumber': 1,
            'ticketPrice': 1,
            'ticketQuantity': 1,
            'termsAccepted': 1,
            'created_at': 1,
            'created_by': 1
        }))
        
        # Process events to handle date formatting and image data
        for event in events:
            # Convert datetime objects to string format for JSON serialization
            if 'created_at' in event and isinstance(event['created_at'], datetime):
                event['created_at'] = event['created_at'].isoformat()
                
            # Handle eventPoster data (if exists in the query)
            if 'eventPoster' in event and isinstance(event['eventPoster'], dict) and 'data' in event['eventPoster']:
                # Create a data URL for the image to be used in HTML
                event['eventPoster'] = f"data:{event['eventPoster']['contentType']};base64,{event['eventPoster']['data']}"
            else:
                event['eventPoster'] = None
                
        return jsonify(events)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route("/bookticket", methods=["POST"])
def book_ticket():
    try:
        # Check if user is logged in
        if "user" not in session:
            return jsonify({
                "success": False,
                "message": "Please log in to book tickets"
            }), 401

        # Get event details from form data
        event_id = request.form.get("eventID")
        event_name = request.form.get("eventName")
        ticket_price = request.form.get("ticketPrice")

        if not all([event_name, ticket_price]):
            return jsonify({
                "success": False,
                "message": "Missing required event information"
            }), 400

        # Store booking details in session for the booking form
        session['booking_details'] = {
            'eventID': event_id,
            'eventName': event_name,
            'ticketPrice': ticket_price
        }

        # Render the booking form template with event details
        return render_template(
            "join.html",  # This should be the filename of your second HTML template
            eventID=event_id,
            eventName=event_name,
            ticketPrice=ticket_price,
            username=session.get("user")
        )

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():
    try:
        # Check if user is logged in
        if "user" not in session:
            return jsonify({
                "success": False,
                "message": "Please log in to confirm booking"
            }), 401

        # Extract booking details from form
        booking_data = {
            "eventID": request.form.get("eventID"),
            "eventName": request.form.get("eventName"),
            "ticketCount": int(request.form.get("ticketCount")),
            "totalAmount": request.form.get("totalAmount"),
            "paymentMethod": request.form.get("paymentMethod"),
            "billingAddress": request.form.get("billingAddress"),
            "username": session.get("user"),
            "booking_date": datetime.now(),
            
            # Create list of ticket holders
            "ticketHolders": []
        }

        # Get ticket holder details
        for i in range(booking_data["ticketCount"]):
            holder = {
                "name": request.form.get(f"holderName{i}"),
                "email": request.form.get(f"holderEmail{i}"),
                "phone": request.form.get(f"holderPhone{i}")
            }
            booking_data["ticketHolders"].append(holder)

        # Create new collection for bookings if it doesn't exist
        if "bookings" not in db.list_collection_names():
            db.create_collection("bookings")

        # Insert booking into database
        bookings_collection = db["bookings"]
        result = bookings_collection.insert_one(booking_data)

        if result.inserted_id:
            # Update event ticket quantity in events collection
            events_collection.update_one(
                {"eventID": booking_data["eventID"]},
                {"$inc": {"ticketQuantity": -booking_data["ticketCount"]}}
            )

            return redirect(url_for("booking_confirmation", booking_id=str(result.inserted_id)))
        else:
            return jsonify({
                "success": False,
                "message": "Failed to save booking"
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route("/booking-confirmation")
def booking_confirmation():
    booking_id = request.args.get("booking_id")
    return render_template("booking_confirmation.html", booking_id=booking_id)
if __name__ == "__main__":
    app.run(debug=True)
