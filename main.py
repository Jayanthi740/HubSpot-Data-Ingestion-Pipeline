import os
import requests

from dotenv import load_dotenv

load_dotenv()

HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")

url = "https://api.hubapi.com/crm/v3/objects/contacts"

headers = {
    "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.get(
    url,
    headers=headers,
    params={"limit": 5}
)

print("Status Code:", response.status_code)

if response.status_code == 200:
    print("HubSpot connection successful!")

    data = response.json()

    for contact in data.get("results", []):
        print(contact)

else:
    print("Connection failed!")
    print(response.text)


