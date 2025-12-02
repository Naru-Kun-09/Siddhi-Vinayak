from flask import Blueprint, request, jsonify
import bcrypt
import jwt
from datetime import datetime, timedelta
from app.database import get_db_connection
from app.config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    if not phone or not password:
        return jsonify({'error': 'Phone and password required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE phone = %s AND is_active = TRUE", (phone,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = jwt.encode({
        'user_id': user['id'],
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(days=7)
    }, Config.JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'phone': user['phone'],
            'email': user['email'],
            'role': user['role']
        }
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200
