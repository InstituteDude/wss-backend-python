"""
Personnel Service - Registration and authentication logic
"""
from typing import Dict, List, Optional
from models.database import db
from models.personnel import Personnel


class PersonnelService:
    """Service untuk operasi personnel/user management"""
    
    def register(self, user_id: str, name: str, password: str, 
                 role: str = 'User', permissions: dict = None) -> Dict:
        """
        Register personnel baru
        """
        try:
            # Check if user_id already exists
            existing = Personnel.query.filter_by(user_id=user_id).first()
            if existing:
                return {
                    'success': False,
                    'error': f'User ID "{user_id}" already exists'
                }
            
            # Create new personnel
            personnel = Personnel(
                user_id=user_id,
                name=name,
                role=role
            )
            personnel.set_password(password)
            
            if permissions:
                personnel.set_permissions(permissions)
            
            db.session.add(personnel)
            db.session.commit()
            
            print(f"[PersonnelService] Registered: {user_id} ({name})")
            
            return {
                'success': True,
                'message': 'Personnel registered successfully',
                'user': personnel.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"[PersonnelService] Register error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def login(self, user_id: str, password: str) -> Dict:
        """
        Login dengan user_id dan password
        """
        try:
            personnel = Personnel.query.filter_by(user_id=user_id).first()
            
            if not personnel:
                print(f"[PersonnelService] Login failed: user not found - {user_id}")
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            if not personnel.check_password(password):
                print(f"[PersonnelService] Login failed: wrong password - {user_id}")
                return {
                    'success': False,
                    'error': 'Invalid password'
                }
            
            print(f"[PersonnelService] Login success: {user_id}")
            
            return {
                'success': True,
                'message': 'Login successful',
                'user': personnel.to_dict()
            }
            
        except Exception as e:
            print(f"[PersonnelService] Login error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_by_user_id(self, user_id: str) -> Optional[Dict]:
        """Get personnel by user_id"""
        personnel = Personnel.query.filter_by(user_id=user_id).first()
        if personnel:
            return personnel.to_dict()
        return None
    
    def list_all(self) -> List[Dict]:
        """List all personnel"""
        personnel_list = Personnel.query.all()
        return [p.to_dict() for p in personnel_list]
    
    def update(self, user_id: str, **kwargs) -> Dict:
        """Update personnel data"""
        try:
            personnel = Personnel.query.filter_by(user_id=user_id).first()
            
            if not personnel:
                return {'success': False, 'error': 'User not found'}
            
            # Update allowed fields
            if 'name' in kwargs:
                personnel.name = kwargs['name']
            if 'role' in kwargs:
                personnel.role = kwargs['role']
            if 'password' in kwargs:
                personnel.set_password(kwargs['password'])
            if 'permissions' in kwargs:
                personnel.set_permissions(kwargs['permissions'])
            if 'has_face' in kwargs:
                personnel.has_face = kwargs['has_face']
            if 'has_fingerprint' in kwargs:
                personnel.has_fingerprint = kwargs['has_fingerprint']
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Personnel updated successfully',
                'user': personnel.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def delete(self, user_id: str) -> Dict:
        """Delete personnel by user_id"""
        try:
            personnel = Personnel.query.filter_by(user_id=user_id).first()
            
            if not personnel:
                return {'success': False, 'error': 'User not found'}
            
            db.session.delete(personnel)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'Personnel {user_id} deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def mark_face_registered(self, user_id: str) -> Dict:
        """Mark that user has registered face"""
        return self.update(user_id, has_face=True)


# Singleton instance
personnel_service = PersonnelService()
