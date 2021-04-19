from keras.models import load_model
import numpy as np

from keras import backend as K


def soft_acc(y_true, y_pred):
    return K.mean(K.equal(K.round(y_true), K.round(y_pred)))


model1 = load_model('model1')
model2 = load_model('model2', custom_objects={'soft_acc':soft_acc})

# model.summary()


p1 = np.array([35])  #Seeds
p2 = np.array([5]) #fruitset

p1[0] = p1[0]/46.58510536 

print("p1",p1)
print("=======")
yyy = model1.predict(p1)

yyy = np.argmax(yyy,axis=1)
print(yyy)

yyyy = model2.predict(yyy)
print(yyyy)


yyyyP2 = model2.predict(p2)
print(yyyyP2)

# model.predict()


maxY = 8969.401842 
minY = 1637.704022

print((maxY - minY)*(yyyy) + minY)
print((maxY - minY)*(yyyyP2) + minY)
# print(yyyyP2)

#  SQL

#  seed , fruitset , model1 , model2 