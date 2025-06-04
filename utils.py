# utils.py
import os
import json
from six.moves.urllib.request import urlopen
from jose import jwt, JWTError
from flask import request

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
ALGORITHMS = ["RS256"]

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

def verify_jwt(request):
    if 'Authorization' not in request.headers:
        raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)

    auth_header = request.headers['Authorization'].split()
    if len(auth_header) != 2:
        raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)

    token = auth_header[1]

    try:
        jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        jwks = json.loads(jsonurl.read())
        unverified_header = jwt.get_unverified_header(token)
    except Exception:
        raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header.get("kid"):
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }

    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer=f"https://{AUTH0_DOMAIN}/"
            )
            return payload
        except JWTError:
            raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)

    raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)
