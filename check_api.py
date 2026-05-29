import urllib.request
import json

try:
    response = urllib.request.urlopen('http://localhost:8000/api/health', timeout=2)
    data = json.loads(response.read())
    print('[OK] API is running')
    print('    Status:', data.get('status'))
    print('    Version:', data.get('version'))
    
    # Test subscriptions endpoint
    response = urllib.request.urlopen('http://localhost:8000/api/subscriptions?page_size=100', timeout=2)
    data = json.loads(response.read())
    print('[OK] API subscriptions endpoint')
    print('    Total:', data.get('total'))
    print('    Items:', len(data.get('items', [])))
    
except Exception as e:
    print('[INFO] API not running. Start it with: python api.py')
