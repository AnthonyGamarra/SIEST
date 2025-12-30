from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

def get_serializer():
    return URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'],
        salt='dashboard-code'
    )

def encode_code(code: str) -> str:
    s = get_serializer()
    return s.dumps(code)

def decode_code(token: str, max_age=3600):
    s = get_serializer()
    try:
        return s.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
