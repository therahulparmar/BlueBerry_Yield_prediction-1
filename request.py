import requests

url = 'http://localhost:5000/predict_api'
r = requests.post(url,json={'seed': 35, 'fruitset':0.5})

print(r.json())