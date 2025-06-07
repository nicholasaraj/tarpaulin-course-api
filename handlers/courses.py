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

    new_course = datastore.Entity(key=client.key('courses'))
    new_course.update({
        "subject": data['subject'],
        "number": data['number'],
        "title": data['title'],
        "term": data['term'],
        "instructor_id": data['instructor_id'],
        "students": []
    })

    client.put(new_course)  # index all fields by default

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

    # Use default limit=3 for pagination
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
    
    # Return 404 if course doesn't exist
    if not course:
        return jsonify({"Error": "Not found"}), 404

    # Build and return the course object
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


## Functionality: Update a course
## Endpoint: PATCH /courses/:id
## Protection: Admin only
## Description: Partial update.
@courses_bp.route('/courses/<int:course_id>', methods=['PATCH'])
def update_course(course_id):
    client = datastore.Client()

    # Authentication
    payload = verify_jwt(request)
    if payload is None:
        return jsonify({"Error": "Unauthorized"}), 401

    sub = payload['sub']
    admin = next((u for u in client.query(kind='users').fetch() if u.get('sub') == sub), None)

    # Authorize
    if not admin or admin.get('role') != 'admin':
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Fetch the course
    course_key = client.key('courses', course_id)
    course = client.get(course_key)
    if not course:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Validate and handle body
    try:
        content = request.get_json()
    except:
        return jsonify({"Error": "The request body is invalid"}), 400
    if not isinstance(content, dict):
        return jsonify({"Error": "The request body is invalid"}), 400

    # Return course unchanged
    if content == {}:
        updated = {
            "id": course.key.id,
            "subject": course["subject"],
            "number": course["number"],
            "title": course["title"],
            "term": course["term"],
            "instructor_id": course["instructor_id"],
            "self": f"{request.host_url}courses/{course.key.id}".rstrip('/')
        }
        return jsonify(updated), 200

    # Validate instructor
    if 'instructor_id' in content:
        instructor_key = client.key('users', content['instructor_id'])
        instructor = client.get(instructor_key)
        if not instructor or instructor.get('role') != 'instructor':
            return jsonify({"Error": "The request body is invalid"}), 400

    # Apply updates
    for field in ['subject', 'number', 'title', 'term', 'instructor_id']:
        if field in content:
            course[field] = content[field]

    client.put(course)

    # Return updated course
    updated = {
        "id": course.key.id,
        "subject": course["subject"],
        "number": course["number"],
        "title": course["title"],
        "term": course["term"],
        "instructor_id": course["instructor_id"],
        "self": f"{request.host_url}courses/{course.key.id}".rstrip('/')
    }

    return jsonify(updated), 200



## Functionality: Delete a course
## Endpoint: DELETE /courses/:id
## Protection: Admin only
## Description: Delete course and delete enrollment info about the course.
@courses_bp.route('/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    client = datastore.Client()

    # Authentication
    payload = verify_jwt(request)
    if payload is None:
        return jsonify({"Error": "Unauthorized"}), 401

    sub = payload['sub']
    user = next((u for u in client.query(kind='users').fetch() if u.get('sub') == sub), None)

    # Authorization
    if not user or user.get('role') != 'admin':
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Fetch course
    course_key = client.key('courses', course_id)
    course = client.get(course_key)
    if not course:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Remove course from instructor
    instructor_id = course.get('instructor_id')
    if instructor_id:
        instructor_key = client.key('users', instructor_id)
        instructor = client.get(instructor_key)
        if instructor and 'courses' in instructor:
            instructor['courses'] = [c for c in instructor['courses'] if c != course_id]
            client.put(instructor)

    # Remove course from students
    for student_id in course.get('students', []):
        student_key = client.key('users', student_id)
        student = client.get(student_key)
        if student and 'courses' in student:
            student['courses'] = [c for c in student['courses'] if c != course_id]
            client.put(student)

    # Delete the course
    client.delete(course_key)
    return '', 204


## Functionality: Update enrollment in a course
## Endpoint: PATCH /courses/:id/students
## Protection: Admin. Or instructor of the course.
## Description: Enroll or disenroll students from the course.
@courses_bp.route('/courses/<int:course_id>/students', methods=['PATCH'])
def update_course_enrollment(course_id):
    client = datastore.Client()

    # Authentication
    payload = verify_jwt(request)
    if payload is None:
        return jsonify({"Error": "Unauthorized"}), 401

    sub = payload['sub']
    user = next((u for u in client.query(kind='users').fetch() if u.get('sub') == sub), None)

    # Fetch course
    course_key = client.key('courses', course_id)
    course = client.get(course_key)
    if not course or user is None:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Authorization
    is_admin = user.get('role') == 'admin'
    is_instructor = user.key.id == course.get('instructor_id')
    if not (is_admin or is_instructor):
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Validate body
    try:
        content = request.get_json()
        add_ids = content.get('add', [])
        remove_ids = content.get('remove', [])
    except:
        return jsonify({"Error": "The request body is invalid"}), 400

    if not isinstance(add_ids, list) or not isinstance(remove_ids, list):
        return jsonify({"Error": "Enrollment data is invalid"}), 409
    if len(add_ids) == 0 and len(remove_ids) == 0:
        return jsonify({"Error": "Enrollment data is invalid"}), 409
    if set(add_ids).intersection(remove_ids):
        return jsonify({"Error": "Enrollment data is invalid"}), 409

    # Validate that all IDs are existing students
    user_keys = [client.key('users', sid) for sid in set(add_ids + remove_ids)]
    user_entities = client.get_multi(user_keys)

    fetched_ids = {e.key.id for e in user_entities if e}
    valid_students = {e.key.id for e in user_entities if e and e.get('role') == 'student'}
    all_ids = set(add_ids + remove_ids)

    if not all_ids.issubset(fetched_ids) or not all_ids.issubset(valid_students):
        return jsonify({"Error": "Enrollment data is invalid"}), 409

    # Update course student list
    current_students = set(course.get('students', []))
    updated_students = current_students.union(add_ids).difference(remove_ids)
    course['students'] = list(updated_students)
    client.put(course)

    # Update student enrollment references
    for sid in add_ids:
        student_key = client.key('users', sid)
        student = client.get(student_key)
        if student:
            enrolled = set(student.get('courses', []))
            enrolled.add(course_id)
            student['courses'] = list(enrolled)
            client.put(student)

    for sid in remove_ids:
        student_key = client.key('users', sid)
        student = client.get(student_key)
        if student:
            enrolled = set(student.get('courses', []))
            enrolled.discard(course_id)
            student['courses'] = list(enrolled)
            client.put(student)

    return '', 200


## Functionality: Get enrollment for a course
## Endpoint: GET /courses/:id/students
## Protection: Admin. Or instructor of the course.
## Description: All students enrolled in the course.
@courses_bp.route('/courses/<int:course_id>/students', methods=['GET'])
def get_enrollment(course_id):
    client = datastore.Client()

    # Authentication
    payload = verify_jwt(request)
    if payload is None:
        return jsonify({"Error": "Unauthorized"}), 401

    sub = payload['sub']
    user = next((u for u in client.query(kind='users').fetch() if u.get('sub') == sub), None)

    # Fetch course
    course_key = client.key('courses', course_id)
    course = client.get(course_key)
    if not user or not course:
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Authorization
    is_admin = user.get('role') == 'admin'
    is_instructor = course.get('instructor_id') == user.key.id
    if not (is_admin or is_instructor):
        return jsonify({"Error": "You don't have permission on this resource"}), 403

    # Return enrolled students
    student_ids = course.get('students', [])
    return jsonify(student_ids), 200
