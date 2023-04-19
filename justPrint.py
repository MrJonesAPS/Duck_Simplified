import board
import busio
import adafruit_thermal_printer
import serial

#Initialize Printer
ThermalPrinter = adafruit_thermal_printer.get_printer_class(2.68)
uart = serial.Serial("/dev/serial0", baudrate=19200, timeout=0)
printer = ThermalPrinter(uart, auto_warm_up=False, dot_print_s = 0, byte_delay_s = 0)
printer.warm_up()

#Set font size
printer.size = adafruit_thermal_printer.SIZE_LARGE
printer.justify = adafruit_thermal_printer.JUSTIFY_CENTER
printer.double_height = True
printer.double_width = True

#Print
printer.feed(2)
printer.print("__(.)<  <(.)__")
printer.print("\___)    (___/")
printer.feed(2)