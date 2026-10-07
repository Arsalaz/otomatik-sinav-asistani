import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:5000/generate', data=json.dumps({'grade': '5', 'subject': 'Sosyal Bilgiler', 'unit': '1. Unite', 'count': 1}).encode(), headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except Exception as e:
    print(e.read().decode())
