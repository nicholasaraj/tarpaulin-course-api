from flask import Blueprint, request, jsonify
import requests
import os
from google.cloud import datastore
from utils import verify_jwt, AuthError

users_bp = Blueprint('users', __name__, url_prefix='/users')

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')


@users_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"Error": "The request body is invalid"}), 400

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


@users_bp.route('', methods=['GET'])
def get_all_users():
    payload = verify_jwt(request)
    sub = payload['sub']

    client = datastore.Client()
    key = client.key('users', sub)
    user = client.get(key)

    if not user or user.get('role') != 'admin':
        raise AuthError({
            "code": "forbidden",
            "description": "You don't have permission on this resource"
        }, 403)

    # fetch all users
    query = client.query(kind='users')
    users = list(query.fetch())

    result = [{
        "id": u.key.id,
        "sub": u['sub'],
        "role": u['role']
    } for u in users]

    return jsonify(result), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    payload = verify_jwt(request)
    requester_sub = payload['sub']

    client = datastore.Client()

    # 🔍 Fetch the user by numeric ID (not sub)
    key = client.key('users', user_id)
    user = client.get(key)
    if not user:
        return jsonify({"Error": "Not found"}), 404

    # 🔐 Check if requester is the same user or admin
    requester_key = client.key('users', requester_sub)
    requester = client.get(requester_key)
    if not requester or (requester['role'] != 'admin' and requester_sub != user['sub']):
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # 🧱 Build response
    result = {
        "id": user_id,
        "sub": user['sub'],
        "role": user['role']
    }

    # 🖼️ Add avatar_url if avatar exists
    from google.cloud import storage
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if bucket_name:
        avatar_path = f"avatars/{user_id}.png"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(avatar_path)
        if blob.exists():
            result["avatar_url"] = f"http://localhost:8080/users/{user_id}/avatar"

    # 📘 Add course URLs if student or instructor
    if user['role'] in ['student', 'instructor']:
        course_query = client.query(kind='courses')
        if user['role'] == 'student':
            course_query.add_filter('students', '=', user_id)
        else:
            course_query.add_filter('instructor_id', '=', user_id)

        course_links = [
            f"http://localhost:8080/courses/{course.key.id}"
            for course in course_query.fetch()
        ]
        result["courses"] = course_links

    return jsonify(result), 200
