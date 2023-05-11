import json
import os
import sqlite3

from datetime import date, datetime, timedelta
from flask import Flask, redirect, url_for, render_template, request, flash
from flask_sqlalchemy import SQLAlchemy
import board
import busio
import adafruit_thermal_printer
import serial
import requests

app = Flask(__name__)
app.config.from_pyfile('instance/config.py')

def initializePrinter():
    ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
    uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=0)
    printer = ThermalPrinter(uart, auto_warm_up=False, dot_print_s = 0.01, byte_delay_s = 0)
    printer.warm_up()
    return printer

def checkPaper():
    if printer.has_paper():
        pass
    else:
        flash("The printer is out of paper. Tell Mr. Jones to fix it!","error")

def PrintHallPass(name, destination, date, time):
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("__(.)<   THIS IS A   <(.)__")
    printer.print("\___)    HALL PASS    (___/")
    printer.feed(1)
    printer.print(name)
    printer.print("is going to " + destination)
    printer.print("at " + time)
    printer.print("on " + date)
    printer.feed(1)
    printer.print("Questions? See Mr. Jones")
    printer.print("in room B130")
    printer.feed(2)

def PrintWPPass(name, date):
    ###
    #I got some of this code from stackoverflow
    #https://stackoverflow.com/questions/5891555/display-the-date-like-may-5th-using-pythons-strftime
    ###
    def suffix(d):
        return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

    def custom_strftime(format, t):
        return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.print("__(.)<   WARRIOR")
    printer.print("\___)    PASS")
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.feed(3)
    printer.print(name)
    printer.print("is invited")
    printer.print("to room B130")
    printer.print("on")
    printer.print(custom_strftime('%a, %B {S}', date))
    printer.feed(3)
    printer.print("Questions?") 
    printer.print("See Mr. Jones")
    printer.print("in room B130")
    printer.feed(2)



@app.route("/", methods=["GET"])
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/helpQ", methods=["GET"])
def helpQ():
    if request.method == "GET":
        waiter_list = Waiter.query.all()
        checkPaper()
        return render_template("helpQ.html", waiter_list = waiter_list, current_user=current_user)   


@app.route("/pass_admin", methods=["GET"])
def pass_admin():
    if request.method == "GET":
        new_pass_requests = db.session.execute(db.select(HallPass).\
                                               filter(HallPass.approved_datetime == None,
                                                      HallPass.rejected.is_(False))).scalars()
        approved_passes = db.session.execute(db.select(HallPass).\
                                             filter(HallPass.approved_datetime != None,
                                                    HallPass.back_datetime == None)).scalars()
        
        new_WP_requests = db.session.execute(db.select(WPPass).\
                                               filter(WPPass.approved_datetime == None,
                                                      WPPass.rejected.is_(False))).scalars()

        approved_WP = db.session.execute(db.select(WPPass).\
                                               filter(WPPass.approved_datetime != None,
                                                      WPPass.rejected.is_(False))).scalars()


        checkPaper()
        
        #####
        #When a student has an unapproved request, quack
        #####
        firstRecord_PassRequests = db.session.execute(db.select(HallPass).\
                                               filter(HallPass.approved_datetime == None,
                                                    HallPass.rejected.is_(False))).first()
        
        should_we_quack = (firstRecord_PassRequests != None)

        return render_template("pass_admin.html",
                               new_pass_requests = new_pass_requests,
                               approved_passes = approved_passes,
                               new_WP_requests = new_WP_requests,
                               approved_WP = approved_WP,
                               should_we_quack=should_we_quack,
                               now = datetime.now,
                               int = int,
                               str = str
                               )

@app.route("/approve_pass/<id>", methods=["GET"])
def approve_pass(id):
    print("approving pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.approved_datetime = datetime.now()
    db.session.commit()
    nowTime = datetime.now().strftime("%I:%M %p")
    nowDate = date.today().strftime("%B %d, %Y")
    PrintHallPass(thisPass.name, thisPass.destination, nowDate, nowTime)
    return redirect(url_for("pass_admin"))  

@app.route("/reject_pass/<id>", methods=["GET"])
def reject_pass(id):
    print("rejecting pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.rejected = True
    db.session.commit()
    return redirect(url_for("pass_admin"))  

@app.route("/approve_wp/<id>", methods=["GET"])
def approve_wp(id):
    print("approving WP",id)
    thisPass = db.session.execute(db.select(WPPass).filter_by(id=id)).scalar_one()
    print(thisPass)
    thisPass.approved_datetime = datetime.now()
    db.session.commit()
    PrintWPPass(thisPass.name, thisPass.date)
    return redirect(url_for("pass_admin"))  

@app.route("/reject_wp/<id>", methods=["GET"])
def reject_wp(id):
    print("rejecting WP",id)
    thisPass = db.session.execute(db.select(WPPass).filter_by(id=id)).scalar_one()
    print(thisPass)
    thisPass.rejected = True #Why doesn't this work???
    db.session.commit()
    return redirect(url_for("pass_admin"))  

@app.route("/return_pass/<id>", methods=["GET"])
def return_pass(id):
    print("returning pass",id)
    thisPass = db.session.execute(db.select(HallPass).filter_by(id=id)).scalar_one()
    thisPass.back_datetime = datetime.now()
    db.session.commit()
    return redirect(url_for("pass_admin"))  

@app.route("/request_pass", methods=["GET","POST"])
def request_pass():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        checkPaper()
        return render_template("request_pass.html")
    elif request.method == "POST":
        name = request.form.get("name")
        destination = request.form.get("destination")
        request_datetime = datetime.now()
        new_pass_request = HallPass(name=name, destination=destination,request_datetime=request_datetime,rejected=False)
        db.session.add(new_pass_request)
        db.session.commit()
        #after you commit, the id is set. I'll use my existing approval code from here
        return approve_pass(new_pass_request.id)  

@app.route("/request_wp", methods=["GET","POST"])
def request_wp():
    #this page for the admin both creates and approves the request
    if request.method == "GET":
        checkPaper()
        return render_template("request_wp.html")
    elif request.method == "POST":
        name = request.form.get("name")
        date = datetime.strptime(request.form.get("date"), '%Y-%m-%d').date()
        request_datetime = datetime.now()
        new_wp_pass_request = WPPass(name=name, date=date,request_datetime=request_datetime,rejected=False)
        db.session.add(new_wp_pass_request)
        db.session.commit()
        return approve_wp(new_wp_pass_request.id)
        

@app.route("/resetdb")
def resetdb():
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()
        flash("The DB was just reset","error")
        return redirect(url_for("home"))

@app.route("/summary")
def summary():
    approved_passes = db.session.execute(db.select(HallPass).\
                                            filter(HallPass.approved_datetime != None)).scalars()
        
    approved_WP = db.session.execute(db.select(WPPass).\
                                            filter(WPPass.approved_datetime != None)).scalars()
    
    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("SUMMARY FOR")
    printer.print(date.today().strftime("%B %d, %Y"))
    printer.justify = adafruit_thermal_printer.JUSTIFY_LEFT
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.print("Hall Passes:")
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    for p in approved_passes:
        printer.print(p.name + " | " + p.destination)
        goneTime = p.back_datetime - p.approved_datetime
        printer.underline = adafruit_thermal_printer.UNDERLINE_THICK
        printer.print(p.approved_datetime.strftime("%B %d, %y %I:%M %p") + "(" + str(int(goneTime.total_seconds() // 60)) + " mins)")
        printer.underline = None

    printer.feed(1)
    printer.size = adafruit_thermal_printer.SIZE_MEDIUM
    printer.print("Warrior's passes:")
    printer.size = adafruit_thermal_printer.SIZE_SMALL
    printer.feed(1)
    for p in approved_WP:
        printer.print(">" + p.name + "|" + p.date.strftime("%B %d, %Y"))

    printer.size = adafruit_thermal_printer.SIZE_LARGE
    printer.feed(1)
    printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
    printer.print("END SUMMARY")
    printer.feed(2)
    flash("Summary print successful")
    return redirect(url_for("home"))

###
#Initialize Printer
###
printer = initializePrinter()

db = SQLAlchemy(app)

class Waiter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    completed_datetime = db.Column(db.DateTime)

class HallPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    request_datetime = db.Column(db.DateTime)
    approved_datetime = db.Column(db.DateTime)
    back_datetime = db.Column(db.DateTime)
    rejected = db.Column(db.Boolean)

class WPPass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    date = db.Column(db.Date)
    request_datetime = db.Column(db.DateTime)
    approved_datetime = db.Column(db.DateTime)
    rejected = db.Column(db.Boolean)

if __name__ == "__main__":
    app.run(port=8000, host='0.0.0.0', debug=True)