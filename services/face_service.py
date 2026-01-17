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

# Import MediaPipe for hand gesture detection
mp_hands = None
MEDIAPIPE_AVAILABLE = False
try:
    import mediapipe as mp
    if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'hands'):
        mp_hands = mp.solutions.hands
        MEDIAPIPE_AVAILABLE = True
        print("[FaceService] ✅ MediaPipe Hands available for gesture detection!")
    else:
        print("[FaceService] ⚠️ MediaPipe installed but solutions.hands not available")
except (ImportError, AttributeError) as e:
    print(f"[FaceService] ⚠️ MediaPipe not available: {e}")

# Import DeepFace for anti-spoofing detection (Full Accuracy Mode)
DEEPFACE_AVAILABLE = False
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("[FaceService] ✅ DeepFace available for anti-spoofing detection!")
except ImportError as e:
    print(f"[FaceService] ⚠️ DeepFace not available: {e}")

# Import OpenCV for texture-based anti-spoofing (fallback)
OPENCV_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
    print("[FaceService] ✅ OpenCV available for texture analysis!")
except ImportError as e:
    print(f"[FaceService] ⚠️ OpenCV not available: {e}")

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
    
    def check_mouth_liveness(self, image_base64: str, required_state: str) -> Dict:
        """
        Check liveness by detecting mouth open/close state.
        
        Uses dlib 68-point facial landmarks:
        - Upper inner lip: points 62, 63
        - Lower inner lip: points 66, 67
        - Mouth width: points 48, 54
        
        Anti-spoofing: Photos cannot open/close mouth on demand!
        
        Args:
            image_base64: Base64 encoded image
            required_state: 'open' or 'closed'
            
        Returns:
            Dict with success, is_live, detected_state, mouth_ratio
        """
        try:
            if self.mock_mode:
                return {
                    'success': True,
                    'is_live': True,
                    'detected_state': required_state,
                    'mouth_ratio': 0.5,
                    'message': 'Mock mode - liveness bypassed'
                }
            
            if required_state not in ['open', 'closed']:
                return {
                    'success': False,
                    'is_live': False,
                    'error': "required_state must be 'open' or 'closed'"
                }
            
            print(f"[MouthLiveness] Checking for mouth {required_state}...")
            
            # Decode image
            image = self.decode_base64_image(image_base64)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(image)
            
            if not face_locations:
                print("[MouthLiveness] No face detected!")
                return {
                    'success': True,
                    'is_live': False,
                    'has_face': False,
                    'detected_state': None,
                    'message': 'No face detected in image'
                }
            
            print(f"[MouthLiveness] Face detected at {face_locations[0]}")
            
            # Get facial landmarks
            face_landmarks_list = face_recognition.face_landmarks(image, face_locations)
            
            if not face_landmarks_list:
                print("[MouthLiveness] No landmarks detected!")
                return {
                    'success': True,
                    'is_live': False,
                    'has_face': True,
                    'detected_state': None,
                    'message': 'Could not detect facial landmarks'
                }
            
            landmarks = face_landmarks_list[0]
            
            # Get mouth landmarks
            # face_recognition uses different landmark names than dlib's 68-point
            top_lip = landmarks.get('top_lip', [])
            bottom_lip = landmarks.get('bottom_lip', [])
            
            if not top_lip or not bottom_lip:
                return {
                    'success': True,
                    'is_live': False,
                    'has_face': True,
                    'detected_state': None,
                    'message': 'Could not detect mouth landmarks'
                }
            
            # Calculate mouth opening ratio
            # Top lip inner points (indices 8, 9, 10 in face_recognition's top_lip)
            # Bottom lip inner points (indices 8, 9, 10 in face_recognition's bottom_lip)
            # The inner lip points are the last few points in each lip array
            
            # Get inner lip points (middle section)
            top_inner = top_lip[9] if len(top_lip) > 9 else top_lip[-1]  # Inner top middle
            bottom_inner = bottom_lip[9] if len(bottom_lip) > 9 else bottom_lip[-1]  # Inner bottom middle
            
            # Calculate vertical distance (mouth opening)
            mouth_height = abs(bottom_inner[1] - top_inner[1])
            
            # Calculate horizontal distance (mouth width)
            left_corner = top_lip[0]
            right_corner = top_lip[6] if len(top_lip) > 6 else top_lip[-1]
            mouth_width = abs(right_corner[0] - left_corner[0])
            
            # Mouth ratio = height / width
            # Higher ratio = mouth more open
            mouth_ratio = mouth_height / mouth_width if mouth_width > 0 else 0
            
            print(f"[MouthLiveness] Mouth height: {mouth_height}px, width: {mouth_width}px")
            print(f"[MouthLiveness] Mouth ratio: {mouth_ratio:.3f}")
            
            # Thresholds
            OPEN_THRESHOLD = 0.25  # Mouth is considered open if ratio > 0.25
            CLOSED_THRESHOLD = 0.15  # Mouth is considered closed if ratio < 0.15
            
            # Determine detected state
            if mouth_ratio > OPEN_THRESHOLD:
                detected_state = 'open'
            elif mouth_ratio < CLOSED_THRESHOLD:
                detected_state = 'closed'
            else:
                detected_state = 'neutral'  # In between
            
            print(f"[MouthLiveness] Detected state: {detected_state}, required: {required_state}")
            
            # Check if detected matches required
            is_live = (detected_state == required_state)
            
            # For 'closed', also accept 'neutral' as close enough
            if required_state == 'closed' and detected_state in ['closed', 'neutral']:
                is_live = True
            
            return {
                'success': True,
                'is_live': is_live,
                'has_face': True,
                'detected_state': detected_state,
                'required_state': required_state,
                'mouth_ratio': round(float(mouth_ratio), 3),
                'message': f'Mouth is {detected_state}!' if is_live 
                          else f'Mouth is {detected_state}, but need {required_state}'
            }
            
        except Exception as e:
            print(f"[MouthLiveness] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'is_live': False,
                'error': str(e)
            }

    def check_anti_spoofing(self, image_base64: str) -> Dict:
        """
        Check if image is real or spoofed using DeepFace anti-spoofing.
        Falls back to OpenCV texture analysis if DeepFace not available.
        
        Uses MiniVision Silent-Face-Anti-Spoofing models to detect:
        - Printed photos
        - Screen/monitor displays
        - Video replays
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Dict with success, is_real, antispoof_score, message
        """
        try:
            # Decode image first
            image = self.decode_base64_image(image_base64)
            
            # Try DeepFace first (most accurate)
            if DEEPFACE_AVAILABLE:
                try:
                    return self._check_anti_spoofing_deepface(image)
                except Exception as deepface_err:
                    print(f"[AntiSpoof] ⚠️ DeepFace failed: {deepface_err}")
                    print("[AntiSpoof] Falling back to OpenCV...")
                    # Fallthrough to OpenCV
            
            # Fallback to OpenCV texture analysis
            if OPENCV_AVAILABLE:
                return self._check_anti_spoofing_opencv(image)
            
            # No anti-spoofing available
            print("[AntiSpoof] No anti-spoofing method available, bypassing check")
            return {
                'success': True,
                'is_real': True,
                'antispoof_score': 1.0,
                'method': 'none',
                'message': 'Anti-spoofing bypassed (no detection library installed)'
            }
                    
        except Exception as e:
            print(f"[AntiSpoof] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'is_real': False,
                'error': str(e)
            }
    
    def _check_anti_spoofing_deepface(self, image: np.ndarray) -> Dict:
        """Use DeepFace MiniVision models for anti-spoofing"""
        import tempfile
        import os
        
        print("[AntiSpoof] Using DeepFace method...")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
            Image.fromarray(image).save(tmp_path, 'JPEG')
        
        try:
            faces = DeepFace.extract_faces(
                img_path=tmp_path,
                anti_spoofing=True,
                enforce_detection=True
            )
            
            if not faces:
                return {
                    'success': True,
                    'is_real': False,
                    'has_face': False,
                    'antispoof_score': 0.0,
                    'method': 'deepface',
                    'message': 'No face detected in image'
                }
            
            face = faces[0]
            is_real = face.get('is_real', False)
            antispoof_score = face.get('antispoof_score', 0.0)
            face_confidence = face.get('confidence', 0.0)
            
            print(f"[AntiSpoof-DeepFace] Result: is_real={is_real}, score={antispoof_score:.3f}, confidence={face_confidence:.3f}")
            
            # Filter out low-confidence faces (e.g. hands, blurry objects)
            if face_confidence < 0.70:
                print(f"[AntiSpoof-DeepFace] ⚠️ Low confidence face ({face_confidence:.3f}), rejecting.")
                return {
                    'success': True,
                    'is_real': False,
                    'has_face': True,
                    'antispoof_score': antispoof_score,
                    'confidence': round(float(face_confidence) * 100, 2),
                    'method': 'deepface',
                    'message': 'Face unsure/occluded. Please show full face.'
                }
            
            return {
                'success': True,
                'is_real': is_real,
                'has_face': True,
                'antispoof_score': round(float(antispoof_score), 3),
                'confidence': round(float(face_confidence) * 100, 2),
                'method': 'deepface',
                'message': 'REAL face detected!' if is_real else 'SPOOFING DETECTED!'
            }
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def _check_anti_spoofing_opencv(self, image: np.ndarray) -> Dict:
        """
        Use OpenCV texture analysis for anti-spoofing (fallback method).
        CRITICAL: Must crop face first! Running on background gives low texture score (spoof).
        """
        print("[AntiSpoof] Using OpenCV texture analysis method...")
        
        # 0. Crop face first using face_recognition
        try:
            face_locations = face_recognition.face_locations(image)
            if not face_locations:
                print("[AntiSpoof-OpenCV] No face found for cropping")
                return {
                    'success': True,
                    'is_real': False,
                    'has_face': False,
                    'antispoof_score': 0.0,
                    'method': 'opencv_texture',
                    'message': 'No face detected (OpenCV)'
                }
            
            # Get largest face
            top, right, bottom, left = face_locations[0]
            
            # Add padding
            h, w, _ = image.shape
            pad = 20
            top = max(0, top - pad)
            bottom = min(h, bottom + pad)
            left = max(0, left - pad)
            right = min(w, right + pad)
            
            face_crop = image[top:bottom, left:right]
            print(f"[AntiSpoof-OpenCV] Face cropped: {face_crop.shape}")
            
        except Exception as e:
            print(f"[AntiSpoof-OpenCV] Cropping failed: {e}, using full image")
            face_crop = image
        
        # Convert to BGR for OpenCV
        image_bgr = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # 1. Laplacian variance (blur/texture detection)
        # Real faces have higher variance >= 100 usually
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_var = laplacian.var()
        
        # 2. Calculate color distribution
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        sat_std = np.std(saturation)
        
        # Scoring tuned for CROPPED face
        # Real face (webcam): laplacian ~100-300+, sat_std ~30-60
        # Screen/Photo: laplacian < 50, sat_std < 20
        
        texture_score = min(1.0, laplacian_var / 300.0) 
        color_score = min(1.0, sat_std / 50.0)
        
        # Weight more on texture
        antispoof_score = (texture_score * 0.7 + color_score * 0.3)
        
        # TIGHTER SECURITY for OpenCV-Only Mode
        # Previous 0.15 was too loose (allowed photos).
        # Raising to 0.45 to block screens/prints.
        REAL_THRESHOLD = 0.45
        is_real = bool(antispoof_score >= REAL_THRESHOLD)
        
        print(f"[AntiSpoof-OpenCV] Texture: {laplacian_var:.1f}, Sat std: {sat_std:.1f}")
        print(f"[AntiSpoof-OpenCV] Final score: {antispoof_score:.3f} (Threshold: {REAL_THRESHOLD})")
        
        return {
            'success': True,
            'is_real': is_real,
            'has_face': True,
            'antispoof_score': round(float(antispoof_score), 3),
            'method': 'opencv_texture',
            'details': {
                'laplacian_var': round(float(laplacian_var), 2),
                'saturation_std': round(float(sat_std), 2)
            },
            'message': 'REAL face detected!' if is_real else f'SPOOFING DETECTED! Score {antispoof_score:.3f} < {REAL_THRESHOLD}. Please use better lighting.'
        }



# Singleton instance
face_service = FaceService()

