#!/usr/bin/env python3
"""
Script untuk register face biometric ke Go Backend
"""
import requests
import base64
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.face_service import face_service

# Configuration - Testing with SUPERADM (registering own face)
USER_ID = "019bb2d0-056a-7212-b1e4-3993673c65cc"  # superadm's user_id
ADMIN_USERNAME = "superadm"
ADMIN_PASSWORD = "wss.ssw"
GO_BACKEND_URL = "https://api-wss.sumapala.co.id"

# Path to user's photo
PHOTO_PATH = r"C:\Users\kaliz\.gemini\antigravity\brain\f673b938-9642-436e-95dd-9b5b3dcf358d\uploaded_image_1_1768687858658.jpg"

def login():
    """Login with ADMIN and get JWT token"""
    print(f"[Login] Logging in as {ADMIN_USERNAME}...")
    response = requests.post(
        f"{GO_BACKEND_URL}/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"[Login] Failed: {response.text}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    print(f"[Login] Success! Token: {token[:50]}...")
    return token

def extract_encoding(photo_path):
    """Extract face encoding using Python backend"""
    print(f"[Encode] Reading photo: {photo_path}")
    
    with open(photo_path, "rb") as f:
        image_data = f.read()
    
    # Convert to base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Decode and extract encoding using face_service
    print("[Encode] Decoding image...")
    image = face_service.decode_base64_image(image_base64)
    print(f"[Encode] Image shape: {image.shape}")
    
    print("[Encode] Extracting face encoding...")
    encoding = face_service.extract_face_encoding(image)
    
    if encoding is None:
        print("[Encode] ERROR: No face detected!")
        return None
    
    print(f"[Encode] Encoding extracted! Length: {len(encoding)}")
    return encoding.tolist()

def register_biometric(token, user_id, encoding):
    """Register biometric to Go backend"""
    print(f"[Register] Registering face for user {user_id}...")
    
    # Format template_data sesuai dokumentasi
    template_data = json.dumps({
        "encoding": encoding,
        "algorithm": "dlib"
    })
    
    # Call Go backend
    response = requests.post(
        f"{GO_BACKEND_URL}/api/users/{user_id}/biometrics",
        json={
            "biometric_type": "face",
            "template_data": template_data,
            "encoding_algorithm": "dlib"  # Required by Go backend
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    
    print(f"[Register] Response status: {response.status_code}")
    print(f"[Register] Response body: {response.text}")
    
    return response.status_code == 200 or response.status_code == 201

def main():
    print("=" * 60)
    print("  FACE BIOMETRIC REGISTRATION")
    print("=" * 60)
    
    # Step 1: Login
    token = login()
    if not token:
        print("FAILED: Could not login")
        return
    
    # Step 2: Extract encoding
    encoding = extract_encoding(PHOTO_PATH)
    if not encoding:
        print("FAILED: Could not extract face encoding")
        return
    
    # Step 3: Register to Go backend
    success = register_biometric(token, USER_ID, encoding)
    
    if success:
        print("\n" + "=" * 60)
        print("  ✅ REGISTRATION SUCCESSFUL!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("  ❌ REGISTRATION FAILED")
        print("=" * 60)

if __name__ == "__main__":
    main()
