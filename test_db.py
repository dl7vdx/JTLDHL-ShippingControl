import requests

API_KEY = 'xwjqiS3MuWfgZH1Tf38i6LPQGop5Lcr8'

r = requests.get('https://api-eu.dhl.com/track/shipments',
    headers={
        'DHL-API-Key': API_KEY,
        'Accept': 'application/json',
    },
    params={'trackingNumber': '00340434158009453867'})

print('Status:', r.status_code)
print('Response:', r.text[:500])