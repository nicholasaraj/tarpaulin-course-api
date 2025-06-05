from flask import Blueprint, request, jsonify
from google.cloud import datastore
from utils import verify_jwt
import os

courses_bp = Blueprint('courses', __name__)


## Functionality: Create a course
## Endpoint: POST /courses
## Protection: Admin only
## Description: Create a course.
@courses_bp.route('/courses', methods=['POST'])
def create_course():
    payload = verify_jwt(request)
    if payload is None:
        return jsonify({"Error": "Unauthorized"}), 401

    client = datastore.Client()
    sub = payload['sub']
    requester = next(
        (u for u in client.query(kind='users').fetch() if u['sub'] == sub),
        None
    )

    if requester is None or requester['role'] != 'admin':
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    data = request.get_json()
    required_fields = ['subject', 'number', 'title', 'term', 'instructor_id']
    if not data or not all(f in data for f in required_fields):
        return jsonify({"Error": "The request body is invalid"}), 400

    # Check instructor_id is valid and corresponds to an instructor
    key = client.key('users', data['instructor_id'])
    instructor = client.get(key)
    if not instructor or instructor.get('role') != 'instructor':
        return jsonify({"Error": "The request body is invalid"}), 400

    # 👇 DO NOT use exclude_from_indexes at all
    new_course = datastore.Entity(key=client.key('courses'))
    new_course.update({
        "subject": data['subject'],
        "number": data['number'],
        "title": data['title'],
        "term": data['term'],
        "instructor_id": data['instructor_id'],
        "students": []
    })

    client.put(new_course)  # This will index all fields by default

    course_id = new_course.key.id
    result = dict(data)
    result['id'] = course_id
    result['self'] = f"{request.host_url.rstrip('/')}/courses/{course_id}"
    return jsonify(result), 201


## Functionality: Get all courses
## Endpoint: GET /courses
## Protection: Unprotected
## Description: Paginated using offset/limit. Page size is 3. 
## Ordered by "subject."  Doesn’t return info on course enrollment.
@courses_bp.route('/courses', methods=['GET'])
def get_all_courses():
    client = datastore.Client()
    query = client.query(kind='courses')

    # Fetch and sort all courses by subject
    all_courses = list(query.fetch())
    all_courses.sort(key=lambda c: c['subject'])

    # Use default limit=3 if none provided
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', default=3, type=int)

    # Paginate the sorted list
    paged_courses = all_courses[offset:offset + limit]

    courses = []
    for course in paged_courses:
        courses.append({
            "id": course.key.id,
            "subject": course['subject'],
            "number": course['number'],
            "title": course['title'],
            "term": course['term'],
            "instructor_id": course['instructor_id'],
            "self": f"{request.host_url.rstrip('/')}/courses/{course.key.id}"
        })

    result = {"courses": courses}

    # Add correct next link if more courses remain
    if (offset + limit) < len(all_courses):
        result["next"] = f"{request.host_url.rstrip('/')}/courses?limit={limit}&offset={offset + limit}"

    return jsonify(result), 200


## Functionality: Get a course
## Endpoint: GET /courses/:id
## Protection: Unprotected
## Description: Doesn’t return info on course enrollment.
@courses_bp.route('/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    client = datastore.Client()
    key = client.key('courses', course_id)
    course = client.get(key)
    if not course:
        return jsonify({"Error": "Not found"}), 404

    result = {
        "id": course_id,
        "subject": course['subject'],
        "number": course['number'],
        "title": course['title'],
        "term": course['term'],
        "instructor_id": course['instructor_id'],
        "self": f"{request.host_url.rstrip('/')}/courses/{course_id}"
    }
    return jsonify(result), 200
