import json
import os
import sqlite3

from datetime import date, datetime
from flask import Flask, redirect, url_for, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
import board
import busio
import adafruit_thermal_printer
import serial

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin
)
from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
#from db import init_db_command
#from user import User

#configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
SERVER_IP_ADDRESS = os.environ.get("IP", None).strip()
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.config.from_pyfile('instance/config.py')

login_manager = LoginManager()
login_manager.init_app(app)

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return get_user(user_id)

def initializePrinter():
    ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
    uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=3000)
    printer = ThermalPrinter(uart, auto_warm_up=False)
    printer.warm_up()
    return printer

def checkPaper():
    if printer.has_paper():
        pass
    else:
        flash("The printer is out of paper. Tell Mr. Jones to fix it!","error")

def PrintHallPass(name, destination, date=date.today().strftime("%B %d, %Y"), time=datetime.now().strftime("%H:%M:%S")):
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.feed(2)
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("__(.)<   THIS IS A   <(.)__")
    printer.print("\___)    HALL PASS    (___/")
    printer.feed(2)
    printer.print(name)
    printer.print("is going to " + destination)
    printer.print("at " + time)
    printer.print("on " + date)
    printer.feed(2)
    printer.print("Questions? See Mr. Jones")
    printer.print("in room B130")
    printer.feed(4)

@app.context_processor
def inject_dict_for_all_templates():
    return dict(SERVER_IP_ADDRESS=SERVER_IP_ADDRESS)

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.before_request
def before_request():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)

@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
        
    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        #users_email = userinfo_response.json()["email"]
        #picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = get_user(unique_id)

    # Doesn't exist? Add it to the database.
    #if not User.get(unique_id):
    #    User.create(unique_id, users_name, users_email, picture)
    
        
    #exists = db.session.query(user.id).filter_by(id=user.id).first() is not None

    # Begin user session by logging the user in
    if user != None:
        login_user(user)
    else:
        flash("You just tried to login with an unknown userid: " + user.id,"error")

    # Send user back to homepage
    return redirect(url_for('pass_admin'))

@app.route("/", methods=["GET"])
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("pass_admin"))


@app.route("/helpQ", methods=["GET"])
def helpQ():
    if request.method == "GET":
        waiter_list = Waiter.query.all()
        #print(vars(waiter_list[0]))
        checkPaper()
        return render_template("helpQ.html", waiter_list = waiter_list, current_user=current_user)   


@app.route("/pass_admin", methods=["GET"])
@login_required
def pass_admin():
    if request.method == "GET":
        #new_pass_requests = HallPass.query.filter_by(approved_datetime == None).all()
        #approved_passes = HallPass.query.filter_by(approved_datetime != None).all()
        new_pass_requests = db.session.execute(db.select(HallPass).\
                                               filter(HallPass.approved_datetime == None)).scalars()
        approved_passes = db.session.execute(db.select(HallPass).\
                                             filter(HallPass.approved_datetime != None,HallPass.back_datetime == None)).\
                                                scalars()
        checkPaper()
        return render_template("pass_admin.html", new_pass_requests = new_pass_requests, approved_passes = approved_passes, current_user=current_user)

@app.route("/approve_pass/<id>", methods=["GET"])
@login_required
def approve_pass(id):
    print("approving pass",id)
    thisPass = HallPass.query.filter(id==id).first()
    thisPass.approved_datetime = datetime.now()
    db.session.commit()
    PrintHallPass(thisPass.name, thisPass.destination)
    return redirect(url_for("pass_admin"))  

@app.route("/return_pass/<id>", methods=["GET"])
@login_required
def return_pass(id):
    print("returning pass",id)
    thisPass = HallPass.query.filter(id==id).first()
    thisPass.back_datetime = datetime.now()
    db.session.commit()
    #PrintHallPass(thisPass.name, thisPass.destination)
    return redirect(url_for("pass_admin"))  

@app.route("/resetdb")
@login_required
def resetdb():
    with app.app_context():
        db.drop_all()
        db.create_all()
        adminUser = User(id='109593852925027537445',name="Admin")
        db.session.add(adminUser)
        db.session.commit()

###
#Initialize Printer
###
printer = initializePrinter()

# /// = relative path, //// = absolute path
#app.config['SQLALCHEMY_DATABASE_URI'] =\
#      'sqlite:////home/chris/Desktop/flask_app/http_student//instance/db.sqlite'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Waiter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class HallPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    request_datetime = db.Column(db.DateTime)
    approved_datetime = db.Column(db.DateTime)
    back_datetime = db.Column(db.DateTime)

def get_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    return user

class User(db.Model, UserMixin):
    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(100))

if __name__ == "__main__":
    #with app.app_context():
    #    db.drop_all()
    #    db.create_all()
    #    adminUser = User(id='109593852925027537445',name="Admin")
    #    db.session.add(adminUser)
    #    db.session.commit()
    app.run(port=443, host='0.0.0.0', debug=True,ssl_context="adhoc")

    #app.run(debug=True)