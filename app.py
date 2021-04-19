import numpy as np
from flask import Flask, request, jsonify, render_template
import pickle
from sklearn.preprocessing import StandardScaler
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import create_engine
from keras.models import load_model
from keras import backend as K

import numpy
from psycopg2.extensions import register_adapter, AsIs
def addapt_numpy_float64(numpy_float64):
    return AsIs(numpy_float64)
def addapt_numpy_int64(numpy_int64):
    return AsIs(numpy_int64)
register_adapter(numpy.float64, addapt_numpy_float64)
register_adapter(numpy.int64, addapt_numpy_int64)


def soft_acc(y_true, y_pred):
    return K.mean(K.equal(K.round(y_true), K.round(y_pred)))

app = Flask(__name__)
model1 = load_model('model1')
model2 = load_model('model2',custom_objects={'soft_acc':soft_acc})

scaler = pickle.load(open('scaler.pkl', 'rb'))


db = SQLAlchemy(app)
migrate = Migrate(app, db)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://akshay:@akshay1@localhost:5432/mydb'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ttzkojpddpctaj:c3e05efbdf687563415036f89fcf6b23d8eef98b9f94fa8716b91e4aed577751@ec2-54-224-120-186.compute-1.amazonaws.com:5432/d5td1eli3ontsg'



class yieldTable(db.Model):

    
    __tablename__ = 'yieldTable'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    seed = db.Column( ) 
    fruitset = db.Column()
    yield1 = db.Column()
    yield2 = db.Column()



    def __init__(self, seed, fruitset,yield1,yield2):
        self.seed = seed
        self.fruitset = fruitset
        self.yield1 = yield1
        self.yield2 = yield2



@app.route('/')
def home():
    return render_template('home.html')

@app.route('/predict',methods=['POST'])
def predict():
    

    features = [float(x) for x in request.form.values()]
    print(features)
    final_features = np.array(features)
    # final_features = scaler.transform(final_features) 

    print('final Features',final_features)
    seed = [features[0]/46.58510536 ]
    fruitset = [0]
    print("seed and fr", seed,fruitset)
    
    yyy = model1.predict(seed)

    yyy = np.argmax(yyy,axis=1)
    print(yyy)

    yyyy = model2.predict(yyy)
    # print(yyyy)


    yyyyP2 = model2.predict(fruitset)
    # print(yyyyP2)

    # model.predict()

    seed = seed[0]*46.58510536 
    maxY = 8969.401842 
    minY = 1637.704022

    yield11 = (maxY - minY)*(yyyy) + minY
    yield22 = (maxY - minY)*(yyyyP2) + minY
    
    # seed = seed[0]
    fruitset = fruitset[0]
    print("11 and 22 ", yield11[0][0],yield22[0][0])
    yield1 = float(yield11[0][0])
    yield2 = float(yield22[0][0])

    print("==")
    print(type(seed), type(fruitset),type(yield1))
    print("y",yield1,yield2)

    fruitset = 0

    entry = yieldTable(seed = seed, fruitset= fruitset,yield1= yield1 , yield2= yield2)

    db.session.add(entry)
    db.session.commit()

    # # person_details(predict[0][0],predict[0][1],predict[0][2],predict[0][3],output)

    # print(output)
    return render_template('home.html', prediction_text= f' Yield is  : {yield1} ')
        
@app.route('/predict_api',methods=['POST'])
def results():

    data = request.get_json(force=True)
    prediction = model1.predict([np.array(list(data.values()))])

    output = prediction[0]
    return jsonify(output)

if __name__ == "__main__":
    db.create_all()
    app.run(debug=False)



