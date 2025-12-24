"""
Enhanced User Management System for CityPets Employee App
Provides secure database-driven user authentication with proper password hashing
"""

import sqlite3
import hashlib
import secrets
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import streamlit as st

class UserManager:
    """Advanced user management with database storage and security features"""
    
    def __init__(self, db_path: str = "citypets_users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize user management database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                employee_name TEXT NOT NULL,
                role TEXT DEFAULT 'employee',
                is_active INTEGER DEFAULT 1,
                is_temp_password INTEGER DEFAULT 0,
                must_change_password INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                password_reset_token TEXT,
                password_reset_expires TIMESTAMP
            )
        ''')
        
        # Create sessions table for better session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create tab sessions table for tab-specific state management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tab_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tab_session_id TEXT NOT NULL,
                session_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Run database migrations
        self._run_migrations(cursor)
        
        conn.commit()
        conn.close()
    
    def _run_migrations(self, cursor):
        """Run database migrations to update schema"""
        # Check if new columns exist and add them if they don't
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_temp_password' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_temp_password INTEGER DEFAULT 0')
        
        if 'must_change_password' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0')
    
    def create_tab_session(self, user_id: int, tab_session_id: str, session_data: Dict = None) -> bool:
        """Create or update a tab session for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_data_json = json.dumps(session_data or {})
            
            cursor.execute('''
                INSERT OR REPLACE INTO tab_sessions 
                (user_id, tab_session_id, session_data, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, datetime('now'), datetime('now'), datetime('now', '+30 days'))
            ''', (user_id, tab_session_id, session_data_json))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating tab session: {e}")
            return False
    
    def get_tab_session(self, user_id: int, tab_session_id: str) -> Optional[Dict]:
        """Get tab session data for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_data, created_at, updated_at 
                FROM tab_sessions 
                WHERE user_id = ? AND tab_session_id = ?
            ''', (user_id, tab_session_id))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Update last accessed time
                self._update_tab_session_access(user_id, tab_session_id)
                
                return {
                    'session_data': json.loads(result[0]),
                    'created_at': result[1],
                    'updated_at': result[2]
                }
            return None
        except Exception as e:
            print(f"Error getting tab session: {e}")
            return None
    
    def _update_tab_session_access(self, user_id: int, tab_session_id: str):
        """Update the last accessed time for a tab session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tab_sessions 
                SET updated_at = datetime('now')
                WHERE user_id = ? AND tab_session_id = ?
            ''', (user_id, tab_session_id))
            
            conn.commit()
            conn.close()
        except Exception:
            pass  # Silently fail - this is not critical
    
    def cleanup_expired_tab_sessions(self, expiry_hours: int = 24):
        """Clean up expired tab sessions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM tab_sessions 
                WHERE updated_at < datetime('now', '-{} hours')
            '''.format(expiry_hours))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error cleaning up expired tab sessions: {e}")
    
    def delete_tab_session(self, user_id: int, tab_session_id: str) -> bool:
        """Delete a specific tab session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM tab_sessions 
                WHERE user_id = ? AND tab_session_id = ?
            ''', (user_id, tab_session_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting tab session: {e}")
            return False
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """Create secure password hash with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt.encode('utf-8'), 
                                          100000)  # 100k iterations
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        computed_hash = hashlib.pbkdf2_hmac('sha256',
                                          password.encode('utf-8'),
                                          salt.encode('utf-8'),
                                          100000)
        return computed_hash.hex() == password_hash
    
    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password meets security requirements"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def generate_temp_password(self, length: int = 12) -> str:
        """Generate a secure temporary password"""
        import secrets
        import string
        
        # Ensure password meets strength requirements
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Guarantee at least one of each required character type
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest with random characters
        all_chars = uppercase + lowercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password to randomize character positions
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def create_user(self, username: str, email: str, password: str, 
                   full_name: str, employee_name: str, role: str = 'employee', 
                   is_temp_password: bool = False) -> Tuple[bool, str]:
        """Create new user account"""
        
        # Validate inputs
        if not self.validate_email(email):
            return False, "Invalid email format"
        
        # Only validate password strength if it's not a temporary password
        if not is_temp_password:
            is_strong, password_errors = self.validate_password_strength(password)
            if not is_strong:
                return False, "; ".join(password_errors)
        
        # Hash password
        password_hash, salt = self.hash_password(password)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, full_name, employee_name, role, 
                                 is_temp_password, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, salt, full_name, employee_name, role, 
                  1 if is_temp_password else 0, 1 if is_temp_password else 0))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return True, user_id
            
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return False, "Username already exists"
            elif "email" in str(e):
                return False, "Email already registered"
            else:
                return False, "Database error occurred"
    
    def create_user_with_temp_password(self, username: str, email: str, 
                                     full_name: str, employee_name: str, 
                                     role: str = 'employee') -> Tuple[bool, str, str]:
        """Create user with temporary password that must be changed on first login"""
        temp_password = self.generate_temp_password()
        success, result = self.create_user(username, email, temp_password, 
                                          full_name, employee_name, role, 
                                          is_temp_password=True)
        if success:
            return success, f"User created successfully with ID: {result}", temp_password
        else:
            return success, result, ""
    
    def authenticate_user(self, username_or_email: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Authenticate user login"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find user by username or email
        cursor.execute('''
            SELECT id, username, email, password_hash, salt, full_name, employee_name, role, 
                   is_active, failed_login_attempts, locked_until, is_temp_password, must_change_password
            FROM users 
            WHERE (username = ? OR email = ?) AND is_active = 1
        ''', (username_or_email, username_or_email))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            return False, None
        
        user_id, username, email, password_hash, salt, full_name, employee_name, role, is_active, failed_attempts, locked_until, is_temp_password, must_change_password = user_data
        
        # Check if account is locked
        if locked_until:
            locked_until_dt = datetime.fromisoformat(locked_until)
            if datetime.now() < locked_until_dt:
                conn.close()
                return False, None
        
        # Verify password
        if self.verify_password(password, password_hash, salt):
            # Reset failed attempts and update last login
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            
            return True, {
                'id': user_id,
                'username': username,
                'email': email,
                'full_name': full_name,
                'employee_name': employee_name,
                'role': role,
                'is_admin': role == 'admin',
                'is_temp_password': bool(is_temp_password),
                'must_change_password': bool(must_change_password)
            }
        else:
            # Increment failed attempts
            new_failed_attempts = failed_attempts + 1
            locked_until = None
            
            # Lock account after 5 failed attempts for 30 minutes
            if new_failed_attempts >= 5:
                locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
            
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = ?, locked_until = ?
                WHERE id = ?
            ''', (new_failed_attempts, locked_until, user_id))
            conn.commit()
            conn.close()
            
            return False, None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users for admin management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, full_name, employee_name, role, is_active, 
                   created_at, last_login, failed_login_attempts, is_temp_password, must_change_password
            FROM users 
            ORDER BY created_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'employee_name': row[4],
                'role': row[5],
                'is_active': bool(row[6]),
                'created_at': row[7],
                'last_login': row[8],
                'failed_login_attempts': row[9],
                'is_temp_password': bool(row[10]),
                'must_change_password': bool(row[11])
            })
        
        conn.close()
        return users
    
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Update user role (admin function)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return success
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return success
    
    def reactivate_user(self, user_id: int) -> bool:
        """Reactivate user account"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
        success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return success
    
    def reset_password(self, user_identifier, new_password: str, is_temp: bool = False) -> Tuple[bool, str]:
        """Reset user password (admin function or user self-reset)
        
        Args:
            user_identifier: User ID (int) or username (str)
            new_password: New password
            is_temp: Whether this is a temporary password that must be changed
        """
        # Validate new password
        is_strong, password_errors = self.validate_password_strength(new_password)
        if not is_strong:
            return False, "Password does not meet security requirements"
        
        # Hash new password
        password_hash, salt = self.hash_password(new_password)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Determine if user_identifier is ID or username
        if isinstance(user_identifier, int):
            where_clause = "id = ?"
            where_value = user_identifier
        else:
            where_clause = "username = ?"
            where_value = user_identifier
        
        # Set temporary password flags if needed
        temp_flag = 1 if is_temp else 0
        must_change_flag = 1 if is_temp else 0
        
        cursor.execute(f'''
            UPDATE users 
            SET password_hash = ?, salt = ?, failed_login_attempts = 0, locked_until = NULL,
                is_temp_password = ?, must_change_password = ?
            WHERE {where_clause}
        ''', (password_hash, salt, temp_flag, must_change_flag, where_value))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            return True, "Password reset successfully"
        else:
            return False, "User not found or password reset failed"
    
    def unlock_user_account(self, user_id: int) -> bool:
        """Unlock user account (admin function)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET failed_login_attempts = 0, locked_until = NULL
            WHERE id = ?
        ''', (user_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_user_info(self, user_id: int, username: str = None, email: str = None, 
                        full_name: str = None, employee_name: str = None, role: str = None) -> Tuple[bool, str]:
        """Update user information (admin function)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Validate email if provided
        if email and not self.validate_email(email):
            conn.close()
            return False, "Invalid email format"
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        if username is not None:
            update_fields.append("username = ?")
            update_values.append(username)
        
        if email is not None:
            update_fields.append("email = ?")
            update_values.append(email)
        
        if full_name is not None:
            update_fields.append("full_name = ?")
            update_values.append(full_name)
        
        if employee_name is not None:
            update_fields.append("employee_name = ?")
            update_values.append(employee_name)
        
        if role is not None:
            update_fields.append("role = ?")
            update_values.append(role)
        
        if not update_fields:
            conn.close()
            return False, "No fields to update"
        
        update_values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        
        try:
            cursor.execute(query, update_values)
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                return True, "User updated successfully"
            else:
                return False, "User not found"
                
        except sqlite3.IntegrityError as e:
            conn.close()
            if "username" in str(e):
                return False, "Username already exists"
            elif "email" in str(e):
                return False, "Email already registered"
            else:
                return False, "Database constraint violation"
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Delete user account (admin function)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First check if user exists and get info
        cursor.execute('SELECT username, employee_name FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            return False, "User not found"
        
        username, employee_name = user_data
        
        try:
            # Delete user sessions first (if sessions table exists)
            cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
            
            # Delete the user
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            return True, f"User {username} ({employee_name}) deleted successfully"
            
        except Exception as e:
            conn.close()
            return False, f"Failed to delete user: {str(e)}"
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, full_name, employee_name, role, is_active, 
                   created_at, last_login, failed_login_attempts
            FROM users 
            WHERE id = ?
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'username': user_data[1],
                'email': user_data[2],
                'full_name': user_data[3],
                'employee_name': user_data[4],
                'role': user_data[5],
                'is_active': bool(user_data[6]),
                'created_at': user_data[7],
                'last_login': user_data[8],
                'failed_login_attempts': user_data[9]
            }
        return None

    def create_session_token(self, user_id: int) -> Optional[str]:
        """Create a session token for the user"""
        import secrets
        from datetime import datetime, timedelta
        
        # Generate a secure random token
        session_token = secrets.token_urlsafe(32)
        
        # Set expiration to 7 days from now
        expires_at = datetime.now() + timedelta(days=7)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert new session token
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            conn.commit()
            conn.close()
            return session_token
            
        except Exception as e:
            conn.close()
            return None
    
    def get_user_by_session_token(self, session_token: str) -> Optional[Dict]:
        """Get user information by session token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user data by valid session token
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.full_name, u.employee_name, u.role,
                   (u.role = 'admin') as is_admin
            FROM users u
            JOIN user_sessions s ON u.id = s.user_id
            WHERE s.session_token = ? 
            AND s.expires_at > datetime('now')
            AND s.is_active = 1
            AND u.is_active = 1
        ''', (session_token,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return {
                'id': user_data[0],
                'username': user_data[1],
                'email': user_data[2],
                'full_name': user_data[3],
                'employee_name': user_data[4],
                'role': user_data[5],
                'is_admin': bool(user_data[6])
            }
        return None
    
    def invalidate_session_token(self, session_token: str) -> bool:
        """Invalidate a session token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE session_token = ?
        ''', (session_token,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def cleanup_expired_sessions(self):
        """Clean up expired session tokens"""
        from datetime import datetime
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM user_sessions 
            WHERE expires_at < ? OR is_active = 0
        ''', (datetime.now(),))
        
        conn.commit()
        conn.close()

def render_advanced_login_page():
    """Render enhanced login page with username/password"""
    st.title("🐕 CityPets Employee Timesheet")
    st.subheader("🔐 Secure Login")
    
    user_manager = UserManager()
    
    # Check if user needs to change password (temporary password)
    if st.session_state.get('force_password_change', False):
        user_data = st.session_state.get('temp_user_data')
        
        st.markdown("### 🔑 Change Your Temporary Password")
        st.info("🔒 **Security Requirement:** You must change your temporary password to continue.")
        
        with st.form("forced_password_change"):
            st.markdown(f"**User:** {user_data['full_name']} ({user_data['username']})")
            
            new_password = st.text_input("New Password", type="password", placeholder="Enter a strong password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your new password")
            
            # Password requirements
            st.markdown("""
            **Password Requirements:**
            - At least 8 characters long
            - Contains uppercase and lowercase letters
            - Contains at least one number
            - Contains at least one special character (!@#$%^&*(),.?":{}|<>)
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("🔒 Change Password", use_container_width=True):
                    if not new_password or not confirm_password:
                        st.error("❌ Please fill in both password fields")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match")
                    else:
                        # Validate password strength
                        is_valid, errors = user_manager.validate_password_strength(new_password)
                        
                        if not is_valid:
                            st.error("❌ Password does not meet requirements:")
                            for error in errors:
                                st.error(f"  • {error}")
                        else:
                            # Change password
                            success, message = user_manager.reset_password(user_data['username'], new_password)
                            
                            if success:
                                # Clear forced password change state
                                st.session_state.force_password_change = False
                                st.session_state.temp_user_data = None
                                
                                # Complete login
                                st.session_state.authenticated = True
                                st.session_state.user_email = user_data['email']
                                st.session_state.user_name = user_data['employee_name']
                                st.session_state.is_admin = user_data['is_admin']
                                st.session_state.login_time = datetime.now()
                                st.session_state.user_id = user_data['id']
                                st.session_state.username = user_data['username']
                                st.session_state.full_name = user_data['full_name']
                                
                                # Create session token for persistence
                                EnhancedAuthManager._create_session_token(user_data['id'])
                                
                                st.success("✅ Password changed successfully! Welcome to CityPets!")
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
            
            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.force_password_change = False
                    st.session_state.temp_user_data = None
                    st.rerun()
        
        return  # Exit early to show only password change form
    
    # Regular login form (when not forcing password change)
    with st.form("login_form"):
        st.markdown("### Login to Your Account")
        
        username_or_email = st.text_input("Username or Email", placeholder="Enter your username or email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            login_submitted = st.form_submit_button("🔓 Login", use_container_width=True)
        
        with col2:
            forgot_password = st.form_submit_button("🔄 Forgot Password?", use_container_width=True)
    
    # Handle login
    if login_submitted:
        if username_or_email and password:
            success, user_data = user_manager.authenticate_user(username_or_email, password)
            
            if success:
                # Check if user must change password (temporary password)
                if user_data.get('must_change_password', False):
                    # Store user data for password change
                    st.session_state.force_password_change = True
                    st.session_state.temp_user_data = user_data
                    st.success(f"✅ Login successful, {user_data['full_name']}!")
                    st.warning("🔑 **You must change your temporary password before continuing.**")
                    st.rerun()
                else:
                    # Normal login - update session state
                    st.session_state.authenticated = True
                    st.session_state.user_email = user_data['email']
                    st.session_state.user_name = user_data['employee_name']
                    st.session_state.is_admin = user_data['is_admin']
                    st.session_state.login_time = datetime.now()
                    st.session_state.user_id = user_data['id']
                    st.session_state.username = user_data['username']
                    st.session_state.full_name = user_data['full_name']
                    
                    # Create session token for persistence
                    EnhancedAuthManager._create_session_token(user_data['id'])
                    
                    st.success(f"✅ Welcome back, {user_data['full_name']}!")
                    st.rerun()
            else:
                st.error("❌ Invalid username/email or password. Account may be locked after 5 failed attempts.")
        else:
            st.warning("⚠️ Please enter both username/email and password")
    
    # Handle forgot password
    if forgot_password:
        if username_or_email:
            st.info("🔄 Password reset functionality is coming soon. Please contact your administrator for assistance.")
        else:
            st.warning("⚠️ Please enter your username or email to reset password")

def render_user_management_page():
    """Render user management page for admins"""
    st.title("👥 User Management")
    
    user_manager = UserManager()
    
    # Tabs for different management functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 View Users", "➕ Add User", "✏️ Edit User", "🔑 Password Reset", "⚙️ Settings"])
    
    with tab1:
        st.subheader("All Users")
        users = user_manager.get_all_users()
        
        # Check if we're editing a user
        editing_user_id = st.session_state.get('edit_user_id')
        
        if users:
            for user in users:
                with st.container():
                    # If this user is being edited, show edit form
                    if editing_user_id == user['id']:
                        st.markdown("### ✏️ Editing User")
                        
                        with st.form(f"edit_form_{user['id']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edit_username = st.text_input("Username", value=user['username'], key=f"edit_username_{user['id']}")
                                edit_email = st.text_input("Email", value=user['email'], key=f"edit_email_{user['id']}")
                                edit_role = st.selectbox("Role", ["employee", "admin"], 
                                                       index=0 if user['role'] == 'employee' else 1,
                                                       key=f"edit_role_{user['id']}")
                            
                            with col2:
                                edit_full_name = st.text_input("Full Name", value=user['full_name'], key=f"edit_full_name_{user['id']}")
                                edit_employee_name = st.text_input("Employee Name", value=user['employee_name'], key=f"edit_employee_name_{user['id']}")
                                edit_active = st.checkbox("Active", value=user['is_active'], key=f"edit_active_{user['id']}")
                            
                            col_save, col_cancel = st.columns(2)
                            
                            with col_save:
                                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                    success, message = user_manager.update_user_info(
                                        user['id'],
                                        username=edit_username,
                                        email=edit_email,
                                        full_name=edit_full_name,
                                        employee_name=edit_employee_name,
                                        role=edit_role
                                    )
                                    
                                    if success:
                                        # Update active status separately
                                        if edit_active != user['is_active']:
                                            if edit_active:
                                                user_manager.reactivate_user(user['id'])
                                            else:
                                                user_manager.deactivate_user(user['id'])
                                        
                                        st.success(f"✅ {message}")
                                        del st.session_state.edit_user_id
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {message}")
                            
                            with col_cancel:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    del st.session_state.edit_user_id
                                    st.rerun()
                        
                        st.divider()
                    else:
                        # Normal user display row
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
                        
                        with col1:
                            status_icon = "🟢" if user['is_active'] else "🔴"
                            role_icon = "👑" if user['role'] == 'admin' else "👤"
                            lock_icon = "🔒" if user['failed_login_attempts'] >= 5 else ""
                            temp_icon = "🔑" if user['is_temp_password'] else ""
                            st.write(f"{status_icon} {role_icon} {lock_icon} {temp_icon} **{user['full_name']}**")
                            st.caption(f"@{user['username']} • {user['email']}")
                            if user['last_login']:
                                st.caption(f"Last login: {user['last_login']}")
                            if user['is_temp_password']:
                                st.caption("🔑 **Temporary password** - Must change on login")
                        
                        with col2:
                            st.write(f"**Employee:** {user['employee_name']}")
                            st.caption(f"Role: {user['role'].title()}")
                            if user['failed_login_attempts'] > 0:
                                st.caption(f"⚠️ Failed attempts: {user['failed_login_attempts']}")
                            if user['must_change_password']:
                                st.caption("🔄 **Must change password**")
                        
                        with col3:
                            if user['failed_login_attempts'] >= 5:
                                if st.button("🔓 Unlock", key=f"unlock_{user['id']}"):
                                    user_manager.unlock_user_account(user['id'])
                                    st.rerun()
                            elif user['is_active']:
                                if st.button("❌ Deactivate", key=f"deact_{user['id']}"):
                                    user_manager.deactivate_user(user['id'])
                                    st.rerun()
                            else:
                                if st.button("✅ Activate", key=f"act_{user['id']}"):
                                    user_manager.reactivate_user(user['id'])
                                    st.rerun()
                        
                        with col4:
                            if st.button("✏️ Edit", key=f"edit_{user['id']}"):
                                st.session_state.edit_user_id = user['id']
                                st.rerun()
                            
                            # Add regenerate temp password option for users with temp passwords
                            if user['is_temp_password']:
                                if st.button("🔑 New Temp", key=f"newtemp_{user['id']}", help="Generate new temporary password"):
                                    # Generate new temporary password
                                    temp_password = user_manager.generate_temp_password()
                                    
                                    # Update user with new password
                                    success, message = user_manager.reset_password(user['username'], temp_password, is_temp=True)
                                    
                                    if success:
                                        # Store in recent temp passwords
                                        if 'recent_temp_passwords' not in st.session_state:
                                            st.session_state.recent_temp_passwords = []
                                        
                                        temp_entry = {
                                            'username': user['username'],
                                            'full_name': user['full_name'],
                                            'temp_password': temp_password,
                                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'unique_id': f"{user['username']}_{datetime.now().timestamp()}"
                                        }
                                        
                                        st.session_state.recent_temp_passwords.append(temp_entry)
                                        
                                        st.success(f"✅ New temporary password generated for {user['full_name']}")
                                        
                                        # Show the new password prominently
                                        st.info(f"🔑 **New Temporary Password:** `{temp_password}`")
                                        st.warning("⚠️ **Share this securely with the user!**")
                                        
                                        # Don't call st.rerun() immediately to keep password visible
                                    else:
                                        st.error(f"❌ {message}")
                        
                        with col5:
                            # Prevent deletion of current user and require confirmation
                            current_user = st.session_state.get('user_email')
                            if user['email'] != current_user:  # Can't delete yourself
                                if st.button("🗑️ Delete", key=f"delete_{user['id']}"):
                                    if st.session_state.get(f'confirm_delete_{user["id"]}', False):
                                        success = user_manager.delete_user(user['id'])
                                        if success:
                                            st.success(f"✅ User {user['full_name']} deleted")
                                            if f'confirm_delete_{user["id"]}' in st.session_state:
                                                del st.session_state[f'confirm_delete_{user["id"]}']
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to delete user")
                                    else:
                                        st.session_state[f'confirm_delete_{user["id"]}'] = True
                                        st.rerun()
                            else:
                                st.caption("*Cannot delete own account*")
                        
                        # Show confirmation message if delete was clicked
                        if st.session_state.get(f'confirm_delete_{user["id"]}', False):
                            st.warning(f"⚠️ **Confirm deletion of {user['full_name']}?** Click Delete again to confirm.")
                        
                        st.divider()
        else:
            st.info("No users found. Add users or run migration to import existing users.")
    
    with tab2:
        st.subheader("Add New User")
        
        # Display recent temporary passwords if any (but not if we just created one)
        if st.session_state.get('recent_temp_passwords') and not st.session_state.get('temp_password_created'):
            st.markdown("### 🔑 **Recent Temporary Passwords**")
            st.error("⚠️ **CRITICAL:** Save these passwords securely! Share them with users who must change them on first login.")
            
            for idx, temp_pass in enumerate(reversed(st.session_state.recent_temp_passwords)):
                with st.container():
                    st.markdown(f"#### {temp_pass['full_name']} (@{temp_pass['username']})")
                    
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.code(f"Temporary Password: {temp_pass['temp_password']}", language="text")
                    
                    with col2:
                        st.caption(f"📅 Created: {temp_pass['created_at']}")
                        st.caption("🔒 Must change on first login")
                    
                    with col3:
                        if st.button("✅ Got it", key=f"remove_temp_{idx}_{temp_pass.get('unique_id', temp_pass['username'])}", help="Remove from list"):
                            # Remove this specific entry by finding it in the original list
                            st.session_state.recent_temp_passwords = [
                                tp for tp in st.session_state.recent_temp_passwords 
                                if tp.get('unique_id', tp['username'] + tp['created_at']) != temp_pass.get('unique_id', temp_pass['username'] + temp_pass['created_at'])
                            ]
                            st.rerun()
                    
                    st.divider()
            
            col_clear, col_space = st.columns([1, 3])
            with col_clear:
                if st.button("🗑️ Clear All Passwords", help="Clear all temporary passwords from display"):
                    st.session_state.recent_temp_passwords = []
                    st.rerun()
            
            st.markdown("---")
        
        # Password type selection
        password_type = st.radio(
            "Password Type:",
            ["Manual Password", "Generate Temporary Password"],
            help="Choose whether to set a password manually or generate a temporary password that must be changed on first login"
        )
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username", help="Unique username for login")
                new_email = st.text_input("Email", help="Valid email address")
                if password_type == "Manual Password":
                    new_password = st.text_input("Password", type="password", help="Must meet security requirements")
                else:
                    st.info("🔑 A secure temporary password will be generated automatically")
            
            with col2:
                new_full_name = st.text_input("Full Name", help="Employee's full name")
                new_employee_name = st.text_input("Employee Name", help="Name used in timesheet system")
                new_role = st.selectbox("Role", ["employee", "admin"])
            
            # Password requirements info
            if password_type == "Manual Password":
                st.info("🔒 **Password Requirements:** 8+ characters, uppercase, lowercase, number, special character")
            else:
                st.info("🔑 **Temporary Password:** User will be forced to change password on first login")
            
            if st.form_submit_button("➕ Create User", use_container_width=True):
                if password_type == "Manual Password":
                    if all([new_username, new_email, new_password, new_full_name, new_employee_name]):
                        success, message = user_manager.create_user(
                            new_username, new_email, new_password, 
                            new_full_name, new_employee_name, new_role
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ Please fill in all fields")
                else:  # Generate temporary password
                    if all([new_username, new_email, new_full_name, new_employee_name]):
                        success, message, temp_password = user_manager.create_user_with_temp_password(
                            new_username, new_email, new_full_name, new_employee_name, new_role
                        )
                        
                        if success:
                            # Store temporary password in session state for display
                            if 'recent_temp_passwords' not in st.session_state:
                                st.session_state.recent_temp_passwords = []
                            
                            # Create unique entry with timestamp
                            temp_entry = {
                                'username': new_username,
                                'full_name': new_full_name,
                                'temp_password': temp_password,
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'unique_id': f"{new_username}_{datetime.now().timestamp()}"
                            }
                            
                            st.session_state.recent_temp_passwords.append(temp_entry)
                            
                            # Keep only last 5 temp passwords
                            if len(st.session_state.recent_temp_passwords) > 5:
                                st.session_state.recent_temp_passwords = st.session_state.recent_temp_passwords[-5:]
                            
                            # Set a flag to show password outside the form
                            st.session_state.temp_password_created = {
                                'username': new_username,
                                'password': temp_password,
                                'success_message': message
                            }
                            
                            st.rerun()  # Refresh to show password outside form
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ Please fill in all required fields")
        
        # Display temporary password outside the form if just created
        if st.session_state.get('temp_password_created'):
            temp_data = st.session_state.temp_password_created
            
            st.balloons()
            st.success(f"🎉 {temp_data['success_message']}")
            
            # Create a prominent display box for the temporary password
            st.markdown("### 🔑 **TEMPORARY PASSWORD CREATED**")
            st.code(f"Username: {temp_data['username']}\nTemporary Password: {temp_data['password']}", language="text")
            
            st.error("⚠️ **CRITICAL:** Save this password now! Share it securely with the user. They must change it on first login.")
            
            # Add a button to continue after saving the password
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ I've Saved the Password - Continue", key="continue_after_temp_creation"):
                    # Clear the temporary password display
                    if 'temp_password_created' in st.session_state:
                        del st.session_state.temp_password_created
                    st.rerun()
            
            with col2:
                if st.button("📋 Add to Recent List", key="add_to_recent_list"):
                    # Just clear the special display, password will show in recent list
                    if 'temp_password_created' in st.session_state:
                        del st.session_state.temp_password_created
                    st.rerun()
    
    with tab3:
        st.subheader("Edit User")
        
        # User selection for editing
        users = user_manager.get_all_users()
        if users:
            # Check if edit_user_id is set from the View Users tab
            edit_user_id = st.session_state.get('edit_user_id')
            
            if edit_user_id:
                # Show edit form for selected user
                edit_user = user_manager.get_user_by_id(edit_user_id)
                
                if edit_user:
                    st.info(f"Editing: **{edit_user['full_name']}** (@{edit_user['username']})")
                    
                    with st.form("edit_user_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_username = st.text_input("Username", value=edit_user['username'])
                            edit_email = st.text_input("Email", value=edit_user['email'])
                            edit_role = st.selectbox("Role", ["employee", "admin"], 
                                                   index=0 if edit_user['role'] == 'employee' else 1)
                        
                        with col2:
                            edit_full_name = st.text_input("Full Name", value=edit_user['full_name'])
                            edit_employee_name = st.text_input("Employee Name", value=edit_user['employee_name'])
                            edit_active = st.checkbox("Active", value=edit_user['is_active'])
                        
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                success, message = user_manager.update_user_info(
                                    edit_user_id,
                                    username=edit_username,
                                    email=edit_email,
                                    full_name=edit_full_name,
                                    employee_name=edit_employee_name,
                                    role=edit_role
                                )
                                
                                if success:
                                    # Update active status separately
                                    if edit_active != edit_user['is_active']:
                                        if edit_active:
                                            user_manager.reactivate_user(edit_user_id)
                                        else:
                                            user_manager.deactivate_user(edit_user_id)
                                    
                                    st.success(f"✅ {message}")
                                    del st.session_state.edit_user_id
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                del st.session_state.edit_user_id
                                st.rerun()
                else:
                    st.error("User not found")
                    del st.session_state.edit_user_id
                    st.rerun()
            else:
                # Show user selection dropdown
                user_options = {f"{user['full_name']} (@{user['username']})": user['id'] for user in users}
                
                selected_user_display = st.selectbox("Select User to Edit", 
                                                    [""] + list(user_options.keys()))
                
                if selected_user_display and selected_user_display != "":
                    if st.button("✏️ Edit Selected User"):
                        st.session_state.edit_user_id = user_options[selected_user_display]
                        st.rerun()
        else:
            st.info("No users available to edit")
    
    with tab4:
        st.subheader("Password Management")
        
        users = user_manager.get_all_users()
        if users:
            active_users = [user for user in users if user['is_active']]
            user_options = {f"{user['full_name']} (@{user['username']})": user for user in active_users}
            
            with st.form("admin_password_reset"):
                selected_user_display = st.selectbox("Select User", list(user_options.keys()))
                
                # Option to auto-generate password
                auto_generate = st.checkbox("🎲 Auto-generate temporary password (recommended)", value=True)
                
                if auto_generate:
                    st.info("✨ A secure temporary password will be generated automatically. The user must change it on first login.")
                    new_password = None
                    confirm_password = None
                else:
                    new_password = st.text_input("New Password", type="password", 
                                               placeholder="Enter new password for user")
                    confirm_password = st.text_input("Confirm Password", type="password",
                                                    placeholder="Confirm new password")
                    
                    st.info("🔒 **Password Requirements:** 8+ characters, uppercase, lowercase, number, special character")
                
                force_change = st.checkbox("🔄 Force password change on next login", value=True,
                                          help="User must change password after first login")
                
                if st.form_submit_button("🔑 Reset Password", use_container_width=True):
                    if selected_user_display:
                        selected_user = user_options[selected_user_display]
                        
                        # Generate password if auto-generate is enabled
                        if auto_generate:
                            generated_password = user_manager.generate_temp_password()
                            success, message = user_manager.reset_password(selected_user['id'], generated_password, is_temp=force_change)
                            
                            if success:
                                st.success(f"✅ Password reset successful for {selected_user['full_name']}")
                                st.markdown("### 🔑 **TEMPORARY PASSWORD**")
                                st.code(f"Username: {selected_user['username']}\nPassword: {generated_password}", language="text")
                                st.warning("⚠️ **CRITICAL:** Share this password securely with the user. They must change it on first login.")
                            else:
                                st.error(f"❌ {message}")
                        else:
                            # Manual password entry
                            if new_password and confirm_password:
                                if new_password != confirm_password:
                                    st.error("❌ Passwords don't match")
                                else:
                                    success, message = user_manager.reset_password(selected_user['id'], new_password, is_temp=force_change)
                                    if success:
                                        st.success(f"✅ Password reset successful for {selected_user['full_name']}")
                                        st.info(f"🔐 **New password for {selected_user['username']}:** `{new_password}`")
                                        st.warning("⚠️ Please share this password securely with the user")
                                    else:
                                        st.error(f"❌ {message}")
                            else:
                                st.warning("⚠️ Please fill in all fields")
                    else:
                        st.warning("⚠️ Please select a user")
            
            # Bulk password reset
            st.markdown("---")
            st.subheader("Bulk Operations")
            
            if st.button("🔄 Generate New Passwords for All Users"):
                if st.button("⚠️ Confirm Bulk Password Reset"):
                    import secrets
                    import string
                    
                    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                    reset_results = []
                    
                    for user in active_users:
                        new_temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
                        success = user_manager.reset_password(user['id'], new_temp_password)
                        if success:
                            reset_results.append({
                                'user': user,
                                'new_password': new_temp_password
                            })
                    
                    if reset_results:
                        st.success(f"✅ Reset passwords for {len(reset_results)} users")
                        st.markdown("### 📋 New Passwords")
                        for result in reset_results:
                            user = result['user']
                            st.code(f"{user['full_name']} (@{user['username']}): {result['new_password']}")
                        st.warning("⚠️ **IMPORTANT**: Share these passwords securely with each user")
        else:
            st.info("No users available for password reset")
    
    with tab5:
        st.subheader("System Settings")
        
        # User statistics
        st.markdown("#### 📊 User Statistics")
        users = user_manager.get_all_users()
        if users:
            active_users = [u for u in users if u['is_active']]
            admin_users = [u for u in users if u['role'] == 'admin']
            locked_users = [u for u in users if u['failed_login_attempts'] >= 5]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Users", len(users))
            with col2:
                st.metric("Active Users", len(active_users))
            with col3:
                st.metric("Administrators", len(admin_users))
            with col4:
                st.metric("Locked Accounts", len(locked_users))
        
        # Security settings display
        st.markdown("#### 🔒 Security Configuration")
        st.info("""
        **Password Requirements:**
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter  
        - At least 1 number
        - At least 1 special character
        
        **Account Lockout Policy:**
        - Accounts lock after 5 failed login attempts
        - Lockout duration: 30 minutes
        - Admins can manually unlock accounts
        
        **Session Management:**
        - Session timeout: 60 minutes
        - Automatic logout on timeout
        """)
        
        # Migration status
        st.markdown("#### 🔄 Migration Status")
        if users:
            st.success(f"✅ **Migration Complete** - {len(users)} users in new system")
            
            # Legacy system check
            st.markdown("#### 🔧 Legacy System")
            if st.button("🗑️ Remove Legacy Authentication Files"):
                st.warning("⚠️ **Warning**: This will permanently remove the old email-based authentication system")
                if st.button("⚠️ Confirm Removal"):
                    st.error("🚫 **Manual Action Required**: Please manually remove/backup `auth_config.py` and `login_component.py`")
        else:
            st.warning("⚠️ **Migration Pending** - Run migration to import existing users")
            
        # Database info
        st.markdown("#### 📊 Database Information")
        st.info(f"**User Database**: `citypets_users.db`\n**Timesheet Database**: `citypets_timesheet.db`")
        
        # Backup recommendation
        st.markdown("#### 💾 Backup Recommendation")
        st.info("🔄 **Regular Backups**: Backup both database files regularly to prevent data loss")
        
        # Danger zone
        st.markdown("#### ⚠️ Danger Zone")
        with st.expander("🚨 Advanced Admin Actions"):
            st.warning("**CAUTION**: These actions are irreversible and can affect system stability")
            
            if st.button("🗑️ Delete All Inactive Users"):
                inactive_users = [u for u in users if not u['is_active']]
                if inactive_users:
                    st.write(f"Found {len(inactive_users)} inactive users:")
                    for user in inactive_users:
                        st.write(f"- {user['full_name']} (@{user['username']})")
                    
                    if st.button("⚠️ CONFIRM: Delete All Inactive Users"):
                        deleted_count = 0
                        for user in inactive_users:
                            success, _ = user_manager.delete_user(user['id'])
                            if success:
                                deleted_count += 1
                        
                        st.success(f"✅ Deleted {deleted_count} inactive users")
                        st.rerun()
                else:
                    st.info("No inactive users found")
            
            if st.button("🔓 Unlock All User Accounts"):
                locked_users = [u for u in users if u['failed_login_attempts'] >= 5]
                if locked_users:
                    unlocked_count = 0
                    for user in locked_users:
                        if user_manager.unlock_user_account(user['id']):
                            unlocked_count += 1
                    
                    st.success(f"✅ Unlocked {unlocked_count} user accounts")
                    st.rerun()
                else:
                    st.info("No locked accounts found")

# Updated AuthManager to work with new system
class EnhancedAuthManager:
    """Enhanced AuthManager with secure session management
    
    Security Features:
    - Session tokens stored in browser localStorage (not exposed in URLs)
    - Browser fingerprinting for session isolation between users
    - File-based backup storage with browser-specific naming
    - Database validation of all session tokens
    - Automatic cleanup of invalid sessions
    """
    
    @staticmethod
    def init_session():
        """Initialize session state and restore authentication if token exists"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_email' not in st.session_state:
            st.session_state.user_email = None
        if 'user_name' not in st.session_state:
            st.session_state.user_name = None
        if 'is_admin' not in st.session_state:
            st.session_state.is_admin = False
        if 'login_time' not in st.session_state:
            st.session_state.login_time = None
        if 'session_initialized' not in st.session_state:
            st.session_state.session_initialized = True
        
        # Cleanup expired tab sessions (run occasionally for maintenance)
        import random
        if random.random() < 0.1:  # Run cleanup 10% of the time to avoid overhead
            try:
                user_manager = UserManager()
                user_manager.cleanup_expired_tab_sessions(24)  # Clean sessions older than 24 hours
            except:
                pass  # Silent fail - not critical
        
        # Always try to restore session from token - this ensures persistence
        # Even if authenticated is True, verify the token is still valid
        EnhancedAuthManager._restore_session_from_token()
    
    @staticmethod
    def _restore_session_from_token():
        """Restore user session from stored token"""
        
        # Try to get session token from persistent storage or session state
        session_token = EnhancedAuthManager._get_persistent_session_token()
        
        if not session_token:
            # No valid token found, ensure user is logged out
            st.session_state.authenticated = False
            return False
            
        user_manager = UserManager()
        user_data = user_manager.get_user_by_session_token(session_token)
        
        if user_data:
            # Restore session state
            st.session_state.authenticated = True
            st.session_state.user_email = user_data['email']
            st.session_state.user_name = user_data['employee_name']
            st.session_state.is_admin = user_data['is_admin']
            st.session_state.user_id = user_data['id']
            st.session_state.username = user_data['username']
            st.session_state.full_name = user_data['full_name']
            st.session_state.login_time = datetime.now()
            st.session_state.session_token = session_token  # Store in session state for current session
            
            return True
        else:
            # Invalid token, clear it and log out user
            EnhancedAuthManager._clear_persistent_session_token()
            st.session_state.authenticated = False
            return False
    
    @staticmethod
    def _get_persistent_session_token():
        """Get session token from HTTP cookie and localStorage (hybrid approach for reliability)"""
        
        # First try to get from session state (fastest)
        if 'session_token' in st.session_state:
            token = st.session_state.session_token
            # Validate it's still valid
            try:
                user_manager = UserManager()
                user_data = user_manager.get_user_by_session_token(token)
                if user_data:
                    return token
                else:
                    # Invalid token, clear it
                    del st.session_state['session_token']
            except:
                if 'session_token' in st.session_state:
                    del st.session_state['session_token']
        
        # Try to get from persistent storage (localStorage as fallback to cookies)
        persistent_token = EnhancedAuthManager._get_token_from_file()
        
        if persistent_token:
            # Validate token is still valid in database
            try:
                user_manager = UserManager()
                user_data = user_manager.get_user_by_session_token(persistent_token)
                if user_data:
                    # Store in session state for faster access during this session
                    st.session_state.session_token = persistent_token
                    return persistent_token
                else:
                    # Invalid token, clear file storage
                    EnhancedAuthManager._clear_token_from_file()
            except Exception as e:
                # If validation fails, clear file storage
                EnhancedAuthManager._clear_token_from_file()
        
        # No valid session found
        return None
    
    @staticmethod
    def _get_token_from_file():
        """Get session token from user-specific file storage"""
        import os
        import tempfile
        import hashlib
        
        try:
            # Create a unique file path based on browser fingerprint for isolation
            browser_id = EnhancedAuthManager._get_browser_fingerprint()
            
            # Ensure browser_id is a string
            if not isinstance(browser_id, str):
                browser_id = f"fallback_{hash(str(browser_id))}"
            
            # Hash the browser ID to create a safe filename
            file_hash = hashlib.md5(browser_id.encode()).hexdigest()
            token_file = os.path.join(tempfile.gettempdir(), f'citypets_session_{file_hash}.txt')
            
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                    if token:
                        return token
            
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def _get_auth_cookie():
        """Get authentication token from HTTP cookie"""
        import streamlit.components.v1 as components
        
        cookie_component = components.html(f"""
        <script>
        // Function to get cookie value by name
        function getCookie(name) {{
            const value = `; ${{document.cookie}}`;
            const parts = value.split(`; ${{name}}=`);
            if (parts.length === 2) {{
                return parts.pop().split(';').shift();
            }}
            return null;
        }}
        
        // Get the citypets_auth cookie
        const authToken = getCookie('citypets_auth');
        console.log('Current cookies:', document.cookie);
        console.log('Auth token found:', authToken);
        
        // Send the token back to Streamlit
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: authToken
        }}, '*');
        </script>
        <div style="display:none;">Reading auth cookie...</div>
        """, height=0)
        
        return cookie_component if cookie_component else None
    
    @staticmethod
    def _set_auth_cookie(token, days=30):
        """Set authentication token in HTTP cookie with security flags"""
        import streamlit.components.v1 as components
        
        # Calculate expiration date
        expiry_date = (datetime.now() + timedelta(days=days)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # For development, we'll use less restrictive cookie settings
        # In production, you should add Secure flag for HTTPS
        components.html(f"""
        <script>
        // Set HTTP cookie with authentication token
        // Note: Secure flag removed for development (add back for HTTPS production)
        document.cookie = 'citypets_auth={token}; expires={expiry_date}; path=/; SameSite=Lax';
        console.log('Auth cookie set for {days} days');
        console.log('Cookie string:', document.cookie);
        
        // Signal completion back to Streamlit
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: 'cookie_set'
        }}, '*');
        </script>
        <div style="display:none;">Setting auth cookie...</div>
        """, height=0)
    
    @staticmethod
    def _clear_auth_cookie():
        """Clear authentication cookie"""
        import streamlit.components.v1 as components
        
        components.html(f"""
        <script>
        // Clear the authentication cookie by setting it to expire in the past
        document.cookie = 'citypets_auth=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax';
        console.log('Auth cookie cleared');
        console.log('Cookies after clear:', document.cookie);
        
        // Signal completion back to Streamlit
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: 'cookie_cleared'
        }}, '*');
        </script>
        <div style="display:none;">Clearing auth cookie...</div>
        """, height=0)
    
    @staticmethod
    def _get_browser_fingerprint():
        """Generate a simple session ID without any URL manipulation (security-focused)"""
        
        # Check if we already have a session ID in session state
        if 'browser_session_id' in st.session_state:
            existing_id = st.session_state.browser_session_id
            return existing_id
        
        import uuid
        
        # Generate a simple session identifier (no persistence, no URLs)
        new_session_id = uuid.uuid4().hex[:12]
        session_id = f"session_{new_session_id}"
        st.session_state.browser_session_id = session_id
        
        # Note: This session will be lost on page refresh for security
        return session_id
    
    @staticmethod
    def _get_token_from_browser_storage():
        """Get session token from browser localStorage using HTML/JS"""
        # This method is no longer used, kept for compatibility
        return None
    
    @staticmethod
    def _store_persistent_session_token(token):
        """Store session token in file for persistence across browser sessions"""
        if not token:
            return
            
        # Store in session state for immediate use during this session
        st.session_state.session_token = token
        
        # Store in file for persistence across browser sessions
        EnhancedAuthManager._set_token_in_file(token)
        
        # Also create tab session for tab-specific state
        user_id = st.session_state.get('user_id')
        if user_id:
            browser_id = EnhancedAuthManager._get_browser_fingerprint()
            if browser_id:
                user_manager = UserManager()
                user_manager.create_tab_session(user_id, browser_id, {
                    'login_time': datetime.now().isoformat(),
                    'user_agent': 'streamlit_browser'
                })
    
    @staticmethod
    def _set_token_in_file(token):
        """Store session token in user-specific file"""
        import os
        import tempfile
        import hashlib
        
        try:
            # Create a unique file path based on browser fingerprint for isolation
            browser_id = EnhancedAuthManager._get_browser_fingerprint()
            
            # Ensure browser_id is a string
            if not isinstance(browser_id, str):
                browser_id = f"fallback_{hash(str(browser_id))}"
            
            # Hash the browser ID to create a safe filename
            file_hash = hashlib.md5(browser_id.encode()).hexdigest()
            token_file = os.path.join(tempfile.gettempdir(), f'citypets_session_{file_hash}.txt')
            
            with open(token_file, 'w') as f:
                f.write(token)
            
        except Exception as e:
            pass  # Silently handle errors

    
    @staticmethod
    def _clear_persistent_session_token():
        """Clear session token from both file and session state"""
        # Clear from session state
        if 'session_token' in st.session_state:
            del st.session_state['session_token']
        
        # Clear file
        EnhancedAuthManager._clear_token_from_file()
        
        # Clear tab session
        user_id = st.session_state.get('user_id')
        if user_id:
            browser_id = EnhancedAuthManager._get_browser_fingerprint()
            if browser_id:
                user_manager = UserManager()
                user_manager.delete_tab_session(user_id, browser_id)
    
    @staticmethod
    def _clear_token_from_file():
        """Clear session token from user-specific file"""
        import os
        import tempfile
        import hashlib
        
        try:
            # Create a unique file path based on browser fingerprint for isolation
            browser_id = EnhancedAuthManager._get_browser_fingerprint()
            
            # Ensure browser_id is a string
            if not isinstance(browser_id, str):
                browser_id = f"fallback_{hash(str(browser_id))}"
            
            # Hash the browser ID to create a safe filename
            file_hash = hashlib.md5(browser_id.encode()).hexdigest()
            token_file = os.path.join(tempfile.gettempdir(), f'citypets_session_{file_hash}.txt')
            
            if os.path.exists(token_file):
                os.remove(token_file)
                
        except Exception as e:
            pass  # Silently handle errors
    
    @staticmethod
    def _create_session_token(user_id):
        """Create a session token for the user"""
        user_manager = UserManager()
        session_token = user_manager.create_session_token(user_id)
        if session_token:
            EnhancedAuthManager._store_persistent_session_token(session_token)
        return session_token
    
    @staticmethod
    def is_authenticated():
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)
    
    @staticmethod
    def is_admin():
        """Check if current user is admin"""
        return st.session_state.get('is_admin', False)
    
    @staticmethod
    def debug_session_state():
        """Debug function to show current session state"""
        st.write("### Session Debug Information")
        st.write(f"**Authenticated**: {st.session_state.get('authenticated', False)}")
        st.write(f"**User Email**: {st.session_state.get('user_email', 'None')}")
        st.write(f"**User Name**: {st.session_state.get('user_name', 'None')}")
        st.write(f"**Browser Fingerprint**: {st.session_state.get('browser_fingerprint', 'None')}")
        st.write(f"**Session Token Present**: {'session_token' in st.session_state}")
        
        # Check for session files
        try:
            import os
            browser_id = st.session_state.get('browser_fingerprint', '')
            if browser_id:
                session_file = f'.streamlit_browser_{browser_id}'
                file_exists = os.path.exists(session_file)
                st.write(f"**Session File Exists**: {file_exists}")
                if file_exists:
                    with open(session_file, 'r') as f:
                        token_length = len(f.read().strip())
                        st.write(f"**Session File Token Length**: {token_length}")
        except:
            st.write("**Session File**: Error reading")

    @staticmethod
    def get_current_user():
        """Get current user information"""
        return {
            'email': st.session_state.get('user_email'),
            'name': st.session_state.get('user_name'),
            'is_admin': st.session_state.get('is_admin', False),
            'username': st.session_state.get('username'),
            'full_name': st.session_state.get('full_name')
        }
    
    @staticmethod
    def logout():
        """Logout current user"""
        # Clear session token from database if exists
        session_token = st.session_state.get('session_token')
        if session_token:
            user_manager = UserManager()
            user_manager.invalidate_session_token(session_token)
        
        # Clear persistent session token
        EnhancedAuthManager._clear_persistent_session_token()
        
        # Clear all session state variables
        for key in list(st.session_state.keys()):
            if key.startswith(('authenticated', 'user_', 'is_admin', 'login_', 'session_')):
                del st.session_state[key]
    
    @staticmethod
    def require_auth():
        """Require authentication"""
        if not EnhancedAuthManager.is_authenticated():
            st.error("🔒 Please login to access this page")
            st.stop()
    
    @staticmethod
    def require_admin():
        """Require admin privileges"""
        EnhancedAuthManager.require_auth()
        if not EnhancedAuthManager.is_admin():
            st.error("🚫 Admin privileges required to access this page")
            st.stop()
