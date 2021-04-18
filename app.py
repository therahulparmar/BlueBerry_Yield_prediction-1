import numpy as np
from flask import Flask, request, jsonify, render_template
import pickle


from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import create_engine


app = Flask(__name__)




@app.route('/')
def home():
    return render_template('index.html')


if __name__ == "__main__":
    # db.create_all()
    app.run(debug=False)

