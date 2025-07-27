from functools import wraps
from flask import request, jsonify, current_app
import jwt
import os

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

def token_required(f):
    """Decorator to require JWT token for protected routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = {
                'unit_id': data['unit_id'],
                'unit_type': data['unit_type']
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = {
                'unit_id': data['unit_id'],
                'unit_type': data['unit_type']
            }
            
            # Check if user is admin
            if current_user['unit_type'] != 'admin':
                return jsonify({'error': 'Admin privileges required'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def dispatch_or_admin_required(f):
    """Decorator to require dispatch or admin privileges"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = {
                'unit_id': data['unit_id'],
                'unit_type': data['unit_type']
            }
            
            # Check if user is dispatch or admin
            if current_user['unit_type'] not in ['dispatch', 'admin']:
                return jsonify({'error': 'Dispatch or admin privileges required'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def get_current_user_from_token():
    """Helper function to get current user from JWT token"""
    token = None
    
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(" ")[1]  # Bearer <token>
        except IndexError:
            return None
    
    if not token:
        return None
    
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return {
            'unit_id': data['unit_id'],
            'unit_type': data['unit_type']
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

