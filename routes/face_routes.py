"""
Face Recognition API Routes

API endpoints untuk face recognition dengan Swagger documentation.
"""
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from services.face_service import face_service

face_bp = Blueprint('face', __name__)


@face_bp.route('/register', methods=['POST'])
def register_face():
    """
    Register a new face
    ---
    tags:
      - Face
    summary: Daftarkan wajah baru
    description: |
      Endpoint untuk mendaftarkan wajah baru ke database.
      
      **Cara kerja:**
      1. Client kirim gambar dalam format base64
      2. Backend extract face encoding (128 angka)
      3. Encoding disimpan ke database PostgreSQL
      
      **Catatan:**
      - Jika user_id sudah ada, face encoding akan di-update
      - Gambar harus mengandung tepat 1 wajah
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - image
            - user_id
            - name
          properties:
            image:
              type: string
              description: Image in base64 format (dengan atau tanpa header data:image)
              example: "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
            user_id:
              type: string
              description: Unique user ID
              example: "user_001"
            name:
              type: string
              description: User name for display
              example: "John Doe"
    responses:
      200:
        description: Face registered successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            face_id:
              type: string
              example: "face_1"
            message:
              type: string
              example: "Face registered successfully"
            user_id:
              type: string
              example: "user_001"
      400:
        description: Bad request or no face detected
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: "No face detected in image"
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['image', 'user_id', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Extract JWT token from Authorization header (for Go backend)
        jwt_token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Register face
        result = face_service.register_face(
            base64_image=data['image'],
            user_id=data['user_id'],
            name=data['name'],
            jwt_token=jwt_token
        )
        
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@face_bp.route('/verify', methods=['POST'])
def verify_face():
    """
    Verify a face against database
    ---
    tags:
      - Face
    summary: Verifikasi wajah
    description: |
      Endpoint untuk memverifikasi wajah dengan database.
      
      **Cara kerja:**
      1. Client kirim gambar dalam format base64
      2. Backend extract face encoding
      3. Encoding dibandingkan dengan semua wajah di database
      4. Jika cocok, return user info
      
      **Tolerance:** 0.6 (semakin kecil = semakin strict)
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - image
          properties:
            image:
              type: string
              description: Image in base64 format
              example: "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    responses:
      200:
        description: Face verification result
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            matched:
              type: boolean
              example: true
            user_id:
              type: string
              example: "user_001"
            name:
              type: string
              example: "John Doe"
            confidence:
              type: number
              example: 85.5
            face_id:
              type: string
              example: "face_1"
      400:
        description: Bad request or no face detected
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            matched:
              type: boolean
              example: false
            error:
              type: string
              example: "No face detected in image"
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'matched': False,
                'error': 'No JSON data provided'
            }), 400
        
        if 'image' not in data:
            return jsonify({
                'success': False,
                'matched': False,
                'error': 'Missing required field: image'
            }), 400
        
        # Verify face
        result = face_service.verify_face(data['image'])
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'matched': False,
            'error': str(e)
        }), 500


@face_bp.route('/list', methods=['GET'])
def list_faces():
    """
    List all registered faces
    ---
    tags:
      - Face
    summary: List semua wajah terdaftar
    description: |
      Endpoint untuk melihat semua wajah yang terdaftar di database.
      
      **Catatan:** Tidak mengembalikan face encoding, hanya metadata.
    produces:
      - application/json
    responses:
      200:
        description: List of registered faces
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            count:
              type: integer
              example: 5
            faces:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  user_id:
                    type: string
                    example: "user_001"
                  name:
                    type: string
                    example: "John Doe"
                  created_at:
                    type: string
                    example: "2024-01-02T10:30:00"
    """
    try:
        faces = face_service.list_faces()
        
        return jsonify({
            'success': True,
            'count': len(faces),
            'faces': faces
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@face_bp.route('/<int:face_id>', methods=['DELETE'])
def delete_face(face_id):
    """
    Delete a face by ID
    ---
    tags:
      - Face
    summary: Hapus wajah berdasarkan ID
    description: Hapus face encoding dari database berdasarkan ID.
    produces:
      - application/json
    parameters:
      - name: face_id
        in: path
        type: integer
        required: true
        description: ID of face to delete
    responses:
      200:
        description: Face deleted successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Face 1 deleted successfully"
      404:
        description: Face not found
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: "Face not found"
    """
    try:
        result = face_service.delete_face(face_id)
        
        status_code = 200 if result.get('success') else 404
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@face_bp.route('/user/<user_id>', methods=['DELETE'])
def delete_face_by_user(user_id):
    """
    Delete a face by user ID
    ---
    tags:
      - Face
    summary: Hapus wajah berdasarkan user ID
    description: Hapus face encoding dari database berdasarkan user_id.
    produces:
      - application/json
    parameters:
      - name: user_id
        in: path
        type: string
        required: true
        description: User ID of face to delete
    responses:
      200:
        description: Face deleted successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "Face for user user_001 deleted successfully"
      404:
        description: Face not found
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: "Face for user user_001 not found"
    """
    try:
        result = face_service.delete_face_by_user_id(user_id)
        
        status_code = 200 if result.get('success') else 404
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
