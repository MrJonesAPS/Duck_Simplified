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

app = Flask(__name__)
app.config.from_pyfile('instance/config.py')

def initializePrinter():
    ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
    uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=3000)
    printer = ThermalPrinter(uart, auto_warm_up=False)
    printer.warm_up()
    return printer

def checkPaper():
    if printer.has_paper():
        #flash("Printer has paper")
        pass
    else:
        flash("The printer is out of paper. Tell Mr. Jones to fix it!","error")

@app.route("/", methods=["GET"])
@app.route("/helpQ", methods=["GET"])
def helpQ():
    if request.method == "GET":
        waiter_list = Waiter.query.all()
        checkPaper()
        return render_template("helpQ.html", waiter_list = waiter_list)

@app.route("/add", methods=["POST"])
def add():
    #create a new Waiter and add it to the queue
    name = request.form.get("name")
    new_waiter = Waiter(name=name)
    db.session.add(new_waiter)
    db.session.commit()

    #print a message saying that the user was added
    message = "Added "+ name + " to queue"
    printer.print(message)
    printer.feed(2)

    #redirect
    return redirect(url_for("helpQ"))

@app.route("/joinQ", methods=["GET"])
def joinQ():
    checkPaper()
    return render_template("joinQ.html")

@app.route("/request_pass", methods=["GET","POST"])
def request_pass():
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
        flash("Hi " + name + " your pass for " + destination + " has been created. You can now ask Mr Jones to approve it")
        return redirect(url_for("helpQ"))    

###
#Initialize Printer
###
printer = initializePrinter()

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
    rejected = db.Column(db.Boolean)

if __name__ == "__main__":
    app.run(port=80, host='0.0.0.0', debug=True)