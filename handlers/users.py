from flask import Blueprint, request, jsonify, send_file
import requests
import os
from google.cloud import datastore
from utils import verify_jwt, AuthError
import io

users_bp = Blueprint('users', __name__, url_prefix='/users')

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")


## Functionality: User login
## Endpoint: POST /users/login
## Protection: Pre-created Auth0 users with username and password
## Description: Use Auth0 to issue JWTs. Referred to the example 
## app presented in Exploration - Implementing Auth Using JWTs.
@users_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"Error": "The request body is invalid"}), 400

    # Build the payload for Auth0 login request
    payload = {
        "grant_type": "password",
        "username": data['username'],
        "password": data['password'],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "openid profile email"
    }

    headers = {'content-type': 'application/json'}
    url = f'https://{AUTH0_DOMAIN}/oauth/token'
    resp = requests.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        return jsonify({"Error": "Unauthorized"}), 401

    token = resp.json().get('id_token') or resp.json().get('access_token')
    if not token:
        return jsonify({"Error": "Unauthorized"}), 401

    return jsonify({"token": token}), 200


## Functionality: Get all users
## Endpoint: GET /users
## Protection: Admin only
## Description: Summary information of all 9 users. No info 
## about avatar or courses.
@users_bp.route('', methods=['GET'])
def get_all_users():
    payload = verify_jwt(request)
    sub = payload['sub']

    client = datastore.Client()
    query = client.query(kind='users')
    users = list(query.fetch())

    # Confirm the requester is an admin user
    user = next((u for u in users if u['sub'] == sub), None)
    if not user or user.get('role') != 'admin':
        raise AuthError({
            "code": "forbidden",
            "description": "You don't have permission on this resource"
        }, 403)

    # Return minimal info (no avatar or courses)
    result = [{
        "id": u.key.id,
        "sub": u['sub'],
        "role": u['role']
    } for u in users]

    return jsonify(result), 200


## Functionality: Get a user
## Endpoint: GET /users/:id
## Protection: Admin. Or user with JWT matching id
## Description: Detailed info about the user, including
## avatar (if any) and courses (for instructors and students)
@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    payload = verify_jwt(request)
    requester_sub = payload['sub']

    client = datastore.Client()
    key = client.key('users', user_id)
    user = client.get(key)
    if not user:
        return jsonify({"Error": "Not found"}), 404

    # Verify the requester has access (self or admin)
    requester = next(
        (u for u in client.query(kind='users').fetch() if u['sub'] == requester_sub),
        None
    )
    if not requester or (requester['role'] != 'admin' and requester_sub != user['sub']):
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    result = {
        "id": user_id,
        "sub": user['sub'],
        "role": user['role']
    }

    # Check if an avatar exists for the user in GCS
    if BUCKET_NAME:
        try:
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(f'avatars/{user_id}.png')
            if blob.exists():
                host = request.host_url.rstrip('/')
                result["avatar_url"] = f"{host}/users/{user_id}/avatar"
        except Exception:
            pass  # Don't block the request if GCS check fails

    # Attach course URLs based on role
    if user['role'] == 'instructor':
        query = client.query(kind='courses')
        result["courses"] = [
            f"http://localhost:8080/courses/{c.key.id}"
            for c in query.fetch()
            if c.get('instructor_id') == user_id
        ]
    elif user['role'] == 'student':
        query = client.query(kind='courses')
        result["courses"] = [
            f"http://localhost:8080/courses/{c.key.id}"
            for c in query.fetch()
            if user_id in c.get('students', [])
        ]

    return jsonify(result), 200


## Functionality: Create/update a user’s avatar
## Endpoint: POST /users/:id/avatar
## Protection: User with JWT matching id
## Description: Upload file to Google Cloud Storage.
@users_bp.route('/<int:user_id>/avatar', methods=['POST'])
def upload_avatar(user_id):
    avatar_file = request.files.get('file')
    if avatar_file is None or avatar_file.filename == '':
        return jsonify({"Error": "The request body is invalid"}), 400

    payload = verify_jwt(request)
    if not payload:
        return jsonify({"Error": "Unauthorized"}), 401

    requester_sub = payload['sub']
    client = datastore.Client()
    user = client.get(client.key('users', user_id))
    if not user:
        return jsonify({"Error": "Not found"}), 404

    # Only the owner of the profile can upload their avatar
    if user['sub'] != requester_sub:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    if not BUCKET_NAME:
        return jsonify({"Error": "Server misconfiguration"}), 500

    # Upload the avatar file to GCS
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f'avatars/{user_id}.png')
    blob.upload_from_file(avatar_file, content_type=avatar_file.content_type)

    avatar_url = f"{request.host_url.rstrip('/')}/users/{user_id}/avatar"
    return jsonify({"avatar_url": avatar_url}), 200


## Functionality: Get a user’s avatar
## Endpoint: GET /users/:id/avatar
## Protection: User with JWT matching id
## Description: Read and return file from Google Cloud Storage.
@users_bp.route('/<int:user_id>/avatar', methods=['GET'])
def get_avatar(user_id):
    payload = verify_jwt(request)
    if not payload:
        return jsonify({"Error": "Missing or invalid JWT"}), 401

    requester_sub = payload['sub']
    client = datastore.Client()
    user = client.get(client.key('users', user_id))
    if not user:
        return jsonify({"Error": "Not found"}), 404

    if user['sub'] != requester_sub:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    if not BUCKET_NAME:
        return jsonify({"Error": "Server misconfiguration"}), 500

    # Retrieve the image file from GCS and stream it back
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f'avatars/{user_id}.png')

    if not blob.exists():
        return jsonify({"Error": "Not found"}), 404

    image_bytes = blob.download_as_bytes()
    return send_file(
        io.BytesIO(image_bytes),
        mimetype='image/png',
        as_attachment=False,
        download_name=f'user_{user_id}_avatar.png'
    )


## Functionality: Delete a user’s avatar
## Endpoint: DELETE /users/:id/avatar
## Protection: User with JWT matching id
## Description: Delete file from Google Cloud Storage
@users_bp.route('/<int:user_id>/avatar', methods=['DELETE'])
def delete_avatar(user_id):
    payload = verify_jwt(request)
    if not payload:
        return jsonify({"Error": "Missing or invalid JWT"}), 401

    requester_sub = payload['sub']
    client = datastore.Client()
    user = client.get(client.key('users', user_id))
    if not user:
        return jsonify({"Error": "Not found"}), 404

    if user['sub'] != requester_sub:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    if not BUCKET_NAME:
        return jsonify({"Error": "Server misconfiguration"}), 500

    # Remove the avatar blob from GCS if it exists
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f'avatars/{user_id}.png')

    if not blob.exists():
        return jsonify({"Error": "Not found"}), 404

    blob.delete()
    return '', 204
