from functools import wraps
from flask import request, jsonify
import jwt
from app.config import Config
from app.database import get_db_connection

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            data = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            current_user = data
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator
