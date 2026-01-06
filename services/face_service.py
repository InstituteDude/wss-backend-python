"""
Face Recognition Service - REAL MODE

Service untuk face recognition menggunakan dlib/face_recognition.
Akurat untuk production use.

Flow:
1. Frontend sends image to Python
2. Python extracts face encoding (dlib)
3. Python forwards encoding to Go backend for storage/verification
"""
import numpy as np
from PIL import Image
import io
import base64
import json
import requests
from typing import Optional, List, Dict
from models.database import db, FaceEncoding
from config import get_config

# Import face_recognition (dlib-based)
try:
    import face_recognition
    MOCK_MODE = False
    print("[FaceService] ✅ Using REAL face_recognition (dlib) - ACCURATE MODE!")
except ImportError:
    MOCK_MODE = True
    print("[FaceService] ⚠️ face_recognition not available, using MOCK MODE")

config = get_config()


class FaceService:
    """Service untuk operasi face recognition"""
    
    def __init__(self):
        self.tolerance = config.FACE_RECOGNITION_TOLERANCE
        self.mock_mode = MOCK_MODE
        self.go_backend_url = config.GO_BACKEND_URL
        self.go_api_key = config.GO_API_KEY
        print(f"[FaceService] Go Backend URL: {self.go_backend_url}")
    
    def decode_base64_image(self, base64_string: str) -> np.ndarray:
        """
        Decode base64 image ke numpy array
        """
        # Remove header if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_string)
        
        # Open image with PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return np.array(image)
    
    def extract_face_encoding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face encoding dari gambar menggunakan dlib
        Returns: numpy array of 128 floats atau None jika tidak ada wajah
        """
        if self.mock_mode:
            # MOCK: Return random encoding
            import hashlib
            image_hash = hashlib.md5(image.tobytes()).hexdigest()
            np.random.seed(int(image_hash[:8], 16))
            return np.random.rand(128).astype(np.float64)
        
        # REAL: Use face_recognition library
        face_locations = face_recognition.face_locations(image)
        
        if not face_locations:
            print("[FaceService] No face detected in image")
            return None
        
        print(f"[FaceService] Found {len(face_locations)} face(s)")
        
        # Get encoding of first face
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if not face_encodings:
            return None
        
        return face_encodings[0]
    
    def register_face(self, base64_image: str, user_id: str, name: str, jwt_token: str = None) -> Dict:
        """
        Registrasi wajah baru
        1. Extract face encoding (dlib)
        2. Forward encoding ke Go backend untuk storage
        3. Also store locally as backup
        """
        try:
            # Decode image
            image = self.decode_base64_image(base64_image)
            print(f"[FaceService] Image decoded: {image.shape}")
            
            # Extract face encoding
            encoding = self.extract_face_encoding(image)
            
            if encoding is None:
                return {
                    'success': False,
                    'error': 'No face detected in image'
                }
            
            print(f"[FaceService] Encoding extracted: {len(encoding)} dimensions")
            
            # Forward to Go backend
            go_result = self._forward_to_go_register(user_id, encoding, jwt_token)
            
            if not go_result.get('success', False):
                print(f"[FaceService] Go backend registration failed: {go_result.get('error')}")
                # Continue with local storage as fallback
            else:
                print(f"[FaceService] Successfully forwarded to Go backend")
            
            # Also store locally (Python DB) as backup
            existing = FaceEncoding.query.filter_by(user_id=user_id).first()
            
            if existing:
                existing.set_encoding(encoding)
                existing.name = name
                db.session.commit()
                local_face_id = existing.id
            else:
                face_record = FaceEncoding(user_id=user_id, name=name)
                face_record.set_encoding(encoding)
                db.session.add(face_record)
                db.session.commit()
                local_face_id = face_record.id
            
            return {
                'success': True,
                'face_id': f'face_{local_face_id}',
                'go_backend_synced': go_result.get('success', False),
                'message': 'Face registered successfully',
                'user_id': user_id,
                'accurate_mode': not self.mock_mode
            }
                
        except Exception as e:
            db.session.rollback()
            print(f"[FaceService] Error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _forward_to_go_register(self, user_id: str, encoding: np.ndarray, jwt_token: str = None) -> Dict:
        """
        Forward face encoding ke Go backend untuk storage
        Go endpoint: POST /api/users/{user_id}/biometrics
        """
        try:
            # Format template_data sesuai Go backend
            template_data = json.dumps({
                "encoding": encoding.tolist(),
                "algorithm": "dlib"
            })
            
            headers = {"Content-Type": "application/json"}
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"
            
            response = requests.post(
                f"{self.go_backend_url}/api/users/{user_id}/biometrics",
                json={
                    "biometric_type": "face",
                    "template_data": template_data
                },
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Go backend returned {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to Go backend: {str(e)}"}
    
    def verify_face(self, base64_image: str, user_id: str = None, use_go_backend: bool = True) -> Dict:
        """
        Verifikasi wajah
        1. Extract face encoding (dlib)
        2. Try Go backend first (if configured)
        3. Fallback to local database
        """
        try:
            # Decode image
            image = self.decode_base64_image(base64_image)
            
            # Extract face encoding
            encoding = self.extract_face_encoding(image)
            
            if encoding is None:
                return {
                    'success': False,
                    'matched': False,
                    'error': 'No face detected in image'
                }
            
            # Try Go backend first
            if use_go_backend and self.go_api_key:
                go_result = self._forward_to_go_verify(encoding, user_id)
                if go_result.get('success'):
                    return go_result
                print(f"[FaceService] Go backend verify failed, using local: {go_result.get('error')}")
            
            # Fallback: Use local database
            return self._verify_local(encoding)
                
        except Exception as e:
            print(f"[FaceService] Verify error: {e}")
            return {
                'success': False,
                'matched': False,
                'error': str(e)
            }
    
    def _forward_to_go_verify(self, encoding: np.ndarray, user_id: str = None) -> Dict:
        """
        Forward face encoding ke Go backend untuk verification
        Go endpoint: POST /api/biometrics/verify
        """
        try:
            template_data = json.dumps({
                "encoding": encoding.tolist(),
                "algorithm": "dlib"
            })
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.go_api_key
            }
            
            payload = {
                "biometric_type": "face",
                "template_data": template_data
            }
            if user_id:
                payload["user_id"] = user_id
            
            response = requests.post(
                f"{self.go_backend_url}/api/biometrics/verify",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'matched': data.get('matched', False),
                    'user_id': data.get('user_id'),
                    'name': data.get('name'),
                    'confidence': data.get('confidence', 0),
                    'source': 'go_backend',
                    'accurate_mode': not self.mock_mode
                }
            else:
                return {"success": False, "error": f"Go backend returned {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Failed to connect to Go backend: {str(e)}"}
    
    def _verify_local(self, encoding: np.ndarray) -> Dict:
        """Verify against local Python database (fallback)"""
        all_faces = FaceEncoding.query.all()
        
        if not all_faces:
            return {
                'success': True,
                'matched': False,
                'message': 'No registered faces in database'
            }
        
        known_encodings = [face.get_encoding() for face in all_faces]
        
        if self.mock_mode:
            distances = [np.linalg.norm(known - encoding) for known in known_encodings]
            matches = [d < 1.0 for d in distances]
        else:
            matches = face_recognition.compare_faces(
                known_encodings, encoding, tolerance=self.tolerance
            )
            distances = face_recognition.face_distance(known_encodings, encoding)
        
        if True in matches:
            best_match_index = np.argmin(distances)
            best_match = all_faces[best_match_index]
            confidence = max(0, (1 - distances[best_match_index]) * 100)
            
            print(f"[FaceService] Match found: {best_match.name} ({confidence:.1f}%)")
            
            return {
                'success': True,
                'matched': True,
                'user_id': best_match.user_id,
                'name': best_match.name,
                'confidence': round(float(confidence), 2),
                'face_id': f'face_{best_match.id}',
                'source': 'local_python',
                'accurate_mode': not self.mock_mode
            }
        else:
            return {
                'success': True,
                'matched': False,
                'message': 'Face not recognized',
                'source': 'local_python',
                'accurate_mode': not self.mock_mode
            }
    
    def list_faces(self) -> List[Dict]:
        """List semua wajah yang terdaftar"""
        faces = FaceEncoding.query.all()
        return [face.to_dict() for face in faces]
    
    def delete_face(self, face_id: int) -> Dict:
        """Hapus wajah dari database"""
        try:
            face = FaceEncoding.query.get(face_id)
            
            if not face:
                return {'success': False, 'error': 'Face not found'}
            
            db.session.delete(face)
            db.session.commit()
            
            return {'success': True, 'message': f'Face {face_id} deleted successfully'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def delete_face_by_user_id(self, user_id: str) -> Dict:
        """Hapus wajah berdasarkan user_id"""
        try:
            face = FaceEncoding.query.filter_by(user_id=user_id).first()
            
            if not face:
                return {'success': False, 'error': f'Face for user {user_id} not found'}
            
            db.session.delete(face)
            db.session.commit()
            
            return {'success': True, 'message': f'Face for user {user_id} deleted successfully'}
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}


# Singleton instance
face_service = FaceService()
