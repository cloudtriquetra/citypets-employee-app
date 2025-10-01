import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import requests
import json
import os
# from dotenv import load_dotenv  # Not currently used but available for future expansion
import plotly.express as px
import plotly.graph_objects as go
import uuid
import re
from pathlib import Path
import threading
import io

# Import employee configuration
from employee_config import (
    EMPLOYEES, JOB_TYPES, JOB_TYPE_RESTRICTIONS,
    get_employee_rate, get_job_type_info, 
    list_employees, list_job_types,
    get_employee_job_types, get_employee_admin_job_types, is_job_type_allowed_for_employee,
    get_pet_custom_rates, set_pet_custom_rate, remove_pet_custom_rate,
    has_pet_custom_rate, list_pets_with_custom_rates,
    add_employee, remove_employee, update_employee_base_rate,
    get_all_employee_data, clone_employee_rates,
    add_job_type_restriction, remove_job_type_restriction,
    get_job_type_restrictions, list_restricted_job_types,
    get_employees_allowed_for_job_type
)

# Import new authentication system
from user_management import UserManager, render_advanced_login_page, render_user_management_page, EnhancedAuthManager

# Jobs that require pet names
JOBS_REQUIRING_PETS = [
    "pet_sitting", "walk", 
    "cat_visit", "dog_at_home", "cat_at_home", "training"
]

# Load environment variables (currently not used but kept for future expansion)
# load_dotenv()

# Constants
DB_NAME = 'citypets_timesheet.db'
TOTAL_AMOUNT_PLN = 'Total Amount (PLN)'
EMPLOYEE_NAME = 'Employee Name'

# Configuration
st.set_page_config(
    page_title="CityPets Employee Timesheet",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Employee configurations with different rates for different job types
# Now imported from employee_config.py

# Display job types for user interface
JOB_TYPES_DISPLAY = {
    "hotel": "Hotel/Daycare",
    "walk": "Dog Walks", 
    "overnight_hotel": "Overnight Hotel",
    "cat_visit": "Cat Visit",
    "pet_sitting": "Pet Sitting",  # Unified pet sitting option
    "dog_at_home": "Dog@Home",
    "cat_at_home": "Cat@Home",
    "management": "Management",
    "transport": "Transport",
    "transport_km": "Transport KM",
    "training": "Training",
    "expense": "Expense",
    "night_shift": "Night Shift",
    # Legacy mappings for backward compatibility
    "hotel_daycare": "Hotel/Daycare",
    "walks": "Dog Walks"
}

# Database initialization
def validate_pet_names_required(job_type, pet_names):
    """Validate that pet names are provided for jobs that require them"""
    if job_type in JOBS_REQUIRING_PETS:
        if not pet_names or (isinstance(pet_names, list) and len(pet_names) == 0):
            return False, f"Pet name(s) are mandatory for {job_type}"
    return True, ""

def validate_expense_requirements(job_type, user_message):
    """Validate that expenses have proper business purpose description."""
    if job_type == "expense":
        message_lower = user_message.lower()
        
        # Check for PURPOSE-related keywords (not just service type)
        purpose_keywords = [
            "for", "to", "from", "home", "hotel", "work", "office", "client", "meeting", 
            "pickup", "drop", "visit", "appointment", "emergency", "vet", "supplies",
            "food", "medication", "equipment", "training", "conference"
        ]
        
        # Check for directional/purpose phrases that explain WHY the expense happened
        purpose_phrases = [
            "from hotel", "to hotel", "from home", "to home", "from work", "to work",
            "for work", "for hotel", "for client", "for meeting", "for pickup",
            "for emergency", "for supplies", "for food", "for training"
        ]
        
        has_purpose_keyword = any(keyword in message_lower for keyword in purpose_keywords)
        has_purpose_phrase = any(phrase in message_lower for phrase in purpose_phrases)
        
        # Check if message explains the business purpose
        has_clear_purpose = has_purpose_keyword or has_purpose_phrase
        
        # Additional check: must have more than just service type + amount
        words = message_lower.split()
        service_words = ["uber", "taxi", "bolt", "parking", "gas", "fuel", "toll"]
        has_service_type = any(service in message_lower for service in service_words)
        
        # If it has a service type, it MUST also have purpose
        if has_service_type and not has_clear_purpose:
            return False, "Please specify the purpose of the expense. Example: 'Expense Uber from hotel to client 20 PLN' or 'Expense parking for work meeting 15 PLN'"
        
        # General description check
        meaningful_words = [w for w in words if w not in ["expense", "pln"] and not w.replace(".", "").isdigit()]
        if len(meaningful_words) < 2:
            return False, "Expense description must explain the purpose. Example: 'Expense supplies for hotel dogs 25 PLN'"
    
    return True, ""

def save_uploaded_file(uploaded_file, employee_name, expense_type="expense"):
    """Save uploaded file to permanent storage and return file path."""
    if not uploaded_file:
        return None
    
    # Create uploads directory if it doesn't exist
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    
    # Generate unique filename to avoid conflicts
    file_extension = Path(uploaded_file.name).suffix.lower()
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{employee_name}_{expense_type}_{uuid.uuid4().hex[:8]}{file_extension}"
    
    # Full file path
    file_path = uploads_dir / unique_filename
    
    try:
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return str(file_path)
    except Exception as e:
        st.error(f"Failed to save file: {str(e)}")
        return None

def get_file_download_link(file_path, display_name=None):
    """Create a download link for a stored file."""
    if not file_path or not os.path.exists(file_path):
        return "File not found"
    
    display_name = display_name or os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    # For Streamlit, we'll create a button that allows download
    return f"📎 {display_name} ({file_size_mb:.1f} MB)"

def create_file_download_button(file_path, display_name=None, key=None):
    """Create a download button for a stored file."""
    if not file_path or not os.path.exists(file_path):
        return False
    
    display_name = display_name or os.path.basename(file_path)
    
    try:
        with open(file_path, "rb") as file:
            file_data = file.read()
        
        return st.download_button(
            label=f"📎 Download {display_name}",
            data=file_data,
            file_name=display_name,
            mime="application/octet-stream",
            key=key
        )
    except Exception as e:
        st.error(f"Error creating download button: {str(e)}")
        return False

def split_multi_day_pet_sitting(start_date, start_time, end_date, end_time):
    """Split multi-day pet sitting into appropriate segments based on duration"""
    # Combine dates and times
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    
    # Calculate total duration
    total_hours = (end_datetime - start_datetime).total_seconds() / 3600
    
    segments = []
    current_time = start_datetime
    
    while current_time < end_datetime:
        # Calculate remaining hours
        remaining_hours = (end_datetime - current_time).total_seconds() / 3600
        
        if remaining_hours <= 8:
            # Use hourly rate for <= 8 hours
            segments.append({
                'job_type': 'pet_sitting_hourly',
                'start_time': current_time.isoformat(),
                'end_time': end_datetime.isoformat()
            })
            break
        elif remaining_hours <= 24:
            # Single overnight segment (8-24 hours)
            segments.append({
                'job_type': 'overnight_pet_sitting',
                'start_time': current_time.isoformat(),
                'end_time': end_datetime.isoformat()
            })
            break
        else:
            # Full 24-hour overnight segment
            segment_end = current_time + timedelta(hours=24)
            segments.append({
                'job_type': 'overnight_pet_sitting',
                'start_time': current_time.isoformat(),
                'end_time': segment_end.isoformat()
            })
            current_time = segment_end
    
    return segments

def split_long_shifts(start_time, end_time, job_type):
    """Split long shifts into hotel, overnight, and hotel segments"""
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)
    
    # Calculate total hours
    total_hours = (end_dt - start_dt).total_seconds() / 3600
    
    # If pet sitting is more than 8 hours, convert to overnight pet sitting
    if job_type == "pet_sitting_hourly" and total_hours > 8:
        return [{
            'job_type': 'overnight_pet_sitting',
            'start_time': start_time,
            'end_time': end_time,
            'note': f'Converted from {total_hours:.1f}h pet sitting to overnight'
        }]
    
    # For hotel work crossing days, split into segments
    if job_type == "hotel" and start_dt.date() != end_dt.date():
        segments = []
        current_dt = start_dt
        
        while current_dt.date() < end_dt.date():
            # Hotel work until 20:00 (8 PM)
            day_end = datetime.combine(current_dt.date(), datetime.min.time().replace(hour=20))
            if current_dt < day_end:
                segments.append({
                    'job_type': 'hotel',
                    'start_time': current_dt.isoformat(),
                    'end_time': day_end.isoformat(),
                    'note': 'Hotel shift (day portion)'
                })
                current_dt = day_end
            
            # Overnight shift from 20:00 to 08:00 next day
            overnight_start = datetime.combine(current_dt.date(), datetime.min.time().replace(hour=20))
            overnight_end = datetime.combine(current_dt.date() + timedelta(days=1), datetime.min.time().replace(hour=8))
            
            if current_dt <= overnight_start and end_dt >= overnight_end:
                segments.append({
                    'job_type': 'overnight_hotel',
                    'start_time': overnight_start.isoformat(),
                    'end_time': overnight_end.isoformat(),
                    'note': 'Overnight shift (20:00-08:00)'
                })
            
            # Move to next day morning
            current_dt = overnight_end
        
        # Final day portion if any
        if current_dt < end_dt:
            segments.append({
                'job_type': 'hotel',
                'start_time': current_dt.isoformat(),
                'end_time': end_dt.isoformat(),
                'note': 'Hotel shift (final day portion)'
            })
        elif current_dt == end_dt and current_dt.hour == 8:
            # If shift ends exactly at 8 AM, add a standard 4-hour morning shift (8-12)
            morning_end = current_dt.replace(hour=12)
            segments.append({
                'job_type': 'hotel',
                'start_time': current_dt.isoformat(),
                'end_time': morning_end.isoformat(),
                'note': 'Hotel shift (morning portion 08:00-12:00)'
            })
        
        return segments
    
    # No splitting needed
    return [{
        'job_type': job_type,
        'start_time': start_time,
        'end_time': end_time,
        'note': None
    }]

def initialize_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create timesheet table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timesheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            job_type TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_hours REAL,
            rate_per_hour REAL NOT NULL,
            total_amount REAL NOT NULL,
            description TEXT,
            pet_names TEXT,
            date_created TEXT NOT NULL,
            week_start_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            file_path TEXT
        )
    ''')
    
    # Add file_path column to existing tables if it doesn't exist
    try:
        cursor.execute('ALTER TABLE timesheet ADD COLUMN file_path TEXT')
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Add payment_status column to existing tables if it doesn't exist
    try:
        cursor.execute('ALTER TABLE timesheet ADD COLUMN payment_status TEXT DEFAULT "pending"')
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Create chat messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT,
            timestamp TEXT NOT NULL,
            processed BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.commit()
    conn.close()

# Calculate work duration and payment amount
def calculate_work_duration_and_amount(start_time, end_time, job_type, employee_name, quantity=1, pet_names=None):
    """Calculate work duration and payment amount"""
    # Handle expenses (quantity = amount in PLN)
    if job_type == "expense":
        return quantity, quantity  # Return amount as both duration and total amount
    
    # Handle KM-based transport (quantity = kilometers)
    if job_type in ["transport_km"]:
        rate = get_employee_rate(employee_name, job_type, pet_names)
        total_amount = quantity * rate
        return quantity, total_amount  # Return KM and total amount
    
    # Handle cat visits (count-based, no duration needed)
    if job_type == "cat_visit":
        rate = get_employee_rate(employee_name, job_type, pet_names)
        total_amount = quantity * rate
        return quantity, total_amount  # Return visit count and total amount
    
    # Handle overnight jobs (flat rate)
    if job_type in ["overnight_hotel", "night_shift", "overnight_pet_sitting", "holiday_on"]:
        rate = get_employee_rate(employee_name, job_type, pet_names)
        if job_type in ["overnight_hotel", "night_shift"]:
            return 12.0, rate  # 12 hours for overnight hotel
        else:
            return 1.0, rate  # Flat rate for other overnight services
    
    # Handle per-day services (dog_at_home, cat_at_home)
    if job_type in ["dog_at_home", "cat_at_home"]:
        # For day-based services, calculate number of days (overnight stays)
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        days = max(1, (end.date() - start.date()).days)  # Minimum 1 day, no +1 for overnight counting
        
        rate = get_employee_rate(employee_name, job_type, pet_names)
        total_amount = days * rate
        return days, total_amount  # Return days and total amount
    
    # Handle walks with default 1-hour duration if no end time provided
    if job_type == "walk":
        if not end_time or end_time == start_time:
            # Default to 1 hour for walks when no duration specified
            rate = get_employee_rate(employee_name, job_type, pet_names)
            total_amount = 1.0 * rate
            return 1.0, total_amount
    
    # Calculate duration for hourly jobs
    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)
    duration = (end - start).total_seconds() / 3600  # Convert to hours
    
    rate = get_employee_rate(employee_name, job_type, pet_names)
    total_amount = duration * rate
    
    return duration, total_amount

def save_timesheet_entry(data):
    """Save processed timesheet entry to database"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10.0)  # Add timeout to prevent hanging
        cursor = conn.cursor()
        
        # Get quantity (for KM transport or visit-based services)
        quantity = data.get('quantity', 1)
        pet_names = data.get('pet_names', [])
        
        # Pre-calculate employee rate once to avoid multiple calls
        employee_rate = get_employee_rate(data['employee_name'], data['job_type'], pet_names)
        
        # Calculate duration and amount based on job type
        if data['job_type'] in ["transport_km"]:
            # KM-based transport
            duration, total_amount = calculate_work_duration_and_amount(
                data['start_time'], data.get('end_time', data['start_time']), data['job_type'], data['employee_name'], quantity, pet_names
            )
            duration_label = f"{duration} KM"
        elif data['job_type'] == "cat_visit":
            # Cat visits - count-based, no duration needed
            duration, total_amount = calculate_work_duration_and_amount(
                data['start_time'], data.get('end_time', data['start_time']), data['job_type'], data['employee_name'], quantity, pet_names
            )
            duration_label = f"{duration} visit{'s' if duration != 1 else ''}"
        elif data['job_type'] in ["dog_at_home", "cat_at_home"]:
            # Day-based services
            duration, total_amount = calculate_work_duration_and_amount(
                data['start_time'], data['end_time'], data['job_type'], data['employee_name'], quantity, pet_names
            )
            duration_label = f"{duration} day{'s' if duration != 1 else ''}"
        elif data['job_type'] == "walk":
            # Walks - default to 1 hour if no end time specified
            end_time = data.get('end_time', data['start_time'])
            duration, total_amount = calculate_work_duration_and_amount(
                data['start_time'], end_time, data['job_type'], data['employee_name'], 1, pet_names
            )
            duration_label = f"{duration} hour{'s' if duration != 1 else ''}"
        elif data['job_type'] == "expense":
            # Expenses - quantity contains the amount in PLN
            duration, total_amount = calculate_work_duration_and_amount(
                data['start_time'], data.get('end_time', data['start_time']), data['job_type'], data['employee_name'], quantity, pet_names
            )
            duration_label = f"{total_amount:.2f} PLN"
        elif data['job_type'] in ["overnight_hotel", "night_shift", "overnight_pet_sitting", "holiday_on"]:
            # Flat rate services - use pre-calculated rate
            if data['job_type'] in ["overnight_hotel", "night_shift"]:
                duration, total_amount = 12.0, employee_rate
                duration_label = f"{duration} hours"
            else:
                duration, total_amount = 1.0, employee_rate
                duration_label = "1 service"
        else:
            # Hourly services
            duration, total_amount = calculate_work_duration_and_amount(
                data['start_time'], data['end_time'], data['job_type'], data['employee_name'], 1, pet_names
            )
            duration_label = f"{duration} hours"
        
        # Get week start date (Monday)
        start_date = datetime.fromisoformat(data['start_time'])
        week_start = start_date - timedelta(days=start_date.weekday())
        
        cursor.execute('''
            INSERT INTO timesheet (
                employee_name, job_type, start_time, end_time, duration_hours,
                rate_per_hour, total_amount, description, pet_names,
                date_created, week_start_date, file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['employee_name'],
            data['job_type'],
            data['start_time'],
            data.get('end_time'),
            duration,
            employee_rate,  # Use pre-calculated rate
            total_amount,
            data.get('description', ''),
            json.dumps(data.get('pet_names', [])),
            datetime.now().isoformat(),
            week_start.date().isoformat(),
            data.get('file_path')
        ))
        
        conn.commit()
        return True, duration_label, total_amount
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise Exception(f"Database error: {str(e)}")
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"Save error: {str(e)}")
    finally:
        if conn:
            conn.close()

def get_timesheet_data(week_start=None):
    """Get timesheet data from database"""
    conn = sqlite3.connect(DB_NAME)
    
    if week_start:
        query = '''
            SELECT * FROM timesheet 
            WHERE week_start_date = ? 
            ORDER BY date_created DESC
        '''
        df = pd.read_sql_query(query, conn, params=(week_start,))
    else:
        query = 'SELECT * FROM timesheet ORDER BY date_created DESC'
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df

def get_timesheet_data_with_payment_filter(week_start=None, payment_status=None, start_date=None, end_date=None):
    """Get timesheet data from database with payment status and date filtering"""
    conn = sqlite3.connect(DB_NAME)
    
    # Base query
    query = '''
        SELECT *, COALESCE(payment_status, 'pending') as payment_status_clean
        FROM timesheet 
        WHERE 1=1
    '''
    params = []
    
    # Add week filter
    if week_start:
        query += ' AND week_start_date = ?'
        params.append(week_start)
    
    # Add date range filter
    if start_date and end_date:
        query += ' AND date(start_time) BETWEEN ? AND ?'
        params.append(start_date.isoformat())
        params.append(end_date.isoformat())
    
    # Add payment status filter
    if payment_status == "pending":
        query += ' AND COALESCE(payment_status, "pending") = "pending"'
    elif payment_status == "paid":
        query += ' AND COALESCE(payment_status, "pending") = "paid"'
    
    query += ' ORDER BY date_created DESC'
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_weekly_summary():
    """Get weekly summary for all employees"""
    conn = sqlite3.connect(DB_NAME)
    
    query = '''
        SELECT 
            employee_name,
            week_start_date,
            SUM(duration_hours) as total_hours,
            SUM(total_amount) as total_amount,
            COUNT(*) as total_entries
        FROM timesheet 
        GROUP BY employee_name, week_start_date
        ORDER BY week_start_date DESC, employee_name
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Initialize database
initialize_database()

# Initialize authentication system
EnhancedAuthManager.init_session()

    
    
    
        
            
    
            
                
                    

    
    
    
        
        
    
        
        
                
                
                
        
        
    

def main():
    """Main application function with enhanced authentication"""
    
    # Check if user is authenticated with new system only
    is_auth = EnhancedAuthManager.is_authenticated()
    
    if not is_auth:
        render_advanced_login_page()
        return
    
    # User is authenticated, show main application
    render_main_application()

def render_enhanced_user_info():
    """Render enhanced user information with password change option"""
    if EnhancedAuthManager.is_authenticated():
        user = EnhancedAuthManager.get_current_user()
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Current User")
        st.sidebar.markdown(f"**Name:** {user['name']}")
        st.sidebar.markdown(f"**Email:** {user['email']}")
        
        if user.get('username'):
            st.sidebar.markdown(f"**Username:** {user['username']}")
        
        if user['is_admin']:
            st.sidebar.markdown("**Role:** 👑 Administrator")
        else:
            st.sidebar.markdown("**Role:** 👤 Employee")
        
        # Enhanced features for new auth system users
        st.sidebar.markdown("---")
        
        # Password change option
        if st.sidebar.button("🔑 Change Password"):
            st.session_state.show_password_change = True
        
        # Show password change form if requested
        if st.session_state.get('show_password_change', False):
            with st.sidebar.form("change_password_form"):
                st.markdown("#### Change Password")
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        if all([current_password, new_password, confirm_password]):
                            if new_password != confirm_password:
                                st.error("Passwords don't match")
                            else:
                                user_manager = UserManager()
                                # Verify current password first
                                username_or_email = user.get('username') or user.get('email')
                                success, user_data = user_manager.authenticate_user(username_or_email, current_password)
                                if success:
                                    reset_success, message = user_manager.reset_password(user_data['id'], new_password)
                                    if reset_success:
                                        st.success("Password updated!")
                                        st.session_state.show_password_change = False
                                        st.rerun()
                                    else:
                                        st.error("Failed to update password")
                                else:
                                    st.error("Current password incorrect")
                        else:
                            st.warning("Fill all fields")
                
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_password_change = False
                        st.rerun()
        
        # Logout button
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Logout", key="logout_btn"):
            EnhancedAuthManager.logout()
            if 'show_password_change' in st.session_state:
                del st.session_state.show_password_change
            st.rerun()

def render_main_application():
    """Render the main application for authenticated users"""
    
    # Render user info in sidebar
    render_enhanced_user_info()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**CityPets Employee Timesheet v2.0**")
    
    # Get current user
    current_user = EnhancedAuthManager.get_current_user()
    
    # Sidebar navigation
    st.sidebar.title("🐕 CityPets Timesheet")
    
    # Different navigation options based on user role
    if current_user['is_admin']:
        # Admin sees all pages
        page_options = [
            "📝 Employee Timesheet Form", 
            "💳 Admin Dashboard", 
            "👥 Employee Management",
            "📊 Reports",
            "📁 Data Export",
            "🔐 User Management"
        ]
    else:
        # Regular employees only see employee pages
        page_options = [
            "📝 Employee Timesheet Form", 
            "📊 My Reports"
        ]
    
    page = st.sidebar.selectbox("Choose a page", page_options)
    
    # Route to appropriate page
    if page == "📝 Employee Timesheet Form":
        render_timesheet_form(current_user)
    elif page == "💳 Admin Dashboard":
        EnhancedAuthManager.require_admin()  # Ensure admin access
        render_admin_dashboard()
    elif page == "👥 Employee Management":
        EnhancedAuthManager.require_admin()  # Ensure admin access
        render_employee_management()
    elif page == "📊 Reports":
        EnhancedAuthManager.require_admin()  # Ensure admin access
        render_reports_page()
    elif page == "📊 My Reports":
        render_employee_reports(current_user)
    elif page == "📁 Data Export":
        EnhancedAuthManager.require_admin()  # Ensure admin access
        render_data_export()
    elif page == "🔐 User Management":
        EnhancedAuthManager.require_admin()  # Ensure admin access
        render_user_management_page()

def render_timesheet_form(current_user):
    """Render timesheet form for authenticated user"""
    st.title("📝 Employee Timesheet Form")
    
    st.write("Fill in your work details using the form below")
    
    # For regular employees, auto-select their name (no dropdown)
    if not current_user['is_admin']:
        selected_employee = current_user['name']
        st.info(f"📝 Submitting timesheet for: **{selected_employee}**")
    else:
        # Admins can select any employee
        selected_employee = st.selectbox("Select Employee:", list_employees())
    
    # Verify employee has access to job types
    available_job_types = get_employee_job_types(selected_employee)
    
    if not available_job_types:
        st.error(f"❌ {selected_employee} does not have access to any job types. Please contact admin.")
        st.stop()
    
    # Job type selection with display names
    job_type_display_options = [JOB_TYPES_DISPLAY.get(jt, jt) for jt in available_job_types]
    selected_job_display = st.selectbox("Job Type:", job_type_display_options)
    
    # Get the actual job type key
    selected_job_type = None
    for jt in available_job_types:
        if JOB_TYPES_DISPLAY.get(jt, jt) == selected_job_display:
            selected_job_type = jt
            break
    
    # Display info for day-based services
    if selected_job_type in ["dog_at_home", "cat_at_home"]:
        st.info("ℹ️ Dog@Home and Cat@Home services are billed per day. Select start and end dates, and payment will be calculated as: (number of days) × (daily rate)")
    
    # Date selection
    if selected_job_type in ["pet_sitting", "dog_at_home", "cat_at_home"]:
        # Multi-day services
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("Start Date:", value=datetime.today().date())
        with col_end:
            end_date = st.date_input("End Date:", value=datetime.today().date())
        
        # Validate date order
        if end_date < start_date:
            st.error("❌ End date must be on or after start date")
            st.stop()
    else:
        # Single day for other job types
        entry_date = st.date_input("Date:", value=datetime.today().date())
        start_date = entry_date
        end_date = entry_date
    
    # Time fields (conditional based on job type)
    if selected_job_type not in ["dog_at_home", "cat_at_home"]:
        col1, col2 = st.columns(2)
        
        # Create time options for dropdown (24-hour format)
        time_options = []
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                time_str = f"{hour:02d}:{minute:02d}"
                time_options.append(time_str)
        
        with col1:
            if selected_job_type in ["cat_visit", "expense"]:
                start_time_str = st.selectbox("Time (optional):", [""] + time_options, index=0)
                if start_time_str:
                    start_time = datetime.strptime(start_time_str, "%H:%M").time()
                else:
                    # For expenses without specific time, use noon as neutral time
                    start_time = datetime.strptime("12:00", "%H:%M").time()
                end_time = None
            elif selected_job_type == "transport_km":
                # Transport KM has optional start time
                start_time_str = enhanced_time_input("Start Time (optional):", "", key="transport_start", allow_empty=True)
                if start_time_str:
                    try:
                        start_time = datetime.strptime(start_time_str, "%H:%M").time()
                    except:
                        start_time = datetime.now().time()
                else:
                    start_time = datetime.now().time()
            elif selected_job_type == "overnight_hotel":
                # Overnight Hotel must start at 19:00 or 20:00 only
                allowed_start_times = ["19:00", "20:00"]
                start_time_str = st.selectbox("Start Time (Overnight Hotel):", allowed_start_times, index=0)
                try:
                    start_time = datetime.strptime(start_time_str, "%H:%M").time()
                except:
                    start_time = datetime.strptime("19:00", "%H:%M").time()
            elif selected_job_type in ["hotel", "hotel_daycare"]:
                # Hotel/Day Care default start time
                start_time_str = enhanced_time_input("Start Time:", "08:00", key="hotel_daycare_start")
                if start_time_str:
                    try:
                        start_time = datetime.strptime(start_time_str, "%H:%M").time()
                        # Store in session state for end time calculation
                        st.session_state['current_start_time'] = start_time_str
                    except:
                        start_time = datetime.strptime("08:00", "%H:%M").time()
                        st.session_state['current_start_time'] = "08:00"
                else:
                    start_time = datetime.strptime("08:00", "%H:%M").time()
                    st.session_state['current_start_time'] = "08:00"
            elif selected_job_type == "pet_sitting":
                # Pet sitting start time
                current_time_str = f"{datetime.now().hour:02d}:00"
                start_time_str = enhanced_time_input("Start Time:", current_time_str, key="petsit_start")
                if start_time_str:
                    try:
                        start_time = datetime.strptime(start_time_str, "%H:%M").time()
                        # Store in session state for end time calculation
                        st.session_state['current_start_time'] = start_time_str
                    except:
                        start_time = datetime.now().time()
                        st.session_state['current_start_time'] = current_time_str
                else:
                    start_time = datetime.now().time()
                    st.session_state['current_start_time'] = current_time_str
            elif selected_job_type == "management":
                # Management tasks - use duration instead of start/end time
                duration_hours = st.number_input("Duration (hours):", min_value=0.25, max_value=24.0, value=1.0, step=0.25, key="management_duration")
                # Set arbitrary start time (will be used for date only)
                start_time = datetime.strptime("09:00", "%H:%M").time()
                # Calculate end time based on duration
                start_datetime = datetime.combine(entry_date, start_time)
                end_datetime = start_datetime + timedelta(hours=duration_hours)
                end_time = end_datetime.time()
            else:
                # Default to current hour
                current_time_str = f"{datetime.now().hour:02d}:00"
                start_time_str = enhanced_time_input("Start Time:", current_time_str, key="default_start")
                if start_time_str:
                    try:
                        start_time = datetime.strptime(start_time_str, "%H:%M").time()
                        # Store in session state for end time calculation
                        st.session_state['current_start_time'] = start_time_str
                    except:
                        start_time = datetime.now().time()
                        st.session_state['current_start_time'] = current_time_str
                else:
                    start_time = datetime.now().time()
                    st.session_state['current_start_time'] = current_time_str
    else:
        # For dog_at_home and cat_at_home, use default times since it's day-based
        start_time = datetime.strptime("09:00", "%H:%M").time()  # Default start time
        end_time = datetime.strptime("09:00", "%H:%M").time()   # Default end time (same since it's day-based)
    
    if selected_job_type not in ["dog_at_home", "cat_at_home"]:
        with col2:
            if selected_job_type == "walk":
                end_time_str = enhanced_time_input("End Time (optional for 1-hour default):", "", key="walk_end", allow_empty=True)
                if end_time_str:
                    try:
                        end_time = datetime.strptime(end_time_str, "%H:%M").time()
                    except:
                        end_time = None
                else:
                    end_time = None
            elif selected_job_type in ["cat_visit", "expense"]:
                end_time = None
            elif selected_job_type == "transport_km":
                # Transport KM has optional end time
                end_time_str = enhanced_time_input("End Time (optional):", "", key="transport_end", allow_empty=True)
                if end_time_str:
                    try:
                        end_time = datetime.strptime(end_time_str, "%H:%M").time()
                    except:
                        end_time = None
                else:
                    end_time = None
            elif selected_job_type == "overnight_hotel":
                # Overnight Hotel is automatically 12 hours from start time
                if 'start_time_str' in locals():
                    start_hour = int(start_time_str.split(':')[0])
                    end_hour = (start_hour + 12) % 24  # 12 hours later, handling day rollover
                    end_time_str = f"{end_hour:02d}:00"
                    st.selectbox("End Time (12 hours fixed):", [end_time_str], index=0, disabled=True)
                    end_time = datetime.strptime(end_time_str, "%H:%M").time()
                else:
                    end_time = datetime.strptime("07:00", "%H:%M").time()  # Default fallback
            elif selected_job_type in ["hotel", "hotel_daycare"]:
                # Hotel/Day Care end time - default to 16:00
                # Use stored start time for calculation or default to 16:00
                stored_start_time = st.session_state.get('current_start_time', '08:00')
                default_end = "16:00"  # Standard 8-hour day care shift
                
                end_time_str = enhanced_time_input("End Time:", default_end, key="hotel_daycare_end")
                if end_time_str:
                    try:
                        end_time = datetime.strptime(end_time_str, "%H:%M").time()
                    except:
                        end_time = datetime.strptime("16:00", "%H:%M").time()
                else:
                    end_time = datetime.strptime("16:00", "%H:%M").time()
            elif selected_job_type == "pet_sitting":
                # Pet sitting end time
                # Use stored start time for calculation
                stored_start_time = st.session_state.get('current_start_time', '17:00')
                if stored_start_time:
                    try:
                        start_hour = int(stored_start_time.split(':')[0])
                        start_minute = int(stored_start_time.split(':')[1])
                        end_hour = start_hour + 1
                        if end_hour >= 24:
                            end_hour = 23
                            start_minute = 45 if start_minute == 45 else start_minute
                        suggested_end = f"{end_hour:02d}:{start_minute:02d}"
                    except:
                        suggested_end = "17:00"
                else:
                    suggested_end = "17:00"
                
                end_time_str = enhanced_time_input("End Time:", suggested_end, key="petsit_end")
                if end_time_str:
                    try:
                        end_time = datetime.strptime(end_time_str, "%H:%M").time()
                    except:
                        end_time = datetime.strptime("17:00", "%H:%M").time()
                else:
                    end_time = datetime.strptime("17:00", "%H:%M").time()
            elif selected_job_type == "management":
                # Management tasks - end time already calculated in start time section
                # Display the calculated duration for confirmation
                calculated_duration = duration_hours
                st.info(f"⏱️ Duration: {calculated_duration} hour{'s' if calculated_duration != 1 else ''}")
            else:
                # Default to 1 hour after start time
                # Use stored start time for calculation
                stored_start_time = st.session_state.get('current_start_time', '17:00')
                if stored_start_time:
                    try:
                        start_hour = int(stored_start_time.split(':')[0])
                        start_minute = int(stored_start_time.split(':')[1])
                        end_hour = start_hour + 1
                        if end_hour >= 24:
                            end_hour = 23
                            start_minute = 45 if start_minute == 45 else start_minute
                        suggested_end = f"{end_hour:02d}:{start_minute:02d}"
                    except:
                        suggested_end = "17:00"
                else:
                    suggested_end = "17:00"
                
                end_time_str = enhanced_time_input("End Time:", suggested_end, key="default_end")
                if end_time_str:
                    try:
                        end_time = datetime.strptime(end_time_str, "%H:%M").time()
                    except:
                        end_time = datetime.strptime("17:00", "%H:%M").time()
                else:
                    end_time = datetime.strptime("17:00", "%H:%M").time()
    
    # Quantity/Amount field (for specific job types)
    if selected_job_type == "expense":
        quantity = st.number_input("Amount (PLN):", min_value=0.0, value=0.0, step=0.001)
    elif selected_job_type == "cat_visit":
        quantity = st.number_input("Number of visits:", min_value=1, value=1, step=1)
    elif selected_job_type == "transport_km":
        quantity = st.number_input("Kilometers driven:", min_value=0.0, value=0.0, step=0.1)
    elif selected_job_type == "transport":
        quantity = st.number_input("Kilometers driven:", min_value=0.0, value=0.0, step=0.1, help="This will create both time-based and distance-based entries")
    else:
        quantity = 1
    
    # Pet names field (conditional)
    pet_names = []
    if selected_job_type in JOBS_REQUIRING_PETS:
        pet_names_input = st.text_input("Pet names (comma-separated):", placeholder="Max, Bella, Luna", key="pet_names_input")
        if pet_names_input.strip():
            pet_names = [name.strip() for name in pet_names_input.split(",") if name.strip()]
    
    # Description field
    if selected_job_type == "management":
        description = st.text_area("Description (required for management tasks):", placeholder="Describe the management work performed...", key="description_input")
        # Note: Validation warning will only show when trying to submit
    else:
        description = st.text_area("Description (optional):", placeholder="Additional details about the work...", key="description_input")
    
    # Initialize saving state if not exists
    if 'is_saving' not in st.session_state:
        st.session_state.is_saving = False
    
    # Safety mechanism: Auto-reset saving state if stuck for too long
    if 'saving_timestamp' not in st.session_state:
        st.session_state.saving_timestamp = None
    
    # Check if saving state has been stuck for more than 30 seconds
    if st.session_state.is_saving and st.session_state.saving_timestamp:
        import time
        current_time = time.time()
        if current_time - st.session_state.saving_timestamp > 30:  # 30 seconds timeout
            st.session_state.is_saving = False
            st.session_state.saving_timestamp = None
            st.warning("⚠️ Save operation timed out and was automatically reset. Please try saving again.")
    
    # Show information if user is in saving state
    if st.session_state.is_saving:
        st.info("💾 **Save in progress...** If this persists, use the Reset button below.")
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Reset", help="Reset if stuck in saving state"):
                st.session_state.is_saving = False
                st.session_state.saving_timestamp = None
                st.success("✅ Saving state reset successfully!")
                st.rerun()
    
    
    # Display success message right before submit button (mobile-friendly)
    if st.session_state.get('show_success', False):
        # Create a prominent success container
        with st.container():
            st.markdown("""
            <div style="
                background-color: #d4edda; 
                border: 2px solid #c3e6cb; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                position: sticky;
                top: 10px;
                z-index: 1000;
            ">
                <h3 style="color: #155724; margin: 0; font-size: 1.2em;">✅ Entry Saved Successfully!</h3>
                <p style="color: #155724; margin: 10px 0 0 0; font-size: 0.9em;">Your timesheet entry has been recorded.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show detailed message
            st.success(st.session_state.get('success_message', ''))
            
            # Auto-clear after showing (with manual option)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("✅ Got it! Clear message", type="secondary", use_container_width=True):
                    st.session_state.show_success = False
                    st.session_state.success_message = ""
                    st.rerun()
            
            # Auto-clear after 10 seconds
            if 'success_timestamp' not in st.session_state:
                import time
                st.session_state.success_timestamp = time.time()
            
            # Check if 10 seconds have passed
            import time
            if time.time() - st.session_state.get('success_timestamp', 0) > 10:
                st.session_state.show_success = False
                st.session_state.success_message = ""
                if 'success_timestamp' in st.session_state:
                    del st.session_state.success_timestamp
                st.rerun()
                
            # Add JavaScript to scroll to success message on mobile
            st.markdown("""
            <script>
            // Scroll to the success message for better mobile visibility
            setTimeout(function() {
                const successDiv = document.querySelector('[data-testid="stMarkdownContainer"]');
                if (successDiv && window.innerWidth <= 768) {
                    successDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
            </script>
            """, unsafe_allow_html=True)
    
    # Submit button with state management
    save_button_disabled = st.session_state.get('is_saving', False)
    button_text = "⏳ Saving... Please wait" if save_button_disabled else "💾 Save Entry"
    button_type = "secondary" if save_button_disabled else "primary"
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        save_clicked = st.button(button_text, type=button_type, disabled=save_button_disabled, use_container_width=True)
    
    with col2:
        # Manual reset button for stuck states
        if save_button_disabled:
            if st.button("🔄 Reset", help="Reset if save gets stuck"):
                st.session_state.is_saving = False
                st.session_state.saving_timestamp = None
                st.rerun()
    
    # Show immediate feedback when saving starts
    if save_button_disabled:
        st.info("⏳ **Processing your entry...** Please don't refresh the page or submit again.", icon="ℹ️")
    
    if save_clicked:
        # Set saving state to prevent double-clicks
        import time
        st.session_state.is_saving = True
        st.session_state.saving_timestamp = time.time()  # Record start time
        
        # Show loading indicator immediately
        loading_placeholder = st.empty()
        loading_placeholder.info("💾 Saving entry... Please wait.")
        
        # Clear any previous success messages but keep processing notifications
        st.session_state.show_success = False
        st.session_state.success_message = ""
        conversion_message = ""  # Store conversion info for final message
        
        # Validation for management tasks
        if selected_job_type == "management" and not description.strip():
            st.session_state.is_saving = False  # Reset saving state
            st.session_state.saving_timestamp = None  # Clear timestamp
            loading_placeholder.error("❌ Description is required for management tasks")
            st.stop()
        
        try:
            # Build entry data
            if selected_job_type in ["pet_sitting", "dog_at_home", "cat_at_home"]:
                # Multi-day services use start_date and end_date
                start_datetime = datetime.combine(start_date, start_time)
                end_datetime = datetime.combine(end_date, end_time)
            else:
                # Other job types use entry_date
                start_datetime = datetime.combine(entry_date, start_time)
                
                if end_time and selected_job_type not in ["cat_visit", "expense", "transport_km"]:
                    end_datetime = datetime.combine(entry_date, end_time)
                    # Handle overnight shifts that cross midnight
                    if end_time < start_time and selected_job_type in ["overnight_hotel", "night_shift"]:
                        end_datetime = datetime.combine(entry_date + timedelta(days=1), end_time)
                elif selected_job_type == "walk" and not end_time:
                    # Default 1 hour for walks
                    end_datetime = start_datetime + timedelta(hours=1)
                else:
                    end_datetime = start_datetime
            
            entry_data = {
                'employee_name': selected_employee,
                'job_type': selected_job_type,
                'start_time': start_datetime.isoformat(),
                'end_time': end_datetime.isoformat(),
                'quantity': quantity,
                'pet_names': pet_names,
                'description': description.strip() if description else '',
                'confidence': 1.0  # High confidence for form entries
            }
            
            # Validate requirements
            if selected_job_type in JOBS_REQUIRING_PETS and not pet_names:
                st.session_state.is_saving = False  # Reset saving state
                loading_placeholder.error(f"❌ Pet names are required for {JOB_TYPES_DISPLAY.get(selected_job_type, selected_job_type)}")
                st.stop()
            
            # Validate time order for same-day jobs (not overnight shifts)
            if selected_job_type in ["hotel", "walk"] and end_time:
                if end_time <= start_time:
                    st.session_state.is_saving = False  # Reset saving state
                    loading_placeholder.error("❌ End time must be later than start time for same-day work. For overnight work, use 'Overnight Hotel' or 'Night Shift' job types.")
                    st.stop()
                
                # Check for reasonable duration (max 12 hours for regular shifts)
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                if duration_hours > 12:
                    st.session_state.is_saving = False  # Reset saving state
                    loading_placeholder.error(f"❌ Duration of {duration_hours:.1f} hours is too long for regular work. For overnight work, use 'Overnight Hotel' or 'Night Shift' job types (max 12 hours for regular shifts).")
                    st.stop()
                
                if duration_hours <= 0:
                    st.session_state.is_saving = False  # Reset saving state
                    loading_placeholder.error("❌ Work duration must be positive. Please check your start and end times.")
                    st.stop()
            
            # Validate duration for multi-day services
            if selected_job_type in ["pet_sitting", "dog_at_home", "cat_at_home"]:
                duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                max_duration = 7 * 24  # 7 days max
                if duration_hours > max_duration:
                    job_display = JOB_TYPES_DISPLAY.get(selected_job_type, selected_job_type)
                    st.session_state.is_saving = False  # Reset saving state
                    loading_placeholder.error(f"❌ {job_display} duration of {duration_hours:.1f} hours ({duration_hours/24:.1f} days) is too long. Maximum is {max_duration/24} days.")
                    st.stop()
                
                if duration_hours <= 0:
                    st.session_state.is_saving = False  # Reset saving state
                    loading_placeholder.error("❌ Work duration must be positive. Please check your dates and times.")
                    st.stop()
            
            # Update entry_data with corrected end_datetime
            entry_data['end_time'] = end_datetime.isoformat()
            
            if selected_job_type == "expense":
                if quantity <= 0:
                    st.session_state.is_saving = False  # Reset saving state
                    st.session_state.saving_timestamp = None  # Clear timestamp
                    loading_placeholder.error("❌ Please enter a valid expense amount")
                    st.stop()
                if not description.strip():
                    st.session_state.is_saving = False  # Reset saving state
                    st.session_state.saving_timestamp = None  # Clear timestamp
                    loading_placeholder.error("❌ Description is required for expenses")
                    st.stop()
            
            if selected_job_type == "transport_km":
                if quantity <= 0:
                    st.session_state.is_saving = False  # Reset saving state
                    st.session_state.saving_timestamp = None  # Clear timestamp
                    loading_placeholder.error("❌ Please enter a valid number of kilometers")
                    st.stop()
            
            # Check for pet sitting that needs segmentation
            if selected_job_type == "pet_sitting":
                segments = split_multi_day_pet_sitting(start_date, start_time, end_date, end_time)
                
                if len(segments) > 1:
                    # Multiple segments detected - save all
                    total_amount = 0
                    segment_details = []  # Store segment info for final message
                    
                    # Update loading message with progress
                    loading_placeholder.info(f"💾 Saving {len(segments)} pet sitting segments... Please wait.")
                    
                    for i, segment in enumerate(segments, 1):
                        # Update progress
                        loading_placeholder.info(f"💾 Saving segment {i} of {len(segments)}... Please wait.")
                        
                        # Create entry data for each segment
                        segment_data = entry_data.copy()
                        segment_data.update(segment)
                        
                        # Save to database with improved error handling
                        try:
                            success, duration_label, amount = save_timesheet_entry(segment_data)
                            if success:
                                # Use returned amount from save function for consistency
                                if segment['job_type'] == 'pet_sitting_hourly':
                                    segment_details.append(f"**Segment {i}:** Hourly Pet Sitting ({segment['start_time'][11:16]} - {segment['end_time'][11:16]}) = {amount:.2f} PLN ({duration_label})")
                                else:
                                    segment_details.append(f"**Segment {i}:** Overnight Pet Sitting ({segment['start_time'][:10]} to {segment['end_time'][:10]}) = {amount:.2f} PLN")
                                total_amount += amount
                            else:
                                loading_placeholder.error(f"❌ Failed to save segment {i}")
                                st.stop()
                        except Exception as e:
                            loading_placeholder.error(f"❌ Error saving segment {i}: {str(e)}")
                            st.stop()
                    
                    # Create comprehensive success message with all segment details
                    conversion_message = f"🔄 **Multi-day pet sitting detected!** Split into {len(segments)} segments:\n\n" + "\n".join(segment_details) + f"\n\n**Total Amount:** {total_amount:.2f} PLN"
                    
                    # Store success message in session state to show it persistently
                    st.session_state.success_message = f"✅ Pet sitting entry saved successfully!\n\n{conversion_message}"
                    st.session_state.show_success = True
                    import time
                    st.session_state.success_timestamp = time.time()  # Set timestamp for auto-clear
                    st.session_state.is_saving = False  # Reset saving state
                    st.session_state.saving_timestamp = None  # Clear timestamp
                    
                    # Clear loading indicator before form reset
                    loading_placeholder.empty()
                    
                    # Clear form fields after successful submission
                    if 'description_input' in st.session_state:
                        del st.session_state.description_input
                    if 'pet_names_input' in st.session_state:
                        del st.session_state.pet_names_input
                    
                    st.rerun()
                else:
                    # Single segment - check if job type was converted
                    segment = segments[0]
                    original_job_type = selected_job_type
                    new_job_type = segment['job_type']
                    
                    # Store conversion info for final message
                    if original_job_type != new_job_type:
                        if new_job_type == 'overnight_pet_sitting':
                            duration_hours = (datetime.fromisoformat(segment['end_time']) - 
                                            datetime.fromisoformat(segment['start_time'])).total_seconds() / 3600
                            conversion_message = f"🔄 **Automatic conversion:** {duration_hours:.1f}-hour pet sitting converted to overnight pet sitting (rate: 140 PLN instead of 17 PLN/hour)"
                        elif new_job_type == 'pet_sitting_hourly':
                            conversion_message = f"🔄 **Automatic conversion:** Pet sitting converted to hourly pet sitting (rate: 17 PLN/hour)"
                    
                    entry_data.update(segment)
            
            # Check for other long shifts that need splitting
            shifts = []  # Initialize shifts as empty list
            if selected_job_type != "pet_sitting":
                shifts = split_long_shifts(
                    entry_data['start_time'],
                    entry_data['end_time'],
                    entry_data['job_type']
                )
            
            if len(shifts) > 1:
                # Multiple shifts detected - save all segments
                loading_placeholder.info(f"🔄 Long shift detected! Saving {len(shifts)} segments...")
                total_amount = 0
                
                for i, shift in enumerate(shifts, 1):
                    # Update progress
                    loading_placeholder.info(f"💾 Saving shift segment {i} of {len(shifts)}... Please wait.")
                    
                    # Create entry data for each shift
                    shift_data = entry_data.copy()
                    shift_data.update(shift)
                    
                    # Save each shift with error handling
                    try:
                        success, duration_label, amount = save_timesheet_entry(shift_data)
                        if success:
                            total_amount += amount
                            st.success(f"**Segment {i}:** {shift['job_type']} ({shift['start_time'][11:16]} - {shift['end_time'][11:16]}) = {amount:.2f} PLN")
                        else:
                            loading_placeholder.error(f"❌ Failed to save shift segment {i}")
                            st.stop()
                    except Exception as e:
                        loading_placeholder.error(f"❌ Error saving shift segment {i}: {str(e)}")
                        st.stop()
                
                loading_placeholder.empty()  # Clear loading indicator
                st.session_state.is_saving = False  # Reset saving state
                st.session_state.saving_timestamp = None  # Clear timestamp
                
                # Store success message in session state for consistency
                st.session_state.success_message = f"✅ **Total Amount:** {total_amount:.2f} PLN - All segments saved! 🎉"
                st.session_state.show_success = True
                import time
                st.session_state.success_timestamp = time.time()  # Set timestamp for auto-clear
                
                # Clear form fields after successful submission
                if 'description_input' in st.session_state:
                    del st.session_state.description_input
                if 'pet_names_input' in st.session_state:
                    del st.session_state.pet_names_input
                
                st.rerun()
            
            else:
                # Special case: Transport creates two entries (time-based + distance-based)
                if selected_job_type == "transport" and quantity > 0:
                    try:
                        # Create first entry: time-based transport
                        transport_time_data = entry_data.copy()
                        transport_time_data['job_type'] = 'transport'
                        transport_time_data['quantity'] = 1  # Default quantity for time-based
                        
                        success1, duration_label1, amount1 = save_timesheet_entry(transport_time_data)
                        if not success1:
                            loading_placeholder.error("❌ Failed to save time-based transport entry")
                            st.stop()
                        
                        # Create second entry: distance-based transport
                        transport_km_data = entry_data.copy()
                        transport_km_data['job_type'] = 'transport_km'
                        transport_km_data['quantity'] = quantity  # KM quantity
                        # Keep the same times for reference, but calculation will use KM
                        
                        success2, duration_label2, amount2 = save_timesheet_entry(transport_km_data)
                        if not success2:
                            loading_placeholder.error("❌ Failed to save distance-based transport entry")
                            st.stop()
                        
                        loading_placeholder.empty()  # Clear loading indicator
                        
                        # Calculate total amount and display
                        total_combined_amount = amount1 + amount2
                        time_rate = get_employee_rate(selected_employee, 'transport', pet_names)
                        km_rate = get_employee_rate(selected_employee, 'transport_km', pet_names)
                        
                        amount_display = (f"{total_combined_amount:.2f} PLN "
                                        f"(Time: {amount1:.2f} PLN + Distance: {amount2:.2f} PLN)")
                        
                        final_message = (f"✅ Transport entries saved successfully!\n"
                                       f"🚗 Time-based: {duration_label1} = {amount1:.2f} PLN\n"
                                       f"🛣️ Distance-based: {quantity}km = {amount2:.2f} PLN\n"
                                       f"💰 Total: {total_combined_amount:.2f} PLN")
                        
                        st.session_state.success_message = final_message
                        st.session_state.show_success = True
                        import time
                        st.session_state.success_timestamp = time.time()  # Set timestamp for auto-clear
                        st.session_state.is_saving = False  # Reset saving state
                        st.session_state.saving_timestamp = None  # Clear timestamp
                        
                        # Clear form data
                        if 'description_input' in st.session_state:
                            del st.session_state.description_input
                        if 'pet_names_input' in st.session_state:
                            del st.session_state.pet_names_input
                        
                        st.rerun()
                        return  # Exit here to prevent further processing
                        
                    except Exception as e:
                        st.session_state.is_saving = False  # Reset saving state on error
                        st.session_state.saving_timestamp = None  # Clear timestamp
                        loading_placeholder.error(f"❌ Error saving transport entries: {str(e)}")
                        st.stop()
                        return  # Exit here to prevent further processing
                
                # Single shift - normal processing (for all other job types)
                else:
                    try:
                        success, duration_label, total_amount = save_timesheet_entry(entry_data)
                        if not success:
                            loading_placeholder.error("❌ Failed to save entry")
                            st.stop()
                            
                        loading_placeholder.empty()  # Clear loading indicator
                        
                        # Calculate and display amount
                        if entry_data['job_type'] == "expense":
                            amount_display = f"{quantity:.2f} PLN"
                        elif entry_data['job_type'] == "cat_visit":
                            rate = get_employee_rate(selected_employee, selected_job_type, pet_names)
                            amount_display = f"{quantity * rate:.2f} PLN"
                        elif entry_data['job_type'] == "transport_km":
                            rate = get_employee_rate(selected_employee, selected_job_type, pet_names)
                            amount_display = f"{quantity * rate:.2f} PLN"
                        elif entry_data['job_type'] in ["dog_at_home", "cat_at_home"]:
                            # Day-based services - extract dates from datetime objects
                            start_dt = datetime.fromisoformat(entry_data['start_time'])
                            end_dt = datetime.fromisoformat(entry_data['end_time'])
                            days = max(1, (end_dt.date() - start_dt.date()).days)  # Overnight counting
                            rate = get_employee_rate(selected_employee, selected_job_type, pet_names)
                            amount = days * rate
                            amount_display = f"{amount:.2f} PLN ({days} day{'s' if days != 1 else ''})"
                        elif entry_data['job_type'] == "walk":
                            if not end_time:
                                rate = get_employee_rate(selected_employee, entry_data['job_type'], pet_names)
                                amount_display = f"{total_amount:.2f} PLN"
                            else:
                                amount_display = f"{total_amount:.2f} PLN"
                        else:
                            amount_display = f"{total_amount:.2f} PLN"
                    
                        # Include conversion message in final success message if available
                        final_message = f"✅ Entry saved successfully! Amount: {amount_display}"
                        if conversion_message:
                            final_message += f"\n\n{conversion_message}"
                        
                        # Add WhatsApp message for expenses
                        if entry_data['job_type'] == "expense":
                            final_message += f"\n\n📱 **Note:** Please share the receipt photo via WhatsApp for manual attachment."
                        
                        # Store success message in session state
                        st.session_state.success_message = final_message
                        st.session_state.show_success = True
                        import time
                        st.session_state.success_timestamp = time.time()  # Set timestamp for auto-clear
                        st.session_state.is_saving = False  # Reset saving state
                        st.session_state.saving_timestamp = None  # Clear timestamp
                        
                        # Clear loading indicator before form reset
                        loading_placeholder.empty()
                        
                        # Clear form fields after successful submission
                        if 'description_input' in st.session_state:
                            del st.session_state.description_input
                        if 'pet_names_input' in st.session_state:
                            del st.session_state.pet_names_input
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.session_state.is_saving = False  # Reset saving state on error
                        st.session_state.saving_timestamp = None  # Clear timestamp
                        loading_placeholder.error(f"❌ Error saving single entry: {str(e)}")
                        st.stop()
        
        except Exception as e:
            st.session_state.is_saving = False  # Reset saving state on error
            st.session_state.saving_timestamp = None  # Clear timestamp
            if 'loading_placeholder' in locals():
                loading_placeholder.error(f"❌ Error saving entry: {str(e)}")
            else:
                st.error(f"❌ Error saving entry: {str(e)}")
    
    # Add some helpful information
    st.markdown("---")
    st.markdown("### 💡 Tips:")
    st.markdown("- **Cat Visits & Expenses:** No start/end time required")
    st.markdown("- **Transport:** Creates TWO entries automatically (time-based + distance-based). Enter start/end times and kilometers.")
    st.markdown("- **Dog Walks:** End time optional (defaults to 1 hour)")
    st.markdown("- **Hotel:** End time must be later than start time (same day work)")
    st.markdown("- **Pet Sitting:** Multi-day support with smart segmentation (≤8h: hourly, >8h: overnight rates)")
    st.markdown("- **Overnight Hotel:** Fixed 12-hour shifts starting at 19:00 or 20:00")
    st.markdown("- **Night Shift:** Use for other overnight work crossing midnight")
    st.markdown("- **Pet names:** Required for walks, hotel work, training, and pet care services")
    st.markdown("- **Max duration:** 12 hours for regular shifts, use overnight types for longer work")

# Helper function for better time input
def better_time_input(label, value=None, key=None, help_text=None):
    """
    Create a better time input with both dropdown and text input options
    Returns a time object or None if invalid
    """
    # Create time options for dropdown (24-hour format)
    time_options = ["Custom..."] + [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in [0, 15, 30, 45]]
    
    # Convert current value to string
    if value is not None:
        if isinstance(value, datetime):
            current_value = value.strftime('%H:%M')
        elif hasattr(value, 'strftime'):  # time object
            current_value = value.strftime('%H:%M')
        else:
            current_value = str(value)
    else:
        current_value = datetime.now().strftime('%H:%M')
    
    # Find index of current value in predefined options
    try:
        current_index = time_options.index(current_value) if current_value in time_options else 0
    except:
        current_index = 0
    
    # Create the selectbox
    selected_option = st.selectbox(
        label, 
        time_options, 
        index=current_index,
        key=f"{key}_select" if key else None,
        help=help_text or "Select common time or choose 'Custom...' for precise entry"
    )
    
    # If custom is selected, show text input
    if selected_option == "Custom...":
        custom_time = st.text_input(
            f"Enter custom time for {label.lower()}:",
            value=current_value,
            placeholder="HH:MM (e.g., 13:50, 09:30)",
            key=f"{key}_custom" if key else None,
            help="Enter time in 24-hour format (HH:MM)"
        )
        
        # Validate custom time input
        try:
            time_obj = datetime.strptime(custom_time, "%H:%M").time()
            return time_obj
        except:
            st.error(f"❌ Invalid time format. Please use HH:MM format (e.g., 13:50)")
            return None
    else:
        # Convert back to time object
        try:
            return datetime.strptime(selected_option, "%H:%M").time()
        except:
            return None

def enhanced_time_input(label, default_value="", key=None, allow_empty=False):
    """
    Enhanced time input with flexible formatting:
    - 24-hour format: 13:50
    - 12-hour format: 1:50 PM
    - Decimal format: 13.5 (means 13:30)
    """
    
    # Create a unique key if not provided
    if key is None:
        import hashlib
        key = f"time_{hashlib.md5(label.encode()).hexdigest()[:8]}"
    
    # Text input for direct time entry
    help_text = "Formats: 13:50 (24hr), 1:50 PM (12hr), 13.5 (decimal)"
    if allow_empty:
        help_text += " or leave empty"
    
    time_text = st.text_input(
        label,
        value=default_value,
        help=help_text,
        key=f"{key}_input",
        placeholder="e.g., 13:50 or 1:50 PM or 13.5"
    )
    
    # Validate and parse the input
    if not time_text.strip() and allow_empty:
        return ""
    
    if not time_text.strip():
        if not allow_empty:
            st.error("Please enter a time")
        return ""
    
    try:
        # Try different time formats
        time_str = time_text.strip()
        
        # Format: 13:50
        if ':' in time_str and len(time_str.split(':')) == 2:
            hour, minute = time_str.split(':')
            hour, minute = int(hour), int(minute)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
        
        # Format: 13.5 (13:30)
        elif '.' in time_str:
            hour_decimal = float(time_str)
            hour = int(hour_decimal)
            minute = int((hour_decimal - hour) * 60)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
        
        # Format: 1:50 PM / 1:50 AM
        elif 'PM' in time_str.upper() or 'AM' in time_str.upper():
            time_part = time_str.upper().replace('PM', '').replace('AM', '').strip()
            is_pm = 'PM' in time_str.upper()
            
            if ':' in time_part:
                hour, minute = time_part.split(':')
                hour, minute = int(hour), int(minute)
                
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return f"{hour:02d}:{minute:02d}"
        
        # If we get here, format is invalid
        st.error(f"Invalid time format: {time_str}. Use formats like: 13:50, 1:50 PM, 13.5")
        return ""
        
    except ValueError:
        st.error(f"Invalid time format: {time_text}. Use formats like: 13:50, 1:50 PM, 13.5")
        return ""

def render_admin_dashboard():
    """Admin dashboard with comprehensive analytics and reports"""
    EnhancedAuthManager.require_admin()  # Ensure admin access
    st.title("💳 Admin Dashboard - Payment Processing")
    
    # Helper function to get date range data with payment status
    def get_date_range_payment_data(start_date_str, end_date_str):
        """Get timesheet data for a specific date range with payment status"""
        conn = sqlite3.connect(DB_NAME)
        query = '''
            SELECT id, employee_name, job_type, start_time, end_time, 
                   duration_hours, rate_per_hour, total_amount, description, 
                   pet_names, date_created, COALESCE(payment_status, 'pending') as status, file_path
            FROM timesheet 
            WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?
            ORDER BY employee_name, start_time
        '''
        df = pd.read_sql_query(query, conn, params=[start_date_str, end_date_str])
        conn.close()
        return df
    
    # Helper function to update payment status for date range
    def mark_date_range_as_paid(employee_name, start_date_str, end_date_str):
        """Mark all entries for an employee in a specific date range as paid"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE timesheet 
            SET payment_status = 'paid' 
            WHERE employee_name = ? 
            AND DATE(start_time) >= ? 
            AND DATE(start_time) <= ?
            AND COALESCE(payment_status, 'pending') = 'pending'
        ''', [employee_name, start_date_str, end_date_str])
        updated_rows = cursor.rowcount
        conn.commit()
        conn.close()
        return updated_rows
    
    # Helper function to get Friday-to-Thursday week range (for quick presets)
    def get_friday_week_range(target_date):
        """Get the Friday-to-Thursday week containing the target date"""
        days_from_friday = (target_date.weekday() + 3) % 7  # 0=Friday, 1=Saturday, ..., 6=Thursday
        week_start = target_date - timedelta(days=days_from_friday)  # Friday
        week_end = week_start + timedelta(days=6)  # Thursday
        return week_start, week_end
    
    # Date Range Selection
    st.subheader("📅 Date Range Selection")
    
    # Get current date and default ranges
    today = datetime.now().date()
    current_week_start, current_week_end = get_friday_week_range(today)
    
    # Quick preset buttons
    st.write("**Quick Presets:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📍 Current Week (Fri-Thu)", help="Current Friday to Thursday week"):
            st.session_state.start_date = current_week_start
            st.session_state.end_date = current_week_end
    
    with col2:
        last_week_start = current_week_start - timedelta(days=7)
        last_week_end = current_week_end - timedelta(days=7)
        if st.button("⬅️ Last Week", help="Previous Friday to Thursday week"):
            st.session_state.start_date = last_week_start
            st.session_state.end_date = last_week_end
    
    with col3:
        if st.button("📅 Current Month", help="From 1st to last day of current month"):
            month_start = today.replace(day=1)
            next_month = month_start.replace(month=month_start.month % 12 + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
            month_end = next_month - timedelta(days=1)
            st.session_state.start_date = month_start
            st.session_state.end_date = month_end
    
    with col4:
        if st.button("⬅️ Last Month", help="Previous month"):
            if today.month == 1:
                last_month_start = today.replace(year=today.year - 1, month=12, day=1)
            else:
                last_month_start = today.replace(month=today.month - 1, day=1)
            
            # Get last day of previous month
            this_month_start = today.replace(day=1)
            last_month_end = this_month_start - timedelta(days=1)
            
            st.session_state.start_date = last_month_start
            st.session_state.end_date = last_month_end
    
    with col5:
        if st.button("📊 Last 30 Days", help="Past 30 days"):
            st.session_state.start_date = today - timedelta(days=30)
            st.session_state.end_date = today
    
    # Manual date range selection
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date:", 
            value=st.session_state.get('start_date', current_week_start),
            help="Select the start date for the report period"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date:", 
            value=st.session_state.get('end_date', current_week_end),
            help="Select the end date for the report period"
        )
    
    # Validate date range
    if start_date > end_date:
        st.error("❌ Start date must be before or equal to end date!")
        st.stop()
    
    # Calculate date range details
    date_range_days = (end_date - start_date).days + 1
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    # Display selected range info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Selected Range:** {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    with col2:
        st.info(f"**Duration:** {date_range_days} day{'s' if date_range_days != 1 else ''}")
    with col3:
        if start_date == current_week_start and end_date == current_week_end:
            st.success("📍 Current Week")
        elif start_date >= current_week_start:
            st.warning("⚠️ Includes Future Dates")
        else:
            st.info("📊 Historical Data")
    
    # Get data for selected range
    range_data = get_date_range_payment_data(start_date_str, end_date_str)
    
    if not range_data.empty:
        # Date Range Summary
        st.subheader("📊 Date Range Summary")
        
        # Calculate summary metrics
        total_entries = len(range_data)
        total_amount = range_data['total_amount'].sum()
        pending_amount = range_data[range_data['status'] == 'pending']['total_amount'].sum()
        paid_amount = range_data[range_data['status'] == 'paid']['total_amount'].sum()
        active_employees = range_data['employee_name'].nunique()
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Entries", total_entries)
        
        with col2:
            st.metric("Total Amount", f"{total_amount:.2f} PLN")
        
        with col3:
            st.metric("Pending", f"{pending_amount:.2f} PLN", delta=f"{len(range_data[range_data['status'] == 'pending'])} entries")
        
        with col4:
            st.metric("Paid", f"{paid_amount:.2f} PLN", delta=f"{len(range_data[range_data['status'] == 'paid'])} entries")
        
        with col5:
            st.metric("Employees", active_employees)
        
        # Employee Selection and Details
        st.markdown("---")
        st.subheader("👥 Employee Payment Processing")
        
        # Employee selector
        employees_in_range = sorted(range_data['employee_name'].unique())
        
        st.markdown("---")
        st.markdown("### 👤 Individual Employee Details (Date Range)")
        
        selected_employee = st.selectbox("Select Employee:", employees_in_range, key="payment_employee")
        
        if selected_employee:
            # Filter data for selected employee
            employee_data = range_data[range_data['employee_name'] == selected_employee].copy()
            
            # Employee summary
            emp_total_amount = employee_data['total_amount'].sum()
            emp_pending_amount = employee_data[employee_data['status'] == 'pending']['total_amount'].sum()
            emp_paid_amount = employee_data[employee_data['status'] == 'paid']['total_amount'].sum()
            emp_pending_entries = len(employee_data[employee_data['status'] == 'pending'])
            emp_paid_entries = len(employee_data[employee_data['status'] == 'paid'])
            
            # Employee summary display
            st.subheader(f"📋 {selected_employee} - Period Summary")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Amount", f"{emp_total_amount:.2f} PLN")
            with col2:
                st.metric("Pending", f"{emp_pending_amount:.2f} PLN", delta=f"{emp_pending_entries} entries")
            with col3:
                st.metric("Paid", f"{emp_paid_amount:.2f} PLN", delta=f"{emp_paid_entries} entries")
            
            # Job type display mapping
            job_type_columns = {
                'overnight_pet_sitting': 'Overnight Pet Sitting',
                'pet_sitting': 'Pet Sitting',
                'pet_sitting_hourly': 'Pet Sitting (Hourly)',
                'overnight_hotel': 'Hotel Overnight',
                'dog_at_home': 'Dog at Home',
                'cat_at_home': 'Cat at Home',
                'cat_visit': 'Cat Visit',
                'expense': 'Expense',
                'holiday_overnight_pet_sitting': 'Holiday Overnight',
                'holiday_hourly_rate': 'Holiday Hourly',
                'management': 'Management',
                'transport': 'Transport',
                'transport_km': 'Transport KM'
            }
            
            # Admin Edit/Delete Actions
            st.markdown("---")
            st.subheader("🔧 Admin Actions - Edit/Delete Entries")
            
            # Display success message if available
            if st.session_state.get('admin_success_message'):
                st.success(st.session_state.admin_success_message)
                # Clear the message after displaying
                del st.session_state.admin_success_message
            
            # Entry selection for editing/deleting
            if len(employee_data) > 0:
                # Create a selectable table for admin actions
                st.write("**Select an entry from the table below:**")
                
                # Create a simplified table for selection with key info
                selection_data = []
                for idx, row in employee_data.iterrows():
                    # Safe datetime parsing
                    try:
                        start_dt = pd.to_datetime(row['start_time'], errors='coerce')
                        end_dt = pd.to_datetime(row['end_time'], errors='coerce')
                        
                        date_str = start_dt.strftime('%d-%b-%y') if pd.notna(start_dt) else 'N/A'
                        start_time = start_dt.strftime('%H:%M') if pd.notna(start_dt) else ''
                        end_time = end_dt.strftime('%H:%M') if pd.notna(end_dt) else ''
                    except:
                        date_str = 'N/A'
                        start_time = ''
                        end_time = ''
                    
                    # Format duration based on job type
                    if row['job_type'] in ['dog_at_home', 'cat_at_home']:
                        duration_display = f"{int(row['duration_hours'])} day(s)"
                    elif row['job_type'] == 'cat_visit':
                        duration_display = f"{int(row['duration_hours'])} visit(s)"
                    elif row['job_type'] == 'transport_km':
                        duration_display = f"{row['duration_hours']:.1f} KM"
                    elif row['job_type'] == 'expense':
                        duration_display = f"{row['duration_hours']:.2f} PLN"
                    else:
                        duration_display = f"{row['duration_hours']:.1f} hrs"
                    
                    # Parse pet names
                    pet_names = ""
                    try:
                        if not pd.isna(row['pet_names']) and row['pet_names']:
                            pet_list = json.loads(row['pet_names'])
                            if isinstance(pet_list, list) and len(pet_list) > 0:
                                pet_names = ', '.join(pet_list)
                    except:
                        pet_names = str(row['pet_names']) if not pd.isna(row['pet_names']) else ""
                    
                    # Truncate pet names for display
                    pet_names_display = pet_names[:25] + "..." if len(pet_names) > 25 else pet_names
                    
                    selection_data.append({
                        'Select': False,
                        'Date': date_str,
                        'Job Type': job_type_columns.get(row['job_type'], row['job_type']),
                        'Start': start_time,
                        'End': end_time,
                        'Duration/Amount': duration_display,
                        'Total (PLN)': f"{row['total_amount']:.2f}",
                        'Pet Names': pet_names_display,
                        'Status': '⏳ Pending' if row['status'] == 'pending' else '✅ Paid',
                        'Description': row.get('description', '')[:30] + '...' if row.get('description', '') and len(row.get('description', '')) > 30 else row.get('description', ''),
                        '_id': row['id'],  # Hidden field for reference
                        '_row_data': row.to_dict()  # Store full row data
                    })
                
                # Use st.data_editor for interactive selection
                edited_data = st.data_editor(
                    selection_data,
                    column_config={
                        "Select": st.column_config.CheckboxColumn(
                            "Select",
                            help="Select entry to edit/delete",
                            default=False,
                        ),
                        "_id": None,  # Hide this column
                        "_row_data": None,  # Hide this column
                    },
                    disabled=["Date", "Job Type", "Start", "End", "Duration/Amount", "Total (PLN)", "Pet Names", "Status", "Description"],
                    hide_index=True,
                    use_container_width=True,
                    key="admin_entry_selection"
                )
                
                # Find selected entries
                selected_entries = [row for row in edited_data if row['Select']]
                
                if len(selected_entries) == 0:
                    st.info("💡 Select entries from the table above to edit (1 entry) or delete (1+ entries).")
                elif len(selected_entries) == 1:
                    selected_entry = selected_entries[0]
                    entry_id = selected_entry['_id']
                    # Get fresh data from database for selected ID
                    original_row = employee_data[employee_data['id'] == entry_id].iloc[0]
                    selected_entry_data = original_row.to_dict()
                    
                    # Show action buttons for single selection
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Selected:** {selected_entry['Date']} - {selected_entry['Job Type']} - {selected_entry['Total (PLN)']} PLN")
                    
                    with col2:
                        if st.button("✏️ Edit Entry", key="edit_entry_btn", use_container_width=True):
                            st.session_state.admin_edit_mode = True
                            st.session_state.admin_edit_entry_id = entry_id
                            st.session_state.admin_edit_data = selected_entry_data
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete Entry", key="delete_entry_btn", type="secondary", use_container_width=True):
                            st.session_state.admin_delete_mode = True
                            st.session_state.admin_delete_entry_ids = [entry_id]
                            st.session_state.admin_delete_data_list = [selected_entry_data]
                            st.rerun()
                else:
                    # Multiple entries selected - only allow delete operation
                    selected_ids = [entry['_id'] for entry in selected_entries]
                    # Get fresh data from database for selected IDs
                    selected_data_list = []
                    for entry_id in selected_ids:
                        # Find the original row data from employee_data
                        original_row = employee_data[employee_data['id'] == entry_id].iloc[0]
                        selected_data_list.append(original_row.to_dict())
                    
                    total_amount = sum(float(entry['Total (PLN)'].replace(' PLN', '')) for entry in selected_entries)
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Selected {len(selected_entries)} entries** - Total: {total_amount:.2f} PLN")
                        st.write("📝 **Edit:** Select only 1 entry to edit")
                        
                        # Show summary of selected entries
                        entry_summary = []
                        for entry in selected_entries:
                            entry_summary.append(f"• {entry['Date']} - {entry['Job Type']} - {entry['Total (PLN)']} PLN")
                        st.write("**Selected entries:**")
                        for summary in entry_summary[:5]:  # Show first 5
                            st.write(summary)
                        if len(entry_summary) > 5:
                            st.write(f"... and {len(entry_summary) - 5} more entries")
                    
                    with col2:
                        if st.button("🗑️ Delete All Selected", key="delete_multiple_btn", type="secondary", use_container_width=True):
                            st.session_state.admin_delete_mode = True
                            st.session_state.admin_delete_entry_ids = selected_ids
                            st.session_state.admin_delete_data_list = selected_data_list
                            st.rerun()
                
                # Edit Entry Modal
                if st.session_state.get('admin_edit_mode', False):
                    st.markdown("---")
                    st.subheader("✏️ Edit Entry")
                    
                    edit_data = st.session_state.admin_edit_data
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Parse the current start_time
                        current_start = pd.to_datetime(edit_data['start_time'], format='mixed', errors='coerce')
                        edit_date = st.date_input("Date:", value=current_start.date(), key="edit_date")
                        
                        # Job type (read-only for now to avoid complex validation)
                        st.text_input("Job Type:", value=edit_data['job_type'], disabled=True, key="edit_job_type")
                        
                        # Start time - using better time input
                        edit_start_time = better_time_input("Start Time:", value=current_start.time(), key="edit_start_time")
                        
                        # End time (if available) - using better time input
                        if pd.notna(edit_data['end_time']) and edit_data['end_time'] != '':
                            current_end = pd.to_datetime(edit_data['end_time'], format='mixed', errors='coerce')
                            edit_end_time = better_time_input("End Time:", value=current_end.time(), key="edit_end_time")
                        else:
                            # Optional end time input
                            st.write("**End Time (optional):**")
                            end_time_options = ["None"] + [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in [0, 15, 30, 45]]
                            end_time_selection = st.selectbox("", end_time_options, index=0, key="edit_end_time_select")
                            edit_end_time = datetime.strptime(end_time_selection, "%H:%M").time() if end_time_selection != "None" else None
                    
                    with col2:
                        # Duration/Amount based on job type
                        if edit_data['job_type'] == 'expense':
                            edit_amount = st.number_input("Amount (PLN):", value=float(edit_data['total_amount']), min_value=0.0, step=0.01, key="edit_amount")
                        elif edit_data['job_type'] == 'cat_visit':
                            edit_visits = st.number_input("Number of visits:", value=int(edit_data['duration_hours']), min_value=1, step=1, key="edit_visits")
                        elif edit_data['job_type'] == 'transport_km':
                            edit_km = st.number_input("Kilometers:", value=float(edit_data['duration_hours']), min_value=0.0, step=0.1, key="edit_km")
                        else:
                            edit_duration = st.number_input("Duration (hours):", value=float(edit_data['duration_hours']), min_value=0.0, step=0.1, key="edit_duration")
                        
                        # Manual total amount override option
                        override_total = st.checkbox("🎯 Override Total Amount", value=False, key="edit_override_total",
                                                   help="Check this to manually set the total amount instead of auto-calculation")
                        
                        if override_total:
                            edit_manual_total = st.number_input("Manual Total (PLN):", 
                                                              value=float(edit_data['total_amount']), 
                                                              min_value=0.0, step=0.01, key="edit_manual_total",
                                                              help="Manually set the total amount (overrides rate calculation)")
                        else:
                            # Show current total amount
                            current_total = float(edit_data['total_amount'])
                            st.info(f"💰 Current Total: {current_total:.2f} PLN")
                        
                        # Description
                        edit_description = st.text_area("Description:", value=edit_data.get('description', ''), key="edit_description")
                        
                        # Pet names (if applicable)
                        if edit_data.get('pet_names'):
                            try:
                                current_pets = json.loads(edit_data['pet_names'])
                                pet_names_str = ', '.join(current_pets) if isinstance(current_pets, list) else str(current_pets)
                            except:
                                pet_names_str = edit_data['pet_names']
                        else:
                            pet_names_str = ''
                        
                        edit_pet_names = st.text_input("Pet Names (comma-separated):", value=pet_names_str, key="edit_pet_names")
                    
                    # Save/Cancel buttons
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("💾 Save Changes", key="save_edit_btn"):
                            try:
                                # Update the entry in database
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                
                                # Construct new datetime strings with proper formatting
                                
                                # Ensure edit_date is a date object
                                if isinstance(edit_date, str):
                                    edit_date = datetime.strptime(edit_date, '%Y-%m-%d').date()
                                elif isinstance(edit_date, datetime):
                                    edit_date = edit_date.date()
                                
                                # Ensure edit_start_time is a time object
                                if isinstance(edit_start_time, str):
                                    edit_start_time = datetime.strptime(edit_start_time, '%H:%M').time()
                                
                                # Construct start datetime string
                                start_dt = datetime.combine(edit_date, edit_start_time)
                                new_start_time = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                                
                                # Construct end datetime string
                                if edit_end_time:
                                    # Ensure edit_end_time is a time object
                                    if isinstance(edit_end_time, str):
                                        edit_end_time = datetime.strptime(edit_end_time, '%H:%M').time()
                                    
                                    end_dt = datetime.combine(edit_date, edit_end_time)
                                    new_end_time = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                                else:
                                    new_end_time = None
                                
                                # Calculate new duration and amount based on job type
                                if edit_data['job_type'] == 'expense':
                                    new_duration = edit_amount
                                    if override_total:
                                        new_total_amount = edit_manual_total
                                    else:
                                        new_total_amount = edit_amount
                                elif edit_data['job_type'] == 'cat_visit':
                                    new_duration = edit_visits
                                    if override_total:
                                        new_total_amount = edit_manual_total
                                    else:
                                        rate = get_employee_rate(selected_employee, edit_data['job_type'])
                                        new_total_amount = edit_visits * rate
                                elif edit_data['job_type'] == 'transport_km':
                                    new_duration = edit_km
                                    if override_total:
                                        new_total_amount = edit_manual_total
                                    else:
                                        rate = get_employee_rate(selected_employee, edit_data['job_type'])
                                        new_total_amount = edit_km * rate
                                else:
                                    new_duration = edit_duration
                                    if override_total:
                                        new_total_amount = edit_manual_total
                                    else:
                                        rate = get_employee_rate(selected_employee, edit_data['job_type'])
                                        new_total_amount = edit_duration * rate
                                
                                # Process pet names
                                if edit_pet_names.strip():
                                    pet_list = [name.strip() for name in edit_pet_names.split(',') if name.strip()]
                                    new_pet_names = json.dumps(pet_list)
                                else:
                                    new_pet_names = '[]'
                                
                                # Update the database
                                cursor.execute('''
                                    UPDATE timesheet 
                                    SET start_time = ?, end_time = ?, duration_hours = ?, 
                                        total_amount = ?, description = ?, pet_names = ?
                                    WHERE id = ?
                                ''', [new_start_time, new_end_time, new_duration, new_total_amount, 
                                      edit_description, new_pet_names, st.session_state.admin_edit_entry_id])
                                
                                conn.commit()
                                conn.close()
                                
                                # Store success message in session state
                                st.session_state.admin_success_message = "✅ Entry updated successfully!"
                                
                                # Clear edit mode
                                st.session_state.admin_edit_mode = False
                                del st.session_state.admin_edit_entry_id
                                del st.session_state.admin_edit_data
                                
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error updating entry: {str(e)}")
                    
                    with col2:
                        if st.button("❌ Cancel", key="cancel_edit_btn"):
                            st.session_state.admin_edit_mode = False
                            if 'admin_edit_entry_id' in st.session_state:
                                del st.session_state.admin_edit_entry_id
                            if 'admin_edit_data' in st.session_state:
                                del st.session_state.admin_edit_data
                            st.rerun()
                
                # Delete Entry/Entries Confirmation
                if st.session_state.get('admin_delete_mode', False):
                    st.markdown("---")
                    
                    # Handle both single and multiple entries
                    entry_ids = st.session_state.admin_delete_entry_ids
                    data_list = st.session_state.admin_delete_data_list
                    
                    if len(entry_ids) == 1:
                        # Single entry delete
                        st.subheader("🗑️ Delete Entry")
                        delete_data = data_list[0]
                        
                        st.warning(f"⚠️ **Are you sure you want to delete this entry?**")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Date:** {pd.to_datetime(delete_data['start_time'], format='mixed', errors='coerce').strftime('%d-%b-%y')}")
                            st.write(f"**Job Type:** {delete_data['job_type']}")
                            st.write(f"**Amount:** {delete_data['total_amount']:.2f} PLN")
                        
                        with col2:
                            st.write(f"**Employee:** {delete_data['employee_name']}")
                            st.write(f"**Duration:** {delete_data['duration_hours']}")
                            if delete_data.get('description'):
                                st.write(f"**Description:** {delete_data['description']}")
                    else:
                        # Multiple entries delete
                        st.subheader(f"🗑️ Delete {len(entry_ids)} Entries")
                        total_amount = sum(float(data['total_amount']) for data in data_list)
                        
                        st.warning(f"⚠️ **Are you sure you want to delete {len(entry_ids)} entries?**")
                        st.error(f"**Total amount to be deleted: {total_amount:.2f} PLN**")
                        
                        # Show summary of entries to be deleted
                        st.write("**Entries to be deleted:**")
                        for i, data in enumerate(data_list[:5]):  # Show first 5
                            date_str = pd.to_datetime(data['start_time'], format='mixed', errors='coerce').strftime('%d-%b-%y')
                            st.write(f"• {date_str} - {data['job_type']} - {data['total_amount']:.2f} PLN ({data['employee_name']})")
                        
                        if len(data_list) > 5:
                            st.write(f"... and {len(data_list) - 5} more entries")
                    
                    # Confirmation buttons
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        delete_btn_text = "🗑️ Confirm Delete" if len(entry_ids) == 1 else f"🗑️ Delete {len(entry_ids)} Entries"
                        if st.button(delete_btn_text, key="confirm_delete_btn", type="primary"):
                            try:
                                # Delete from database
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                
                                # Delete multiple entries
                                placeholders = ','.join(['?' for _ in entry_ids])
                                cursor.execute(f'DELETE FROM timesheet WHERE id IN ({placeholders})', entry_ids)
                                
                                conn.commit()
                                conn.close()
                                
                                success_msg = f"✅ Entry deleted successfully!" if len(entry_ids) == 1 else f"✅ {len(entry_ids)} entries deleted successfully!"
                                st.session_state.admin_success_message = success_msg
                                
                                # Clear delete mode
                                st.session_state.admin_delete_mode = False
                                del st.session_state.admin_delete_entry_ids
                                del st.session_state.admin_delete_data_list
                                
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error deleting entries: {str(e)}")
                    
                    with col2:
                        if st.button("❌ Cancel Delete", key="cancel_delete_btn"):
                            st.session_state.admin_delete_mode = False
                            if 'admin_delete_entry_ids' in st.session_state:
                                del st.session_state.admin_delete_entry_ids
                            if 'admin_delete_data_list' in st.session_state:
                                del st.session_state.admin_delete_data_list
                            st.rerun()
            
            # Payment Processing Actions
            st.markdown("---")
            st.subheader("💳 Payment Processing")
            
            if emp_pending_entries > 0:
                # Get pending entries for selection
                pending_entries = employee_data[employee_data['status'] == 'pending'].copy()
                
                # Payment method selection
                payment_method = st.radio(
                    "Payment Method:",
                    ["💳 Pay All Pending", "✅ Pay Selected Entries"],
                    horizontal=True,
                    help="Choose to pay all pending entries at once or select specific entries"
                )
                
                if payment_method == "💳 Pay All Pending":
                    # Bulk payment option (existing functionality)
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.info(f"**Total Pending:** {emp_pending_amount:.2f} PLN ({emp_pending_entries} entries)")
                    
                    with col2:
                        st.warning("⚠️ This will mark ALL pending entries for this employee in this date range as PAID")
                    
                    with col3:
                        if st.button(f"💳 Pay All ({emp_pending_amount:.2f} PLN)", type="primary", key="pay_all"):
                            updated_rows = mark_date_range_as_paid(selected_employee, start_date_str, end_date_str)
                            if updated_rows > 0:
                                st.success(f"✅ Marked {updated_rows} entries as paid for {selected_employee}")
                                st.balloons()
                                st.rerun()
                            else:
                                st.warning("No pending entries found to update")
                
                else:
                    # Partial payment option using same table interface as admin section
                    st.write("**Select entries to pay:**")
                    
                    # Create selection data for payment processing (similar to admin section)
                    payment_selection_data = []
                    for idx, row in pending_entries.iterrows():
                        # Parse date
                        try:
                            parsed_date = pd.to_datetime(row['start_time'], format='mixed', errors='coerce')
                            date_str = parsed_date.strftime('%d-%b-%y') if not pd.isna(parsed_date) else 'Invalid'
                        except:
                            date_str = 'Invalid'
                        
                        # Get job type display name
                        job_display = job_type_columns.get(row['job_type'], row['job_type'])
                        
                        # Format start/end times
                        try:
                            start_time = pd.to_datetime(row['start_time'], format='mixed', errors='coerce')
                            start_str = start_time.strftime('%H:%M') if not pd.isna(start_time) else ''
                        except:
                            start_str = ''
                        
                        try:
                            end_time = pd.to_datetime(row['end_time'], format='mixed', errors='coerce')
                            end_str = end_time.strftime('%H:%M') if not pd.isna(end_time) else ''
                        except:
                            end_str = ''
                        
                        # Format duration based on job type
                        if row['job_type'] in ['dog_at_home', 'cat_at_home']:
                            duration_str = f"{int(row['duration_hours'])} day{'s' if row['duration_hours'] != 1 else ''}"
                        elif row['job_type'] in ['cat_visit', 'overnight_pet_sitting']:
                            duration_str = f"{int(row['duration_hours'])} visit{'s' if row['duration_hours'] != 1 else ''}"
                        elif row['job_type'] == 'overnight_hotel':
                            # Convert hours to nights (12 hours = 1 night)
                            if row['duration_hours'] >= 12:
                                nights = int(round(row['duration_hours'] / 12))
                            else:
                                nights = int(row['duration_hours']) if row['duration_hours'] >= 1 else 1
                            nights = max(1, nights)
                            duration_str = f"{nights} night{'s' if nights != 1 else ''}"
                        elif row['job_type'] in ['transport_km']:
                            duration_str = f"{row['duration_hours']:.1f} KM"
                        elif row['job_type'] == 'expense':
                            duration_str = f"{row['duration_hours']:.2f} PLN"
                        else:
                            duration_str = f"{row['duration_hours']:.1f} hrs"
                        
                        # Parse pet names
                        pet_names = ""
                        try:
                            if not pd.isna(row['pet_names']) and row['pet_names']:
                                pet_list = json.loads(row['pet_names'])
                                if isinstance(pet_list, list) and len(pet_list) > 0:
                                    pet_names = ', '.join(pet_list)
                        except:
                            pet_names = str(row['pet_names']) if not pd.isna(row['pet_names']) else ""
                        
                        # Truncate description and pet names for display
                        description = str(row.get('description', ''))[:30] + "..." if len(str(row.get('description', ''))) > 30 else str(row.get('description', ''))
                        pet_names_display = pet_names[:25] + "..." if len(pet_names) > 25 else pet_names
                        
                        payment_selection_data.append({
                            "Select": False,
                            "Date": date_str,
                            "Job Type": job_display,
                            "Start": start_str,
                            "End": end_str,
                            "Duration/Amount": duration_str,
                            "Total (PLN)": f"{row['total_amount']:.2f}",
                            "Pet Names": pet_names_display,
                            "Description": description,
                            "_id": row['id'],
                            "_row_data": row
                        })
                    
                    # Use st.data_editor for interactive selection
                    edited_payment_data = st.data_editor(
                        payment_selection_data,
                        column_config={
                            "Select": st.column_config.CheckboxColumn(
                                "Select",
                                help="Select entries to mark as paid",
                                default=False,
                            ),
                            "_id": None,
                            "_row_data": None,
                        },
                        disabled=["Date", "Job Type", "Start", "End", "Duration/Amount", "Total (PLN)", "Pet Names", "Description"],
                        hide_index=True,
                        use_container_width=True,
                        key="payment_entry_selection"
                    )
                    
                    # Find selected entries for payment
                    selected_payment_entries = [row for row in edited_payment_data if row['Select']]
                    
                    if len(selected_payment_entries) > 0:
                        # Calculate totals for selected entries
                        selected_entry_ids = [row['_id'] for row in selected_payment_entries]
                        # Access total_amount directly from the row data or calculate from displayed value
                        selected_amount = 0.0
                        for row in selected_payment_entries:
                            # Try to get from _row_data first, fallback to parsing the displayed value
                            try:
                                if isinstance(row['_row_data'], dict):
                                    selected_amount += row['_row_data']['total_amount']
                                elif hasattr(row['_row_data'], 'total_amount'):
                                    selected_amount += row['_row_data'].total_amount
                                else:
                                    # Parse from the displayed "Total (PLN)" string
                                    amount_str = row['Total (PLN)']
                                    selected_amount += float(amount_str)
                            except:
                                # Fallback: parse from the displayed "Total (PLN)" string
                                amount_str = row['Total (PLN)']
                                selected_amount += float(amount_str)
                        
                        st.markdown("---")
                        col1, col2, col3 = st.columns([2, 2, 1])
                        
                        with col1:
                            st.info(f"**Selected:** {selected_amount:.2f} PLN ({len(selected_entry_ids)} entries)")
                        
                        with col2:
                            st.success(f"**Remaining Pending:** {emp_pending_amount - selected_amount:.2f} PLN")
                        
                        with col3:
                            if st.button(f"💳 Pay Selected ({selected_amount:.2f} PLN)", type="primary", key="pay_selected"):
                                # Helper function to mark specific entries as paid
                                def mark_selected_entries_as_paid(entry_ids):
                                    """Mark specific entries as paid by their IDs"""
                                    conn = sqlite3.connect(DB_NAME)
                                    cursor = conn.cursor()
                                    placeholders = ','.join(['?' for _ in entry_ids])
                                    cursor.execute(f'''
                                        UPDATE timesheet 
                                        SET payment_status = 'paid' 
                                        WHERE id IN ({placeholders})
                                        AND COALESCE(payment_status, 'pending') = 'pending'
                                    ''', entry_ids)
                                    updated_rows = cursor.rowcount
                                    conn.commit()
                                    conn.close()
                                    return updated_rows
                                
                                updated_rows = mark_selected_entries_as_paid(selected_entry_ids)
                                if updated_rows > 0:
                                    # Store success message in session state for persistence
                                    st.session_state.payment_success_message = f"✅ Marked {updated_rows} selected entries as paid ({selected_amount:.2f} PLN)"
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.warning("No entries were updated")
                    else:
                        st.info("👆 Select entries above to process payment")
                    
                    # Display success message if available (persistent across reruns)
                    if st.session_state.get('payment_success_message'):
                        st.success(st.session_state.payment_success_message)
                        # Clear the message after a delay or user interaction
                        if st.button("Clear Success Message", key="clear_payment_success"):
                            del st.session_state.payment_success_message
                            st.rerun()
            else:
                st.success(f"✅ All entries for {selected_employee} in this date range are already paid!")
    
    else:
        st.info(f"No timesheet entries found for the period {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    
    # Quick Stats Section
    st.markdown("---")
    st.subheader("📈 Quick Stats - Recent Weeks")
    
    # Get overall stats for the last 4 Friday-to-Thursday weeks
    stats_weeks = []
    for i in range(4):
        week_date = today - timedelta(weeks=i)
        week_start, week_end = get_friday_week_range(week_date)
        week_data = get_date_range_payment_data(week_start.isoformat(), week_end.isoformat())
        
        if not week_data.empty:
            stats_weeks.append({
                'Week': f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
                'Entries': len(week_data),
                'Total Amount': f"{week_data['total_amount'].sum():.2f} PLN",
                'Pending': f"{week_data[week_data['status'] == 'pending']['total_amount'].sum():.2f} PLN",
                'Paid': f"{week_data[week_data['status'] == 'paid']['total_amount'].sum():.2f} PLN"
            })
    
    if stats_weeks:
        stats_df = pd.DataFrame(stats_weeks)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    else:
        st.info("📭 No timesheet entries found for the selected date range.")
        st.write("💡 **Tip:** Try selecting a different date range or check if employees have submitted their timesheets.")
    
    # Global Payment Status Table (All Employees - All Time) - Not affected by date range
    st.markdown("---")
    st.markdown("### 💰 Global Payment Status (All Time)")
    st.caption("This section shows overall payment status for all employees across all dates, independent of the date range selected above.")
    
    # Get all employees and their overall payment status
    conn = sqlite3.connect(DB_NAME)
    global_query = '''
        SELECT employee_name,
               COUNT(*) as total_entries,
               SUM(CASE WHEN COALESCE(payment_status, 'pending') = 'pending' THEN 1 ELSE 0 END) as pending_count,
               SUM(CASE WHEN COALESCE(payment_status, 'pending') = 'pending' THEN total_amount ELSE 0 END) as pending_amount
        FROM timesheet 
        GROUP BY employee_name
        ORDER BY employee_name
    '''
    global_status_df = pd.read_sql_query(global_query, conn)
    conn.close()
    
    # Create simple status table
    status_table = []
    for _, row in global_status_df.iterrows():
        employee = row['employee_name']
        has_pending = row['pending_count'] > 0
        pending_amount = row['pending_amount']
        
        # Simple red/green status
        if has_pending:
            status_color = "🔴 PENDING"
            status_style = "pending"
        else:
            status_color = "🟢 PAID"
            status_style = "paid"
        
        status_table.append({
            'Employee': employee,
            'Payment Status': status_color,
            'Total Entries': row['total_entries'],
            'Pending Amount (PLN)': f"{pending_amount:.2f}" if pending_amount > 0 else "-"
        })
    
    # Display simple status table
    if status_table:
        status_df = pd.DataFrame(status_table)
        st.dataframe(status_df, use_container_width=True, hide_index=True)
        
        # Simple summary
        total_employees = len(status_table)
        paid_employees = len([emp for emp in status_table if '🟢' in emp['Payment Status']])
        pending_employees = total_employees - paid_employees
        
        # Calculate total pending amount across all employees
        total_pending_amount = global_status_df['pending_amount'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Employees", total_employees)
        with col2:
            st.metric("🟢 Fully Paid", paid_employees)
        with col3:
            st.metric("🔴 Have Pending", pending_employees)
        with col4:
            st.metric("💰 Total Pending", f"{total_pending_amount:.2f} PLN")

def render_employee_management():
    """Employee management interface for administrators"""
    st.title("👥 Employee & Job Access Management")
    
    # Create tabs for different management functions
    emp_tab1, emp_tab2, emp_tab3, emp_tab4, emp_tab5 = st.tabs(["🆕 Onboard", "🚪 Offboard", "💰 Base Rates", "🐕 Pet Rates", "📋 Overview"])
    
    with emp_tab1:
        st.write("**Add New Employee**")
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            new_emp_name = st.text_input("Employee Name:", placeholder="e.g., John Smith", key="new_emp_name")
        
        with col2:
            clone_from = st.selectbox(
                "Clone rates from existing employee:", 
                ["None"] + list_employees(),
                key="clone_from_emp"
            )
        
        with col3:
            if st.button("Add Employee", disabled=not new_emp_name):
                try:
                    if new_emp_name in list_employees():
                        st.error(f"Employee {new_emp_name} already exists!")
                    else:
                        if clone_from != "None":
                            clone_employee_rates(clone_from, new_emp_name)
                            st.success(f"✅ Added {new_emp_name} with rates cloned from {clone_from}")
                        else:
                            add_employee(new_emp_name)
                            st.success(f"✅ Added {new_emp_name} with default rates")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if new_emp_name and new_emp_name not in list_employees():
            st.info("💡 **Tip:** You can clone rates from an existing employee with similar role")
    
    with emp_tab2:
        st.write("**Remove Employee (Offboarding)**")
        st.warning("⚠️ This will permanently remove the employee and all their custom rates")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            emp_to_remove = st.selectbox("Select employee to remove:", list_employees(), key="remove_emp")
        
        with col2:
            if st.button("Remove Employee", type="secondary"):
                try:
                    success, message = remove_employee(emp_to_remove)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    with emp_tab3:
        st.write("**Update Employee Rates**")
        
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            rate_emp = st.selectbox("Employee:", list_employees(), key="rate_emp")
        
        with col2:
            if rate_emp:
                emp_jobs = get_employee_admin_job_types(rate_emp)
                rate_job = st.selectbox("Job Type:", emp_jobs, key="rate_job")
        
        with col3:
            if rate_emp and rate_job:
                current_rate = get_employee_rate(rate_emp, rate_job)
                st.write(f"Current: {current_rate} PLN")
                new_rate = st.number_input(
                    "New Rate:", 
                    min_value=0.0, 
                    step=0.5,
                    value=float(current_rate),
                    key="new_rate"
                )
        
        with col4:
            if rate_emp and rate_job and new_rate != get_employee_rate(rate_emp, rate_job):
                if st.button("Update Rate"):
                    try:
                        update_employee_base_rate(rate_emp, rate_job, new_rate)
                        st.success(f"✅ Updated {rate_emp} {rate_job} rate to {new_rate} PLN")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    with emp_tab4:
        st.write("**Pet-Specific Custom Rates Management**")
        st.info("Set custom rates for specific pets that apply to ALL employees when working with those pets.")
        
        # Add new pet custom rate
        st.markdown("##### Add/Update Pet Custom Rate")
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            pet_name = st.text_input("Pet Name:", placeholder="e.g., Lili Maya", key="pet_rate_name")
        
        with col2:
            job_types = list(JOB_TYPES.keys())
            # Remove unified types and show only actual job types
            job_types = [jt for jt in job_types if jt not in ["pet_sitting", "expense"]]
            pet_job_type = st.selectbox("Job Type:", job_types, key="pet_rate_job")
        
        with col3:
            pet_rate = st.number_input("Rate (PLN):", min_value=0.0, step=0.5, key="pet_rate_amount")
        
        with col4:
            if st.button("Add/Update", key="add_pet_rate"):
                if pet_name and pet_job_type and pet_rate > 0:
                    try:
                        set_pet_custom_rate(pet_name, pet_job_type, pet_rate)
                        st.success(f"✅ Set {pet_name} {pet_job_type} rate to {pet_rate} PLN")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Please fill all fields")
        
        # Display existing pet custom rates
        st.markdown("##### Current Pet Custom Rates")
        pet_rates = get_pet_custom_rates()
        
        if pet_rates:
            for pet, rates in pet_rates.items():
                with st.expander(f"🐕 {pet} ({len(rates)} custom rates)"):
                    for job_type, rate in rates.items():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{job_type}**: {rate} PLN/hour")
                        with col2:
                            if st.button("Remove", key=f"remove_{pet}_{job_type}"):
                                remove_pet_custom_rate(pet, job_type)
                                st.success(f"✅ Removed {pet} {job_type} custom rate")
                                st.rerun()
        else:
            st.info("No pet custom rates defined yet. Add some above!")
            
        st.markdown("---")
        st.markdown("**Rate Priority System:**")
        st.markdown("1. 🥇 **Pet-Specific Rates** (Highest Priority) - Applies to ALL employees")
        st.markdown("2. 🥈 **Employee-Specific Rates** (Medium Priority) - Individual employee rates")
        st.markdown("3. 🥉 **Standard Base Rates** (Lowest Priority) - Default rates")

    with emp_tab5:
        st.write("**Employee Overview**")
        employee_data = get_all_employee_data()
        
        for emp_name, data in employee_data.items():
            with st.expander(f"👤 {emp_name} ({len(data['rates'])} job types)"):
                st.write("**Rates:**")
                for job, rate in data['rates'].items():
                    st.write(f"• {job}: {rate} PLN")
                st.write("• expense: (exact amount, no rate)")

    # Job Type Restrictions Management Section
    st.markdown("---")
    st.subheader("🔒 Job Type Access Control")
    st.info("Control which employees can access specific job types")
    
    # Simple interface: Employee + Job Type + Add/Remove
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        selected_employee = st.selectbox(
            "Employee:",
            list_employees(),
            key="access_employee"
        )
    
    with col2:
        # Show all job types except expense and pet_sitting (virtual employee interface type)
        all_job_types = [job for job in list_job_types() if job not in ["expense", "pet_sitting"]]
        selected_job_type = st.selectbox(
            "Job Type:",
            all_job_types,
            key="access_job_type"
        )
    
    with col3:
        if selected_employee and selected_job_type:
            # Check if employee currently has access
            current_access = get_employees_allowed_for_job_type(selected_job_type)
            has_access = selected_employee in current_access
            
            if not has_access:
                if st.button("✅ Give Access", key="give_access"):
                    try:
                        # Add job type rate if employee doesn't have it
                        if selected_job_type not in EMPLOYEES[selected_employee]:
                            default_rates = {
                                "training": 100, "management": 30, "transport": 25,
                                "hotel": 25, "walk": 25, "overnight_hotel": 90,
                                "cat_visit": 30, "pet_sitting_hourly": 17,
                                "overnight_pet_sitting": 140, "dog_at_home": 75,
                                "cat_at_home": 25, "transport_km": 1.0
                            }
                            EMPLOYEES[selected_employee][selected_job_type] = default_rates.get(selected_job_type, 25)
                        
                        # Update restrictions
                        new_allowed = current_access + [selected_employee]
                        add_job_type_restriction(selected_job_type, new_allowed)
                        st.success(f"✅ {selected_employee} can now do {selected_job_type}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    with col4:
        if selected_employee and selected_job_type:
            current_access = get_employees_allowed_for_job_type(selected_job_type)
            has_access = selected_employee in current_access
            
            if has_access:
                # Check if this would remove all access (prevent this)
                remaining_access = [emp for emp in current_access if emp != selected_employee]
                if remaining_access:  # Others still have access
                    if st.button("❌ Remove Access", key="remove_access"):
                        try:
                            add_job_type_restriction(selected_job_type, remaining_access)
                            st.success(f"✅ Removed {selected_job_type} access from {selected_employee}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.button("❌ Can't Remove", disabled=True, help="At least one employee must have access")
    
    # Show current status
    if selected_employee and selected_job_type:
        current_access = get_employees_allowed_for_job_type(selected_job_type)
        has_access = selected_employee in current_access
        
        if has_access:
            st.success(f"✅ **{selected_employee}** currently **has access** to **{selected_job_type}**")
        else:
            st.warning(f"❌ **{selected_employee}** currently **does not have access** to **{selected_job_type}**")
        
        # Show who else has access
        other_access = [emp for emp in current_access if emp != selected_employee]
        if other_access:
            st.info(f"Others with {selected_job_type} access: {', '.join(other_access)}")
        elif has_access:
            st.warning(f"⚠️ {selected_employee} is the only one with {selected_job_type} access")
    
    # Quick overview table
    st.markdown("---")
    st.subheader("👁️ Access Overview")
    
    # Create a matrix showing which employees have access to which job types
    access_matrix = []
    all_job_types = [job for job in list_job_types() if job not in ["expense", "pet_sitting"]]
    for job_type in all_job_types:
        allowed_employees = get_employees_allowed_for_job_type(job_type)
        row = {"Job Type": job_type}
        for emp in list_employees():
            row[emp] = "✅" if emp in allowed_employees else "❌"
        access_matrix.append(row)
    
    import pandas as pd
    df = pd.DataFrame(access_matrix)
    st.dataframe(df, use_container_width=True)

def render_reports_page():
    """Comprehensive reports page for administrators"""
    EnhancedAuthManager.require_admin()  # Ensure admin access
    st.title("📊 Reports")
    
    # Helper function to get Friday-to-Thursday week range
    def get_friday_week_range(target_date):
        """Get the Friday-to-Thursday week containing the target date"""
        days_from_friday = (target_date.weekday() + 3) % 7  # 0=Friday, 1=Saturday, ..., 6=Thursday
        week_start = target_date - timedelta(days=days_from_friday)  # Friday
        week_end = week_start + timedelta(days=6)  # Thursday
        return week_start, week_end
    
    # Date Range Selection (reuse from Admin Dashboard)
    st.subheader("📅 Date Range Selection")
    
    # Get current date and default ranges
    today = datetime.now().date()
    current_week_start, current_week_end = get_friday_week_range(today)
    
    # Quick preset buttons
    st.write("**Quick Presets:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📍 Current Week", help="Current Friday to Thursday week", key="reports_current_week"):
            st.session_state.reports_start_date = current_week_start
            st.session_state.reports_end_date = current_week_end
    
    with col2:
        last_week_start = current_week_start - timedelta(days=7)
        last_week_end = current_week_end - timedelta(days=7)
        if st.button("⬅️ Last Week", help="Previous Friday to Thursday week", key="reports_last_week"):
            st.session_state.reports_start_date = last_week_start
            st.session_state.reports_end_date = last_week_end
    
    with col3:
        if st.button("📅 Current Month", help="From 1st to last day of current month", key="reports_current_month"):
            month_start = today.replace(day=1)
            next_month = month_start.replace(month=month_start.month % 12 + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
            month_end = next_month - timedelta(days=1)
            st.session_state.reports_start_date = month_start
            st.session_state.reports_end_date = month_end
    
    with col4:
        if st.button("⬅️ Last Month", help="Previous month", key="reports_last_month"):
            if today.month == 1:
                last_month_start = today.replace(year=today.year - 1, month=12, day=1)
            else:
                last_month_start = today.replace(month=today.month - 1, day=1)
            
            # Get last day of previous month
            this_month_start = today.replace(day=1)
            last_month_end = this_month_start - timedelta(days=1)
            
            st.session_state.reports_start_date = last_month_start
            st.session_state.reports_end_date = last_month_end
    
    with col5:
        if st.button("📊 Last 30 Days", help="Past 30 days", key="reports_last_30"):
            st.session_state.reports_start_date = today - timedelta(days=30)
            st.session_state.reports_end_date = today
    
    # Manual date range selection
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date:", 
            value=st.session_state.get('reports_start_date', current_week_start),
            help="Select the start date for the report period",
            key="reports_start_manual"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date:", 
            value=st.session_state.get('reports_end_date', current_week_end),
            help="Select the end date for the report period",
            key="reports_end_manual"
        )
    
    # Validate date range
    if start_date > end_date:
        st.error("❌ Start date must be before or equal to end date!")
        st.stop()
    
    # Calculate date range details
    date_range_days = (end_date - start_date).days + 1
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    # Display selected range info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Selected Range:** {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
    with col2:
        st.info(f"**Duration:** {date_range_days} day{'s' if date_range_days != 1 else ''}")
    with col3:
        if start_date == current_week_start and end_date == current_week_end:
            st.success("📍 Current Week")
        elif start_date >= current_week_start:
            st.warning("⚠️ Includes Future Dates")
        else:
            st.info("📊 Historical Data")
    
    # Get data for selected range
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT employee_name, job_type, start_time, end_time, 
               duration_hours, rate_per_hour, total_amount, description, 
               pet_names, date_created, COALESCE(payment_status, 'pending') as status
        FROM timesheet 
        WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?
        ORDER BY start_time
    '''
    range_data = pd.read_sql_query(query, conn, params=[start_date_str, end_date_str])
    conn.close()
    
    if not range_data.empty:
        # Overall Summary
        st.subheader("📊 Period Summary")
        
        total_entries = len(range_data)
        total_amount = range_data['total_amount'].sum()
        active_employees = range_data['employee_name'].nunique()
        unique_job_types = range_data['job_type'].nunique()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entries", total_entries)
        
        with col2:
            st.metric("Total Amount", f"{total_amount:.2f} PLN")
        
        with col3:
            st.metric("Employees", active_employees)
        
        with col4:
            st.metric("Job Categories", unique_job_types)
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏷️ Job Category Breakdown", "👥 Employee Breakdown", "👤 Employee Detail Report", "📋 Detailed View", "📈 Analytics"])
        
        with tab1:
            st.subheader("🏷️ Job Category Analysis")
            
            # Job type mapping for better display
            job_type_display = {
                'hotel': '🏨 Hotel',
                'walk': '🚶 Walk',
                'expense': '💰 Expense',
                'cat_visit': '🐱 Cat Visit',
                'pet_sitting_hourly': '🏠 Pet Sitting (Hourly)',
                'pet_sitting': '🏠 Pet Sitting',
                'overnight_pet_sitting': '🌙 Overnight Pet Sitting',
                'overnight_hotel': '🏨 Overnight Hotel',
                'dog_at_home': '🐕 Dog@Home',
                'cat_at_home': '🐱 Cat@Home',
                'training': '📚 Training',
                'management': '👔 Management',
                'transport': '🚗 Transport',
                'transport_km': '🛣️ Transport KM'
            }
            
            # Group by job type
            job_summary = range_data.groupby('job_type').agg({
                'duration_hours': 'sum',
                'total_amount': 'sum',
                'employee_name': 'count'
            }).reset_index()
            
            job_summary.columns = ['Job Type', 'Total Duration/Units', 'Total Amount', 'Entry Count']
            
            # Add display names and format
            job_summary['Job Category'] = job_summary['Job Type'].map(job_type_display)
            job_summary['Amount (PLN)'] = job_summary['Total Amount'].round(2)
            job_summary['Percentage'] = (job_summary['Total Amount'] / total_amount * 100).round(1)
            
            # Display job category breakdown
            display_job_summary = job_summary[['Job Category', 'Amount (PLN)', 'Entry Count', 'Percentage']].copy()
            display_job_summary = display_job_summary.sort_values('Amount (PLN)', ascending=False)
            
            st.dataframe(display_job_summary, use_container_width=True, hide_index=True)
            
            # Job category chart
            if len(job_summary) > 1:
                fig = px.pie(job_summary, values='Total Amount', names='Job Category', 
                           title=f"Payroll Distribution by Job Category ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})")
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("👥 Employee Breakdown")
            
            # Employee summary
            employee_summary = range_data.groupby('employee_name').agg({
                'total_amount': 'sum',
                'job_type': 'count'
            }).reset_index()
            employee_summary.columns = ['Employee', 'Total Amount', 'Entry Count']
            employee_summary = employee_summary.sort_values('Total Amount', ascending=False)
            
            st.dataframe(employee_summary, use_container_width=True, hide_index=True)
            
            # Employee amount chart
            if len(employee_summary) > 1:
                fig = px.bar(employee_summary, x='Employee', y='Total Amount',
                           title=f"Employee Earnings ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})")
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("👤 Employee Detail Report")
            
            # Employee selection
            all_employees = sorted(range_data['employee_name'].unique())
            selected_employee = st.selectbox("Select Employee:", all_employees, 
                                           help="Choose an employee to view their detailed entries for the selected date range")
            
            if selected_employee:
                try:
                    # Filter data for selected employee
                    employee_data = range_data[range_data['employee_name'] == selected_employee].copy()
                    
                    if not employee_data.empty:
                        # Employee summary metrics
                        emp_total_entries = len(employee_data)
                        emp_total_amount = employee_data['total_amount'].sum()
                        emp_job_types = employee_data['job_type'].nunique()
                        
                        # Job category wise totals with safe duration handling
                        # Ensure duration_hours column exists and is numeric
                        if 'duration_hours' not in employee_data.columns:
                            employee_data['duration_hours'] = 0.0
                        employee_data['duration_hours'] = pd.to_numeric(employee_data['duration_hours'], errors='coerce').fillna(0)
                        
                        job_category_totals = employee_data.groupby('job_type').agg({
                            'total_amount': 'sum',
                            'duration_hours': 'sum',
                            'employee_name': 'count'
                        }).reset_index()
                        job_category_totals.columns = ['Job Type', 'Amount', 'Hours/Units', 'Count']
                        
                        # Job type display mapping
                        job_type_display = {
                            'hotel': '🏨 Hotel/Daycare',
                            'walk': '🚶 Dog Walk',
                            'expense': '💰 Expense',
                            'cat_visit': '🐱 Cat Visit',
                            'pet_sitting_hourly': '🏠 Pet Sitting (Hourly)',
                            'pet_sitting': '🏠 Pet Sitting',
                            'overnight_pet_sitting': '🌙 Overnight Pet Sitting',
                            'overnight_hotel': '🌙 Overnight Hotel',
                            'dog_at_home': '🐕 Dog@Home',
                            'cat_at_home': '🐱 Cat@Home',
                            'training': '📚 Training',
                            'management': '👔 Management',
                            'transport': '🚗 Transport',
                            'transport_km': '🛣️ Transport KM'
                        }
                        
                        job_category_totals['Job Category'] = job_category_totals['Job Type'].map(job_type_display).fillna(job_category_totals['Job Type'])
                        
                        # Display summary metrics
                        st.markdown(f"### 📊 Summary for **{selected_employee}**")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Total Entries", emp_total_entries)
                        
                        with col2:
                            st.metric("Total Amount", f"{emp_total_amount:.2f} PLN")
                        
                        with col3:
                            st.metric("Job Categories", emp_job_types)
                        
                        # Job Category wise breakdown
                        st.markdown("### 🏷️ Job Category wise Totals")
                        
                        # Display job category totals in a nice format
                        job_display = job_category_totals[['Job Category', 'Amount', 'Hours/Units', 'Count']].copy()
                        job_display['Amount (PLN)'] = job_display['Amount'].round(2)
                        job_display['Hours/Units'] = job_display['Hours/Units'].round(1)
                        job_display_final = job_display[['Job Category', 'Amount (PLN)', 'Hours/Units', 'Count']].sort_values('Amount (PLN)', ascending=False)
                        
                        st.dataframe(job_display_final, use_container_width=True, hide_index=True)
                        
                        # Payment status breakdown
                        status_breakdown = employee_data.groupby('status').agg({
                            'total_amount': 'sum',
                            'employee_name': 'count'
                        }).reset_index()
                        status_breakdown.columns = ['Status', 'Amount', 'Count']
                        
                        st.markdown("### 💳 Payment Status Breakdown")
                        
                        for _, row in status_breakdown.iterrows():
                            status_icon = "✅" if row['Status'] == 'paid' else "⏳" if row['Status'] == 'pending' else "❌"
                            st.metric(f"{status_icon} {row['Status'].title()}", 
                                    f"{row['Amount']:.2f} PLN", 
                                    f"{row['Count']} entries")
                        
                        # Detailed entries table
                        st.markdown("### 📋 Detailed Entries")
                        
                        # Prepare display data
                        display_emp_data = employee_data.copy()
                        
                        # Show exact DB values without any parsing - just display raw strings
                        display_emp_data['Date'] = display_emp_data['start_time'].astype(str).str[:10]
                        display_emp_data['Start Time'] = display_emp_data['start_time'].astype(str) 
                        display_emp_data['End Time'] = display_emp_data['end_time'].astype(str)
                        
                        # For overnight entries, still show raw values but indicate they're overnight
                        overnight_mask = display_emp_data['job_type'].isin(['overnight_pet_sitting', 'overnight_hotel'])
                        if overnight_mask.any():
                            # Just add prefix to indicate overnight, but keep raw values visible
                            display_emp_data.loc[overnight_mask, 'Start Time'] = 'Overnight: ' + display_emp_data.loc[overnight_mask, 'start_time'].astype(str)
                            display_emp_data.loc[overnight_mask, 'End Time'] = 'Overnight: ' + display_emp_data.loc[overnight_mask, 'end_time'].astype(str)
                        
                        display_emp_data['Amount'] = display_emp_data['total_amount'].round(2)
                        
                        # Safe duration calculation
                        if 'duration_hours' in display_emp_data.columns:
                            display_emp_data['Hours'] = pd.to_numeric(display_emp_data['duration_hours'], errors='coerce').fillna(0).round(2)
                        else:
                            display_emp_data['Hours'] = 0.0
                        
                        # Job type display mapping for details
                        display_emp_data['Job Type Display'] = display_emp_data['job_type'].map(job_type_display).fillna(display_emp_data['job_type'])
                        
                        # Select and order columns for display with safety checks
                        available_columns = display_emp_data.columns.tolist()
                        columns_to_show = []
                        
                        # Check if there are any entries that need date display to determine column headers
                        has_date_display_entries = ((display_emp_data['job_type'] == 'overnight_pet_sitting') | 
                                                   (display_emp_data['job_type'] == 'overnight_hotel') |
                                                   (display_emp_data['Start Time'] == 'N/A') |
                                                   (display_emp_data['End Time'] == 'N/A')).any()
                        
                        if has_date_display_entries:
                            # Mixed headers: Start Date/End Date for overnight, Start Time/End Time for others
                            column_mapping = {
                                'Date': 'Date',
                                'Start Time': 'Start Date/Time',
                                'End Time': 'End Date/Time',
                                'Job Type Display': 'Job Type',
                                'Hours': 'Hours/Units',
                                'Amount': 'Amount (PLN)',
                                'status': 'Status',
                                'description': 'Description',
                                'pet_names': 'Pets'
                            }
                        else:
                            # Regular headers for time-based entries
                            column_mapping = {
                                'Date': 'Date',
                                'Start Time': 'Start',
                                'End Time': 'End',
                                'Job Type Display': 'Job Type',
                                'Hours': 'Hours/Units',
                                'Amount': 'Amount (PLN)',
                                'status': 'Status',
                                'description': 'Description',
                                'pet_names': 'Pets'
                            }
                        
                        # Only include columns that exist
                        for col in ['Date', 'Start Time', 'End Time', 'Job Type Display', 'Hours', 'Amount']:
                            if col in available_columns:
                                columns_to_show.append(col)
                        
                        # Add optional columns if they exist
                        for col in ['status', 'description', 'pet_names']:
                            if col in available_columns:
                                columns_to_show.append(col)
                            else:
                                # Add placeholder column with empty values
                                display_emp_data[col] = ""
                                columns_to_show.append(col)
                        
                        final_emp_display = display_emp_data[columns_to_show].copy()
                        
                        # Rename columns
                        new_column_names = [column_mapping.get(col, col) for col in columns_to_show]
                        final_emp_display.columns = new_column_names
                        
                        # Sort by date and start time (handle both possible column names)
                        start_col = 'Start Date/Time' if 'Start Date/Time' in final_emp_display.columns else 'Start'
                        if start_col in final_emp_display.columns:
                            final_emp_display = final_emp_display.sort_values(['Date', start_col])
                        else:
                            final_emp_display = final_emp_display.sort_values(['Date'])
                        
                        st.dataframe(final_emp_display, use_container_width=True, hide_index=True)
                        
                        # Export options
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            csv_emp = final_emp_display.to_csv(index=False)
                            st.download_button(
                                label=f"📁 Download {selected_employee}'s Report (CSV)",
                                data=csv_emp,
                                file_name=f"{selected_employee}_report_{start_date}_{end_date}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col2:
                            # Summary for copying
                            
                            summary_text = f"""Employee Report Summary
Employee: {selected_employee}
Period: {start_date} to {end_date}
Total Entries: {emp_total_entries}
Total Amount: {emp_total_amount:.2f} PLN
Job Categories: {emp_job_types}

Job Category Breakdown:
{chr(10).join([f"- {row['Job Category']}: {row['Amount (PLN)']:.2f} PLN ({row['Count']} entries)" for _, row in job_display_final.iterrows()])}

Payment Status:
{chr(10).join([f"- {row['Status'].title()}: {row['Amount']:.2f} PLN ({row['Count']} entries)" for _, row in status_breakdown.iterrows()])}
"""
                            st.download_button(
                                label="📋 Download Summary (TXT)",
                                data=summary_text,
                                file_name=f"{selected_employee}_summary_{start_date}_{end_date}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                    else:
                        st.info(f"No entries found for {selected_employee} in the selected date range.")
                        
                except Exception as e:
                    st.error(f"❌ Error processing employee data: {str(e)}")
                    st.error("This may be due to data format issues. Please check the data in the database.")
                    # Show debug information
                    if st.checkbox("Show debug information"):
                        st.write("Employee data columns:", employee_data.columns.tolist() if 'employee_data' in locals() else "No data loaded")
                        if 'employee_data' in locals() and not employee_data.empty:
                            st.write("Sample data:")
                            st.write(employee_data.head())
        with tab4:
            st.subheader("📋 Detailed Entries")
            
            # Display all entries with better formatting
            display_data = range_data.copy()
            
            # Safe datetime parsing with enhanced error handling
            try:
                # Parse datetimes with coercion for invalid values
                start_datetime = pd.to_datetime(display_data['start_time'], errors='coerce')
                
                # Extract date component
                display_data['Date'] = start_datetime.dt.strftime('%Y-%m-%d')
                
                # Handle entries where datetime parsing failed (NaT values)
                invalid_start_mask = start_datetime.isna()
                
                if invalid_start_mask.any():
                    # Try to use date_created or other fallback for date
                    if 'date_created' in display_data.columns:
                        fallback_dates = pd.to_datetime(display_data.loc[invalid_start_mask, 'date_created'], errors='coerce')
                        display_data.loc[invalid_start_mask, 'Date'] = fallback_dates.dt.strftime('%Y-%m-%d')
                    else:
                        display_data.loc[invalid_start_mask, 'Date'] = "N/A"
                        
            except Exception as e:
                st.warning(f"Date parsing issue: {e}. Using fallback format.")
                display_data['Date'] = display_data['start_time'].astype(str).str[:10] if 'start_time' in display_data.columns else "N/A"
            
            display_data['Amount'] = display_data['total_amount'].round(2)
            
            # Safe duration calculation
            if 'duration_hours' in display_data.columns:
                display_data['Hours'] = pd.to_numeric(display_data['duration_hours'], errors='coerce').fillna(0).round(2)
            else:
                display_data['Hours'] = 0.0
            
            # Select columns to display
            columns_to_show = ['Date', 'employee_name', 'job_type', 'Hours', 'Amount', 'status', 'description']
            final_display = display_data[columns_to_show].copy()
            final_display.columns = ['Date', 'Employee', 'Job Type', 'Hours/Units', 'Amount (PLN)', 'Status', 'Description']
            
            st.dataframe(final_display, use_container_width=True, hide_index=True)
            
            # Export option
            csv = final_display.to_csv(index=False)
            st.download_button(
                label="📁 Download Detailed Report (CSV)",
                data=csv,
                file_name=f"detailed_report_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with tab5:
            st.subheader("📈 Analytics Dashboard")
            
            # Daily trend with safe datetime parsing
            try:
                range_data['date'] = pd.to_datetime(range_data['start_time'], errors='coerce').dt.date
            except Exception as e:
                st.warning(f"Date parsing issue for analytics: {e}. Using fallback format.")
                range_data['date'] = pd.to_datetime(range_data['start_time'].astype(str).str[:10], errors='coerce').dt.date
            
            daily_summary = range_data.groupby('date')['total_amount'].sum().reset_index()
            
            fig_daily = px.line(daily_summary, x='date', y='total_amount',
                              title="Daily Earnings Trend",
                              labels={'total_amount': 'Amount (PLN)', 'date': 'Date'})
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # Job type vs Employee heatmap
            pivot_data = range_data.pivot_table(
                index='employee_name',
                columns='job_type', 
                values='total_amount',
                aggfunc='sum',
                fill_value=0
            )
            
            if not pivot_data.empty:
                fig_heatmap = px.imshow(
                    pivot_data.values,
                    x=pivot_data.columns,
                    y=pivot_data.index,
                    title="Employee vs Job Type Earnings Heatmap",
                    labels=dict(x="Job Type", y="Employee", color="Amount (PLN)")
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
    
    else:
        st.info("📭 No data available for the selected period.")
        st.write("💡 Try selecting a different date range or check if employees have submitted timesheets.")

def render_employee_reports(current_user):
    """Employee reports page with detailed analytics"""
    st.title("📊 Employee Reports")
    
    def get_friday_week_range(target_date):
        """Get the Friday-to-Thursday week containing the target date"""
        days_from_friday = (target_date.weekday() + 3) % 7  # 0=Friday, 1=Saturday, ..., 6=Thursday
        week_start = target_date - timedelta(days=days_from_friday)  # Friday
        week_end = week_start + timedelta(days=6)  # Thursday
        return week_start, week_end
    
    # Initialize database connection
    conn = sqlite3.connect(DB_NAME)
    
    if current_user['is_admin']:
        st.markdown("### 👑 Administrator View - All Employee Reports")
        
        # Enhanced Date Range Selection
        st.subheader("📅 Date Range Selection")
        
        # Get current date and default ranges
        today = datetime.now().date()
        current_week_start, current_week_end = get_friday_week_range(today)
        
        # Initialize session state for dates if not exists
        if 'reports_start_date' not in st.session_state:
            st.session_state.reports_start_date = (datetime.now() - timedelta(days=30)).date()
        if 'reports_end_date' not in st.session_state:
            st.session_state.reports_end_date = datetime.now().date()
        
        # Quick preset buttons
        st.write("**Quick Presets:**")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("📍 Current Week (Fri-Thu)", help="Current Friday to Thursday week", key="admin_reports_current_week"):
                st.session_state.reports_start_date = current_week_start
                st.session_state.reports_end_date = current_week_end
        
        with col2:
            last_week_start = current_week_start - timedelta(days=7)
            last_week_end = current_week_end - timedelta(days=7)
            if st.button("⬅️ Last Week", help="Previous Friday to Thursday week", key="admin_reports_last_week"):
                st.session_state.reports_start_date = last_week_start
                st.session_state.reports_end_date = last_week_end
        
        with col3:
            if st.button("📅 Current Month", help="From 1st to last day of current month", key="admin_reports_current_month"):
                month_start = today.replace(day=1)
                next_month = month_start.replace(month=month_start.month % 12 + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
                month_end = next_month - timedelta(days=1)
                st.session_state.reports_start_date = month_start
                st.session_state.reports_end_date = month_end
        
        with col4:
            if st.button("⬅️ Last Month", help="Previous month", key="admin_reports_last_month"):
                if today.month == 1:
                    last_month_start = today.replace(year=today.year - 1, month=12, day=1)
                else:
                    last_month_start = today.replace(month=today.month - 1, day=1)
                
                # Get last day of previous month
                this_month_start = today.replace(day=1)
                last_month_end = this_month_start - timedelta(days=1)
                
                st.session_state.reports_start_date = last_month_start
                st.session_state.reports_end_date = last_month_end
        
        with col5:
            if st.button("📊 Last 30 Days", help="Past 30 days", key="admin_reports_last_30"):
                st.session_state.reports_start_date = today - timedelta(days=30)
                st.session_state.reports_end_date = today
        
        # Custom date range inputs
        st.write("**Custom Date Range:**")
        col1, col2 = st.columns(2)
        with col1:
            start_date_input = st.date_input("Start Date", value=st.session_state.reports_start_date, key="admin_reports_start_date")
            if start_date_input != st.session_state.reports_start_date:
                st.session_state.reports_start_date = start_date_input
        with col2:
            end_date_input = st.date_input("End Date", value=st.session_state.reports_end_date, key="admin_reports_end_date")
            if end_date_input != st.session_state.reports_end_date:
                st.session_state.reports_end_date = end_date_input
        
        # Use session state values
        start_date = st.session_state.reports_start_date
        end_date = st.session_state.reports_end_date
        
        # Date range info display
        date_range_days = (end_date - start_date).days + 1
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Selected Range:** {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
        with col2:
            st.info(f"**Duration:** {date_range_days} day{'s' if date_range_days != 1 else ''}")
        with col3:
            if start_date == current_week_start and end_date == current_week_end:
                st.success("📍 Current Week")
            elif start_date >= current_week_start:
                st.warning("⚠️ Includes Future Dates")
            else:
                st.info("📊 Historical Data")
        
        # Employee selector - get from database
        user_manager = UserManager()
        users = user_manager.get_all_users()
        employee_names = [user['employee_name'] for user in users if user['is_active']]
        employee_options = ['All Employees'] + employee_names
        selected_employee = st.selectbox("Select Employee", employee_options)
        
        # Generate report button
        if st.button("📈 Generate Report", use_container_width=True):
            with st.spinner("Generating reports..."):
                generate_admin_reports(conn, start_date, end_date, selected_employee)
    
    else:
        st.markdown(f"### 👤 Employee View - {current_user['name']}'s Reports")
        
        # Enhanced Date Range Selection for Employee
        st.subheader("📅 Date Range Selection")
        
        # Get current date and default ranges
        today = datetime.now().date()
        current_week_start, current_week_end = get_friday_week_range(today)
        
        # Initialize session state for employee dates if not exists
        if 'emp_reports_start_date' not in st.session_state:
            st.session_state.emp_reports_start_date = (datetime.now() - timedelta(days=30)).date()
        if 'emp_reports_end_date' not in st.session_state:
            st.session_state.emp_reports_end_date = datetime.now().date()
        
        # Quick preset buttons for employee
        st.write("**Quick Presets:**")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("📍 Current Week (Fri-Thu)", help="Current Friday to Thursday week", key="emp_reports_current_week"):
                st.session_state.emp_reports_start_date = current_week_start
                st.session_state.emp_reports_end_date = current_week_end
        
        with col2:
            last_week_start = current_week_start - timedelta(days=7)
            last_week_end = current_week_end - timedelta(days=7)
            if st.button("⬅️ Last Week", help="Previous Friday to Thursday week", key="emp_reports_last_week"):
                st.session_state.emp_reports_start_date = last_week_start
                st.session_state.emp_reports_end_date = last_week_end
        
        with col3:
            if st.button("📅 Current Month", help="From 1st to last day of current month", key="emp_reports_current_month"):
                month_start = today.replace(day=1)
                next_month = month_start.replace(month=month_start.month % 12 + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
                month_end = next_month - timedelta(days=1)
                st.session_state.emp_reports_start_date = month_start
                st.session_state.emp_reports_end_date = month_end
        
        with col4:
            if st.button("⬅️ Last Month", help="Previous month", key="emp_reports_last_month"):
                if today.month == 1:
                    last_month_start = today.replace(year=today.year - 1, month=12, day=1)
                else:
                    last_month_start = today.replace(month=today.month - 1, day=1)
                
                # Get last day of previous month
                this_month_start = today.replace(day=1)
                last_month_end = this_month_start - timedelta(days=1)
                
                st.session_state.emp_reports_start_date = last_month_start
                st.session_state.emp_reports_end_date = last_month_end
        
        with col5:
            if st.button("📊 Last 30 Days", help="Past 30 days", key="emp_reports_last_30"):
                st.session_state.emp_reports_start_date = today - timedelta(days=30)
                st.session_state.emp_reports_end_date = today
        
        # Custom date range inputs for employee
        st.write("**Custom Date Range:**")
        col1, col2 = st.columns(2)
        with col1:
            start_date_input = st.date_input("Start Date", value=st.session_state.emp_reports_start_date, key="emp_reports_start_date")
            if start_date_input != st.session_state.emp_reports_start_date:
                st.session_state.emp_reports_start_date = start_date_input
        with col2:
            end_date_input = st.date_input("End Date", value=st.session_state.emp_reports_end_date, key="emp_reports_end_date")
            if end_date_input != st.session_state.emp_reports_end_date:
                st.session_state.emp_reports_end_date = end_date_input
        
        # Use session state values
        start_date = st.session_state.emp_reports_start_date
        end_date = st.session_state.emp_reports_end_date
        
        # Date range info display for employee
        date_range_days = (end_date - start_date).days + 1
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Selected Range:** {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
        with col2:
            st.info(f"**Duration:** {date_range_days} day{'s' if date_range_days != 1 else ''}")
        with col3:
            if start_date == current_week_start and end_date == current_week_end:
                st.success("📍 Current Week")
            elif start_date >= current_week_start:
                st.warning("⚠️ Includes Future Dates")
            else:
                st.info("📊 Historical Data")
        
        # Generate personal report
        if st.button("📈 Generate My Report", use_container_width=True):
            with st.spinner("Generating your report..."):
                generate_employee_personal_report(conn, current_user, start_date, end_date)
    
    conn.close()

def generate_admin_reports(conn, start_date, end_date, selected_employee):
    """Generate comprehensive reports for admin"""
    
    try:
        # Base query using correct table and column names
        base_query = """
            SELECT 
                employee_name,
                start_time as date,
                job_type,
                pet_names,
                duration_hours as hours_worked,
                rate_per_hour as hourly_rate,
                total_amount,
                description as notes
            FROM timesheet 
            WHERE date(start_time) BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        
        if selected_employee != 'All Employees':
            base_query += " AND employee_name = ?"
            params.append(selected_employee)
        
        base_query += " ORDER BY start_time DESC, employee_name"
        
        df = pd.read_sql_query(base_query, conn, params=params)
        
    except Exception as e:
        st.error(f"Database query error: {str(e)}")
        st.info("This might be because there's no timesheet data yet. Try adding some timesheet entries first.")
        return
    
    if df.empty:
        st.warning("No data found for the selected period.")
        return
    
    # Convert start_time to date for grouping - use flexible datetime parsing
    df['date'] = pd.to_datetime(df['date'], format='mixed').dt.date
    
    # Summary metrics
    st.markdown("### 📊 Summary Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_amount = df['total_amount'].sum()
        st.metric("Total Amount", f"{total_amount:.2f} PLN")
    
    with col2:
        unique_employees = df['employee_name'].nunique()
        st.metric("Active Employees", unique_employees)
    
    with col3:
        total_entries = len(df)
        st.metric("Total Entries", total_entries)
    
    # Employee breakdown
    st.markdown("### 👥 Employee Breakdown")
    
    employee_summary = df.groupby('employee_name').agg({
        'total_amount': 'sum',
        'date': 'count'
    }).round(2)
    employee_summary.columns = ['Total Amount (PLN)', 'Number of Entries']
    employee_summary = employee_summary.sort_values('Total Amount (PLN)', ascending=False)
    
    st.dataframe(employee_summary, use_container_width=True)
    
    # Job type analysis
    st.markdown("### 🏢 Job Type Analysis")
    
    job_summary = df.groupby('job_type').agg({
        'total_amount': 'sum',
        'date': 'count'
    }).round(2)
    job_summary.columns = ['Total Amount (PLN)', 'Number of Entries']
    job_summary = job_summary.sort_values('Total Amount (PLN)', ascending=False)
    
    st.dataframe(job_summary, use_container_width=True)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💰 Earnings by Employee")
        fig_employee = px.bar(
            employee_summary.reset_index(), 
            x='employee_name', 
            y='Total Amount (PLN)',
            title="Total Earnings by Employee"
        )
        st.plotly_chart(fig_employee, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Entries by Job Type")
        fig_job = px.pie(
            job_summary.reset_index(), 
            names='job_type', 
            values='Number of Entries',
            title="Entry Distribution by Job Type"
        )
        st.plotly_chart(fig_job, use_container_width=True)
    
    # Daily timeline
    st.markdown("### 📅 Daily Timeline")
    daily_summary = df.groupby('date').agg({
        'total_amount': 'sum'
    }).reset_index()
    
    fig_timeline = px.line(
        daily_summary, 
        x='date', 
        y='total_amount',
        title="Daily Earnings Timeline",
        labels={'total_amount': 'Amount (PLN)', 'date': 'Date'}
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Detailed data table
    st.markdown("### 📋 Detailed Entries")
    
    # Format the dataframe for display
    display_df = df.copy()
    display_df['date'] = pd.to_datetime(display_df['date'], format='mixed').dt.strftime('%Y-%m-%d')
    display_df['total_amount'] = display_df['total_amount'].round(2)
    display_df['hours_worked'] = display_df['hours_worked'].round(2)
    
    st.dataframe(display_df, use_container_width=True)
    
    # Export options
    st.markdown("### 💾 Export Data")
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📁 Download CSV",
            data=csv,
            file_name=f"employee_report_{start_date}_to_{end_date}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Create Excel file
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Detailed Data', index=False)
            employee_summary.to_excel(writer, sheet_name='Employee Summary')
            job_summary.to_excel(writer, sheet_name='Job Type Summary')
        
        st.download_button(
            label="📊 Download Excel",
            data=excel_buffer.getvalue(),
            file_name=f"employee_report_{start_date}_to_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def generate_employee_personal_report(conn, current_user, start_date, end_date):
    """Generate personal report for individual employee"""
    
    try:
        query = """
            SELECT 
                start_time as date,
                job_type,
                pet_names,
                duration_hours as hours_worked,
                rate_per_hour as hourly_rate,
                total_amount,
                description as notes,
                COALESCE(payment_status, 'pending') as payment_status
            FROM timesheet 
            WHERE employee_name = ? AND date(start_time) BETWEEN ? AND ?
            ORDER BY start_time DESC
        """
        
        df = pd.read_sql_query(query, conn, params=[current_user['name'], start_date, end_date])
        
    except Exception as e:
        st.error(f"Database query error: {str(e)}")
        st.info("This might be because there's no timesheet data yet. Try adding some timesheet entries first.")
        return
    
    if df.empty:
        st.warning("No timesheet entries found for the selected period.")
        return
    
    # Convert start_time to date for processing - use flexible datetime parsing
    df['date'] = pd.to_datetime(df['date'], format='mixed').dt.date
    
    # 1. DETAILED ENTRIES FIRST (as requested)
    st.markdown("### 📋 Your Detailed Entries")
    
    display_df = df.copy()
    display_df['date'] = pd.to_datetime(display_df['date'], format='mixed').dt.strftime('%Y-%m-%d')
    display_df['total_amount'] = display_df['total_amount'].round(2)
    display_df['hours_worked'] = display_df['hours_worked'].round(2)
    
    # Add payment status styling
    def style_payment_status(val):
        if val == 'paid':
            return 'background-color: #d4edda; color: #155724;'
        elif val == 'pending':
            return 'background-color: #fff3cd; color: #856404;'
        else:
            return ''
    
    styled_df = display_df.style.applymap(style_payment_status, subset=['payment_status'])
    st.dataframe(styled_df, use_container_width=True)
    
    # 2. SUMMARY METRICS 
    st.markdown("### 📊 Your Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_earnings = df['total_amount'].sum()
        st.metric("Total Earnings", f"{total_earnings:.2f} PLN")
    
    with col2:
        paid_amount = df[df['payment_status'] == 'paid']['total_amount'].sum()
        st.metric("Amount Paid", f"{paid_amount:.2f} PLN", 
                 delta=f"{total_earnings - paid_amount:.2f} PLN pending")
    
    with col3:
        total_entries = len(df)
        st.metric("Total Entries", total_entries)
    
    # 3. JOB TYPE BREAKDOWN
    st.markdown("### 🏢 Your Job Type Breakdown")
    
    job_breakdown = df.groupby('job_type').agg({
        'hours_worked': 'sum',
        'total_amount': 'sum',
        'date': 'count'
    }).round(2)
    job_breakdown.columns = ['Hours Worked', 'Earnings (PLN)', 'Number of Sessions']
    job_breakdown = job_breakdown.sort_values('Earnings (PLN)', ascending=False)
    
    st.dataframe(job_breakdown, use_container_width=True)
    
    # 4. CHARTS
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💰 Earnings by Job Type")
        fig_earnings = px.bar(
            job_breakdown.reset_index(), 
            x='job_type', 
            y='Earnings (PLN)',
            title="Your Earnings by Job Type"
        )
        st.plotly_chart(fig_earnings, use_container_width=True)
    
    with col2:
        st.markdown("#### ⏰ Hours by Job Type")
        fig_hours = px.pie(
            job_breakdown.reset_index(), 
            names='job_type', 
            values='Hours Worked',
            title="Your Hours Distribution"
        )
        st.plotly_chart(fig_hours, use_container_width=True)
    
    # 5. TIMELINE
    st.markdown("### 📅 Your Daily Earnings")
    daily_earnings = df.groupby('date')['total_amount'].sum().reset_index()
    
    fig_personal_timeline = px.bar(
        daily_earnings, 
        x='date', 
        y='total_amount',
        title="Your Daily Earnings",
        labels={'total_amount': 'Earnings (PLN)', 'date': 'Date'}
    )
    st.plotly_chart(fig_personal_timeline, use_container_width=True)
    
    # 6. EXPORT
    st.markdown("### 💾 Export Your Data")
    csv = df.to_csv(index=False)
    st.download_button(
        label="📁 Download My Report (CSV)",
        data=csv,
        file_name=f"my_timesheet_{current_user['name']}_{start_date}_to_{end_date}.csv",
        mime="text/csv",
        use_container_width=True
    )

def render_data_export():
    """Data Export functionality"""
    st.title("📁 Data Export")
    
    # Export options
    st.subheader("Export Options")
    
    # Add informational note about payment filtering
    if st.checkbox("ℹ️ Show Payment Filter Help", value=False):
        st.info("""
        **Payment Status Filter Options:**
        - **All Records**: Export all timesheet entries regardless of payment status
        - **Pending Payments Only**: Export only entries that haven't been paid yet
        - **Paid Records Only**: Export only entries that have been marked as paid
        
        This feature is useful for:
        - Generating payroll reports for pending payments
        - Tracking which employees need to be paid
        - Maintaining payment history records
        """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_type = st.radio("Export Type:", ["Current Week", "All Data", "Custom Date Range"])
        
        # Payment status filter
        payment_filter = st.radio("Payment Status Filter:", 
                                ["All Records", "Pending Payments Only", "Paid Records Only"])
    
    with col2:
        if export_type == "Custom Date Range":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
    
    # Get data based on selection
    payment_status_filter = None
    if payment_filter == "Pending Payments Only":
        payment_status_filter = "pending"
    elif payment_filter == "Paid Records Only":
        payment_status_filter = "paid"
    
    if export_type == "Current Week":
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start_str = week_start.date().isoformat()
        export_data = get_timesheet_data_with_payment_filter(
            week_start=week_start_str, 
            payment_status=payment_status_filter
        )
        payment_suffix = f"_{payment_filter.lower().replace(' ', '_')}" if payment_filter != "All Records" else ""
        filename = f"citypets_timesheet_week_{week_start_str}{payment_suffix}.xlsx"
    
    elif export_type == "All Data":
        export_data = get_timesheet_data_with_payment_filter(
            payment_status=payment_status_filter
        )
        payment_suffix = f"_{payment_filter.lower().replace(' ', '_')}" if payment_filter != "All Records" else ""
        filename = f"citypets_timesheet_all_data{payment_suffix}.xlsx"
    
    else:  # Custom Date Range
        export_data = get_timesheet_data_with_payment_filter(
            payment_status=payment_status_filter,
            start_date=start_date,
            end_date=end_date
        )
        payment_suffix = f"_{payment_filter.lower().replace(' ', '_')}" if payment_filter != "All Records" else ""
        filename = f"citypets_timesheet_custom_{start_date}_{end_date}{payment_suffix}.xlsx"
    
    if not export_data.empty:
        # Prepare data for export
        export_df = export_data.copy()
        export_df['pet_names'] = export_df['pet_names'].apply(
            lambda x: ', '.join(json.loads(x)) if x and x != '[]' else ''
        )
        
        # Create properly formatted Duration column
        def format_duration_with_units(row):
            duration = row['duration_hours']
            job_type = row['job_type']
            
            if job_type in ['dog_at_home', 'cat_at_home']:
                return f"{int(duration)} day{'s' if duration != 1 else ''}"
            elif job_type == 'overnight_hotel':
                # Convert hours to nights (12 hours = 1 night)
                if duration >= 12:
                    nights = int(round(duration / 12))
                else:
                    nights = int(duration) if duration >= 1 else 1
                nights = max(1, nights)
                return f"{nights} night{'s' if nights != 1 else ''}"
            elif job_type == 'cat_visit':
                return f"{int(duration)} visit{'s' if duration != 1 else ''}"
            elif job_type == 'overnight_pet_sitting':
                return f"{int(duration)} night{'s' if duration != 1 else ''}"
            elif job_type in ['transport_km']:
                return f"{duration:.1f} KM"
            elif job_type == 'expense':
                return f"{duration:.2f} PLN"
            else:
                return f"{duration:.1f} hour{'s' if duration != 1 else ''}"
        
        export_df['Duration'] = export_df.apply(format_duration_with_units, axis=1)
        
        # Keep duration_hours for summary calculations before removing
        duration_hours_col = export_df['duration_hours'].copy()
        
        # Remove internal columns and include payment status
        columns_to_export = ['employee_name', 'job_type', 'start_time', 'end_time', 
                           'Duration', 'rate_per_hour', 'total_amount', 
                           'description', 'pet_names', 'payment_status_clean', 'date_created']
        export_df = export_df[columns_to_export]
        
        # Rename columns for better readability
        export_df.columns = [EMPLOYEE_NAME, 'Job Type', 'Start Time', 'End Time', 
                           'Duration', 'Rate (PLN/hr)', TOTAL_AMOUNT_PLN, 
                           'Description', 'Pet Names', 'Payment Status', 'Entry Date']
        
        # Add back duration_hours for summary calculations
        export_df['duration_hours_temp'] = duration_hours_col
        
        # Display preview
        st.subheader("Data Preview")
        st.dataframe(export_df.head(10), use_container_width=True)
        
        st.subheader("Summary")
        st.write(f"**Total Records:** {len(export_df)}")
        # Note: Can't sum Duration column since it contains mixed units (hours, days, visits, etc.)
        st.write(f"**Total Amount:** {export_df[TOTAL_AMOUNT_PLN].sum():.2f} PLN")
        
        # Payment status summary
        if 'Payment Status' in export_df.columns:
            pending_count = len(export_df[export_df['Payment Status'] == 'pending'])
            paid_count = len(export_df[export_df['Payment Status'] == 'paid'])
            pending_amount = export_df[export_df['Payment Status'] == 'pending'][TOTAL_AMOUNT_PLN].sum()
            paid_amount = export_df[export_df['Payment Status'] == 'paid'][TOTAL_AMOUNT_PLN].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**🟡 Pending:** {pending_count} entries ({pending_amount:.2f} PLN)")
            with col2:
                st.write(f"**🟢 Paid:** {paid_count} entries ({paid_amount:.2f} PLN)")
        
        # Convert to Excel
        try:
            from io import BytesIO
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Add summary sheet
                summary_df = export_df.groupby(EMPLOYEE_NAME).agg({
                    TOTAL_AMOUNT_PLN: 'sum',
                    EMPLOYEE_NAME: 'count'
                }).rename(columns={
                    EMPLOYEE_NAME: 'Total Entries'
                }).round(2)
                
                # Remove the temporary column from main export
                export_df_clean = export_df.drop('duration_hours_temp', axis=1)
                
                # Write main data (without temp column)
                export_df_clean.to_excel(writer, index=False, sheet_name='Timesheet Data')
                
                summary_df.to_excel(writer, sheet_name='Employee Summary')
            
            # Download button
            st.download_button(
                label="📥 Download Excel File",
                data=buffer.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.error("📊 Excel export requires openpyxl package. Please install it with: pip install openpyxl")
            
            # Fallback: Provide CSV export instead
            export_df_clean = export_df.drop('duration_hours_temp', axis=1)
            csv_data = export_df_clean.to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV (Fallback)",
                data=csv_data,
                file_name=filename.replace('.xlsx', '.csv'),
                mime="text/csv"
            )
    
    else:
        st.info("No data available for export.")

# Entry point
if __name__ == "__main__":
    main()
