import os
import requests
from google.cloud import datastore
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
PASSWORD = os.getenv('USER_PASSWORD')

users_to_create = [
    ("admin1@osu.com", "admin"),
    ("instructor1@osu.com", "instructor"),
    ("instructor2@osu.com", "instructor"),
    ("student1@osu.com", "student"),
    ("student2@osu.com", "student"),
    ("student3@osu.com", "student"),
    ("student4@osu.com", "student"),
    ("student5@osu.com", "student"),
    ("student6@osu.com", "student"),
]

def get_id_token(email):
    url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "password",
        "username": email,
        "password": PASSWORD,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "openid profile email"
    }
    headers = { 'content-type': 'application/json' }
    resp = requests.post(url, json=payload, headers=headers)

    try:
        return resp.json()['id_token']
    except KeyError:
        print(f"Failed to get id_token for {email}")
        print("Status Code:", resp.status_code)
        print("Response JSON:", resp.json())
        raise


def get_sub_from_token(id_token):
    return jwt.get_unverified_claims(id_token)['sub']

users_to_create = [
    ("admin1@osu.com", "admin"),
    ("instructor1@osu.com", "instructor"),
    ("instructor2@osu.com", "instructor"),
    ("student1@osu.com", "student"),
    ("student2@osu.com", "student"),
    ("student3@osu.com", "student"),
    ("student4@osu.com", "student"),
    ("student5@osu.com", "student"),
    ("student6@osu.com", "student"),
]

def seed():
    client = datastore.Client()
    for i, (email, role) in enumerate(users_to_create, start=1):  # 👈 1 through 9
        print(f"Creating {email}...")

        id_token = get_id_token(email)
        sub = get_sub_from_token(id_token)

        key = client.key('users', i)  # 👈 numeric key = 1 through 9
        entity = datastore.Entity(key=key)
        entity.update({
            'sub': sub,
            'role': role
        })
        client.put(entity)
        print(f"  -> Added {role} with sub: {sub} and id: {entity.key.id}")

if __name__ == "__main__":
    seed()
