import secrets
SQLALCHEMY_DATABASE_URI = 'sqlite:////home/chris/Desktop/flask_app/http_student//instance/db.sqlite'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = secrets.token_hex(16)