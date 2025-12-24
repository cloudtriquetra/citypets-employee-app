# Employee Configuration for CityPets Timesheet
# All rates in PLN

import json
import os

# File to persist job type restrictions
RESTRICTIONS_FILE = "job_type_restrictions.json"

# File to persist employee configurations
EMPLOYEES_FILE = "employees_config.json"

# File to persist pet custom rates
PET_RATES_FILE = "pet_custom_rates.json"

# File to persist holiday dates
HOLIDAY_DATES_FILE = "holiday_dates.json"

# Holiday dates storage
HOLIDAY_DATES = []

# Pet-specific custom rates that apply to ALL employees
# Format: "pet_name": {"job_type": custom_rate}
# Note: These are now loaded from pet_custom_rates.json file
PET_CUSTOM_RATES = {
    # Default rates are now managed through the JSON file
    # Use the UI or functions to add pet custom rates
}

def remove_pet_custom_rate(pet_name, job_type):
    """Remove a custom rate for a specific pet-job combination"""
    if pet_name in PET_CUSTOM_RATES and job_type in PET_CUSTOM_RATES[pet_name]:
        del PET_CUSTOM_RATES[pet_name][job_type]
        
        # Clean up empty pet entry
        if not PET_CUSTOM_RATES[pet_name]:
            del PET_CUSTOM_RATES[pet_name]
        
        _save_pet_rates_to_file()  # Save changes
        return True
    return False

def get_pet_custom_rates(pet_name=None):
    """Get custom rates for a specific pet or all pets"""
    if pet_name:
        return PET_CUSTOM_RATES.get(pet_name, {})
    return PET_CUSTOM_RATES

def has_pet_custom_rate(pet_name, job_type):
    """Check if a pet has a custom rate for a specific job type"""
    return pet_name in PET_CUSTOM_RATES and job_type in PET_CUSTOM_RATES[pet_name]

def list_pets_with_custom_rates():
    """Get list of all pets that have custom rates"""
    return list(PET_CUSTOM_RATES.keys())

# Job Types - definitions and descriptions
JOB_TYPES = {
    "hotel": {
        "name": "Hotel (Hours)",
        "description": "Hotel/daycare work - hourly rate"
    },
    "walk": {
        "name": "Walk (Hours)", 
        "description": "Dog walking - hourly rate"
    },
    "overnight_hotel": {
        "name": "Overnight Hotel",
        "description": "Overnight hotel shift - flat rate"
    },
    "expense": {
        "name": "Expense (PLN)",
        "description": "General expenses - exact amount in PLN (requires description and photo)"
    },
    "cat_visit": {
        "name": "Cat Visit",
        "description": "Cat visit service - per visit"
    },
    "pet_sitting_hourly": {
        "name": "Pet Sitting Hourly",
        "description": "Pet sitting - hourly rate"
    },
    "pet_sitting": {
        "name": "Pet Sitting",
        "description": "Unified pet sitting - multi-day support with smart segmentation"
    },
    "overnight_pet_sitting": {
        "name": "Overnight Pet Sitting",
        "description": "Overnight pet sitting - flat rate"
    },
    "dog_at_home": {
        "name": "dog@home",
        "description": "Dog care at home - per session"
    },
    "cat_at_home": {
        "name": "cat@home",
        "description": "Cat care at home - per session"
    },
    "management": {
        "name": "management",
        "description": "Management tasks - hourly rate"
    },
    "transport": {
        "name": "Transport (Hours)",
        "description": "Transportation - hourly rate"
    },
    "transport_km": {
        "name": "Transport KM",
        "description": "Transportation per KM - employee-specific rates"
    },
    "training": {
        "name": "Training (Hours)",
        "description": "Training sessions - hourly rate"
    },
    "household_work": {
        "name": "Household Work (Hours)",
        "description": "Household work tasks - hourly rate"
    }
    # Note: Holiday rates are applied automatically by admin for specific dates
    # They modify hotel and overnight job types (not walk) with higher rates
}

# Employee configurations - each employee has their own defined rates
EMPLOYEES = {
    "ROXANA": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        # Holiday rates - applied automatically by admin on designated dates
        "holiday_rate_hotel": 30,      # Holiday rate for hotel work
        "holiday_rate_overnight_hotel_hotel": 100  # Holiday rate for overnight work (both hotel and pet sitting)
    },
    "JEAN": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "SURIYA": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "KUBA": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "ANKITA": {
        "hotel": 28,
        "walk": 28,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 20,  # Special rate: 20 PLN/hour
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 32,      # Holiday rate for hotel work (higher base rate)
        "holiday_rate_walk": 32,       # Holiday rate for walk work (higher base rate)
        "holiday_rate_overnight_hotel_hotel": 100  # Holiday rate for overnight work
    },
    "PIYUSH": {
        "hotel": 28,
        "walk": 28,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 32,
        "holiday_rate_walk": 32,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "PRACHI": {
        "hotel": 28,
        "walk": 28,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "management": 30,
        "holiday_rate_hotel": 32,
        "holiday_rate_walk": 32,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "SEAN": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "YASH": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "NAREYA": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "ERAY": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "management": 30,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "OGUZ": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "transport": 25,
        "transport_km": 1.5,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    },
    "WERONIKA": {
        "hotel": 25,
        "walk": 25,
        "overnight_hotel": 90,
        "cat_visit": 30,
        "pet_sitting_hourly": 17,
        "overnight_pet_sitting": 140,
        "dog_at_home": 75,
        "cat_at_home": 25,
        "management": 30,
        "transport": 25,
        "transport_km": 1.15,
        "training": 100,
        "holiday_rate_hotel": 30,
        "holiday_rate_walk": 30,
        "holiday_rate_overnight_hotel_hotel": 100
    }
}

# Job type restrictions - controls which employees can access specific job types
# Format: "job_type": ["employee1", "employee2", ...] or "job_type": "all" for all employees
JOB_TYPE_RESTRICTIONS = {
    "training": ["WERONIKA"],  # Only Weronika can do training by default
    # "management": ["PRACHI", "ERAY"],  # Example: Only specific employees can do management
    # Add more job type restrictions as needed
}

def _save_restrictions_to_file():
    """Save current job type restrictions to JSON file"""
    try:
        with open(RESTRICTIONS_FILE, 'w') as f:
            json.dump(JOB_TYPE_RESTRICTIONS, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving restrictions: {e}")
        return False

def _load_restrictions_from_file():
    """Load job type restrictions from JSON file"""
    global JOB_TYPE_RESTRICTIONS
    try:
        if os.path.exists(RESTRICTIONS_FILE):
            with open(RESTRICTIONS_FILE, 'r') as f:
                loaded_restrictions = json.load(f)
                JOB_TYPE_RESTRICTIONS.update(loaded_restrictions)
        return True
    except Exception as e:
        print(f"Error loading restrictions: {e}")
        return False

def _save_employees_to_file():
    """Save current employee data to JSON file"""
    try:
        with open(EMPLOYEES_FILE, 'w') as f:
            json.dump(EMPLOYEES, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving employees: {e}")
        return False

def _load_employees_from_file():
    """Load employee data from JSON file"""
    global EMPLOYEES
    try:
        if os.path.exists(EMPLOYEES_FILE):
            with open(EMPLOYEES_FILE, 'r') as f:
                loaded_employees = json.load(f)
                EMPLOYEES.update(loaded_employees)
        return True
    except Exception as e:
        print(f"Error loading employees: {e}")
        return False

# Load restrictions from file on module import
_load_restrictions_from_file()

# Load employees from file on module import
_load_employees_from_file()

# Pet custom rates persistence functions
def _save_pet_rates_to_file():
    """Save current pet custom rates to JSON file"""
    try:
        with open(PET_RATES_FILE, 'w') as f:
            json.dump(PET_CUSTOM_RATES, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving pet custom rates: {e}")
        return False

def _load_pet_rates_from_file():
    """Load pet custom rates from JSON file"""
    global PET_CUSTOM_RATES
    try:
        if os.path.exists(PET_RATES_FILE):
            with open(PET_RATES_FILE, 'r') as f:
                loaded_rates = json.load(f)
                PET_CUSTOM_RATES = loaded_rates  # Replace instead of update
        return True
    except Exception as e:
        print(f"Error loading pet custom rates: {e}")
        return False

# Load pet rates from file on module import
_load_pet_rates_from_file()

# Holiday dates persistence functions
def _save_holiday_dates_to_file():
    """Save current holiday dates to JSON file"""
    try:
        with open(HOLIDAY_DATES_FILE, 'w') as f:
            json.dump({"holiday_dates": HOLIDAY_DATES}, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving holiday dates: {e}")
        return False

def _load_holiday_dates_from_file():
    """Load holiday dates from JSON file"""
    global HOLIDAY_DATES
    try:
        if os.path.exists(HOLIDAY_DATES_FILE):
            with open(HOLIDAY_DATES_FILE, 'r') as f:
                data = json.load(f)
                HOLIDAY_DATES = data.get("holiday_dates", [])
        return True
    except Exception as e:
        print(f"Error loading holiday dates: {e}")
        return False

def add_holiday_date(date_str):
    """Add a date as a holiday"""
    if date_str not in HOLIDAY_DATES:
        HOLIDAY_DATES.append(date_str)
        _save_holiday_dates_to_file()
        return True
    return False

def remove_holiday_date(date_str):
    """Remove a holiday date"""
    if date_str in HOLIDAY_DATES:
        HOLIDAY_DATES.remove(date_str)
        _save_holiday_dates_to_file()
        return True
    return False

def is_holiday(date_str):
    """Check if a date is a holiday"""
    return date_str in HOLIDAY_DATES

def get_all_holiday_dates():
    """Get list of all holiday dates"""
    return HOLIDAY_DATES.copy()

# Load holiday dates from file on module import
_load_holiday_dates_from_file()

def get_employee_rate(employee_name, job_type, pet_names=None, date_str=None):
    """Get the rate for a specific employee and job type, considering pet-specific rates and holiday dates
    
    Args:
        employee_name: Name of the employee
        job_type: Type of job
        pet_names: Optional pet names for pet-specific rates
        date_str: Date string in YYYY-MM-DD format to check for holiday rates
    """
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    # For expense, always return 1 (exact amount, no rate multiplication)
    if job_type == "expense":
        return 1
    
    # Handle special "pet_sitting" job type (used for UI, but segments use specific types)
    if job_type == "pet_sitting":
        # Default to pet_sitting_hourly rate for validation purposes
        # The actual segmentation will use the correct job types
        if "pet_sitting_hourly" in EMPLOYEES[employee_name]:
            job_type = "pet_sitting_hourly"
        else:
            raise ValueError(f"Job type pet_sitting not available for employee {employee_name}")
    
    # Check for pet-specific rates first (applies to ALL employees)
    if pet_names:
        if isinstance(pet_names, str):
            pet_names = [pet_names]
        
        for pet_name in pet_names:
            if pet_name in PET_CUSTOM_RATES and job_type in PET_CUSTOM_RATES[pet_name]:
                return PET_CUSTOM_RATES[pet_name][job_type]
    
    # Check if this is a holiday date and use holiday rate if available
    if date_str and is_holiday(date_str):
        holiday_job_type = f"holiday_rate_{job_type}"
        if holiday_job_type in EMPLOYEES[employee_name]:
            return EMPLOYEES[employee_name][holiday_job_type]
        # If job type is overnight_hotel, check for holiday_rate_overnight_hotel
        elif job_type == "overnight_hotel" and "holiday_rate_overnight_hotel" in EMPLOYEES[employee_name]:
            return EMPLOYEES[employee_name]["holiday_rate_overnight_hotel"]
    
    # Use employee's standard rate
    if job_type not in EMPLOYEES[employee_name]:
        raise ValueError(f"Job type {job_type} not available for employee {employee_name}")
    
    return EMPLOYEES[employee_name][job_type]

def get_employee_job_types(employee_name):
    """Get list of available job types for a specific employee"""
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    # Start with employee's defined job types
    job_types = list(EMPLOYEES[employee_name].keys())
    
    # Remove holiday rates - these are applied automatically by admin on specific dates
    job_types = [jt for jt in job_types if not jt.startswith('holiday_rate_')]
    
    # Remove transport_km from user dropdown since Transport now creates both entries automatically
    job_types = [jt for jt in job_types if jt != 'transport_km']
    
    # Add expense since it's available to all employees (no rate needed)
    if "expense" not in job_types:
        job_types.append("expense")
    
    # Replace individual pet sitting types with unified "pet_sitting"
    if "pet_sitting_hourly" in job_types or "overnight_pet_sitting" in job_types:
        # Remove individual pet sitting types
        job_types = [jt for jt in job_types if jt not in ["pet_sitting_hourly", "overnight_pet_sitting"]]
        # Add unified pet_sitting if not already there
        if "pet_sitting" not in job_types:
            job_types.append("pet_sitting")
    
    # Apply job type restrictions
    filtered_job_types = []
    for job_type in job_types:
        if is_job_type_allowed_for_employee(employee_name, job_type):
            filtered_job_types.append(job_type)
    
    return filtered_job_types

def get_employee_admin_job_types(employee_name):
    """Get list of job types for admin rate management (shows individual pet sitting types)"""
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    # Start with employee's defined job types
    job_types = list(EMPLOYEES[employee_name].keys())
    
    # Remove holiday rates - these are applied automatically by admin on specific dates
    job_types = [jt for jt in job_types if not jt.startswith('holiday_rate_')]
    
    # Add expense since it's available to all employees (no rate needed)
    if "expense" not in job_types:
        job_types.append("expense")
    
    # Don't unify pet sitting types for admin - show individual rates
    return job_types

def is_job_type_allowed_for_employee(employee_name, job_type):
    """Check if a job type is allowed for a specific employee based on restrictions"""
    # Check if there are restrictions for this job type
    if job_type in JOB_TYPE_RESTRICTIONS:
        restrictions = JOB_TYPE_RESTRICTIONS[job_type]
        
        # If restrictions is "all", allow all employees
        if restrictions == "all":
            return True
        
        # If restrictions is a list, check if employee is in the list
        if isinstance(restrictions, list):
            return employee_name in restrictions
        
        # If restrictions is not a list or "all", deny access
        return False
    
    # No restrictions for this job type, allow all employees
    return True

def can_employee_do_job(employee_name, job_type):
    """Check if an employee can perform a specific job type"""
    if employee_name not in EMPLOYEES:
        return False
    
    
    # expense is available to all employees
    if job_type == "expense":
        return True
    
    # Check if employee has this job type defined AND if it's allowed by restrictions
    return job_type in EMPLOYEES[employee_name] and is_job_type_allowed_for_employee(employee_name, job_type)

def get_job_type_info(job_type):
    """Get information about a job type"""
    
    if job_type not in JOB_TYPES:
        return None
    
    return JOB_TYPES[job_type]

def list_employees():
    """Get list of all employees"""
    return list(EMPLOYEES.keys())

def list_job_types():
    """Get list of all job types"""
    return list(JOB_TYPES.keys())

def add_employee(name, rates=None):
    """Add a new employee with default or custom rates"""
    if rates is None:
        # Use standard rates template
        rates = {
            "hotel": 25,
            "walk": 25,
            "overnight_hotel": 90,
            "cat_visit": 30,
            "pet_sitting_hourly": 17,
            "overnight_pet_sitting": 140,
            "dog_at_home": 75,
            "cat_at_home": 25,
            "holiday_rate_hotel": 30,
            "holiday_rate_walk": 30,
            "holiday_rate_overnight_hotel_hotel": 100
        }
    
    EMPLOYEES[name] = rates
    _save_employees_to_file()  # Save changes
    return True

def remove_employee(employee_name):
    """Remove an employee (offboarding)"""
    if employee_name not in EMPLOYEES:
        return False, f"Employee {employee_name} not found"
    
    # Remove from main employees dict
    del EMPLOYEES[employee_name]
    
    _save_employees_to_file()  # Save changes
    return True, f"Employee {employee_name} has been removed"

def update_employee_base_rate(employee_name, job_type, new_rate):
    """Update a rate for an employee"""
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    
    EMPLOYEES[employee_name][job_type] = new_rate
    _save_employees_to_file()  # Save changes
    return True

def get_all_employee_data():
    """Get complete employee data including rates"""
    employee_data = {}
    for emp_name, rates in EMPLOYEES.items():
        employee_data[emp_name] = {
            'rates': rates.copy(),
            'is_active': True
        }
    return employee_data

def clone_employee_rates(source_employee, target_employee):
    """Clone rates from one employee to another"""
    if source_employee not in EMPLOYEES:
        raise ValueError(f"Source employee {source_employee} not found")
    
    # Clone rates
    EMPLOYEES[target_employee] = EMPLOYEES[source_employee].copy()
    
    _save_employees_to_file()  # Save changes
    return True

def update_employee_rate(employee_name, job_type, new_rate):
    """Update a specific rate for an employee"""
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    
    # expense doesn't need to be stored - it's always 1
    if job_type == "expense":
        return True
    
    EMPLOYEES[employee_name][job_type] = new_rate
    _save_employees_to_file()  # Save changes
    return True

def set_custom_rate(employee_name, job_type, custom_rate):
    """Set a rate for a specific employee-job combination (now just updates the employee's rate)"""
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    
    # Check if job type is available for this employee
    if job_type not in EMPLOYEES[employee_name]:
        raise ValueError(f"Job type {job_type} not available for employee {employee_name}")
    
    EMPLOYEES[employee_name][job_type] = custom_rate
    _save_employees_to_file()  # Save changes
    return True

def remove_custom_rate(employee_name, job_type):
    """Reset a rate to a standard value (since we no longer have separate custom rates)"""
    
    if employee_name in EMPLOYEES and job_type in EMPLOYEES[employee_name]:
        # Reset to a standard rate based on job type
        standard_rates = {
            "hotel": 25, "walk": 25, "overnight_hotel": 90,
            "cat_visit": 30, "pet_sitting_hourly": 17, "overnight_pet_sitting": 140,
            "dog_at_home": 75, "cat_at_home": 25, "management": 30, "transport": 25,
            "transport_km": 1.0,  # Default KM rate
            "holiday_rate_hotel": 30, "holiday_rate_walk": 30, "holiday_rate_overnight_hotel_hotel": 100
        }
        if job_type in standard_rates:
            EMPLOYEES[employee_name][job_type] = standard_rates[job_type]
            _save_employees_to_file()  # Save changes
            return True
    return False

def get_custom_rates(employee_name=None):
    """Get rates for a specific employee or all employees (simplified since no separate custom rates)"""
    if employee_name:
        return EMPLOYEES.get(employee_name, {})
    return dict(EMPLOYEES.items())

def has_custom_rate(employee_name, job_type):
    """Check if an employee has a rate for a specific job type"""
    
    return employee_name in EMPLOYEES and job_type in EMPLOYEES[employee_name]

def set_pet_custom_rate(pet_name, job_type, custom_rate):
    """Set a custom rate for a specific pet-job combination (applies to all employees)"""
    
    # Check if job type exists
    if job_type not in JOB_TYPES:
        raise ValueError(f"Job type {job_type} not found")
    
    # Initialize pet custom rates if not exists
    if pet_name not in PET_CUSTOM_RATES:
        PET_CUSTOM_RATES[pet_name] = {}
    
    PET_CUSTOM_RATES[pet_name][job_type] = custom_rate
    _save_pet_rates_to_file()  # Save changes
    return True

# Holiday Rate Management
# Holiday rates are applied automatically by admin for specific dates
# They override the normal rates for hotel, walk, and overnight job types

def get_holiday_rate(employee_name, job_type):
    """Get the holiday rate for a specific employee and job type"""
    if employee_name not in EMPLOYEES:
        raise ValueError(f"Employee {employee_name} not found")
    
    # Map job types to their holiday rate equivalents
    holiday_rate_mapping = {
        "hotel": "holiday_rate_hotel",
        "walk": "holiday_rate_walk", 
        "overnight_hotel": "holiday_rate_overnight_hotel"
    }
    
    if job_type not in holiday_rate_mapping:
        # No holiday rate for this job type, return regular rate
        return get_employee_rate(employee_name, job_type)
    
    holiday_rate_key = holiday_rate_mapping[job_type]
    
    if holiday_rate_key not in EMPLOYEES[employee_name]:
        # Fallback to regular rate if holiday rate not defined
        return get_employee_rate(employee_name, job_type)
    
    return EMPLOYEES[employee_name][holiday_rate_key]

def is_holiday_applicable_job(job_type):
    """Check if a job type can have holiday rates applied"""
    return job_type in ["hotel", "walk", "overnight_hotel"]

# Job Type Restriction Management Functions
def add_job_type_restriction(job_type, employees):
    """Add or update job type restrictions for specific employees"""
    
    if job_type not in JOB_TYPES:
        raise ValueError(f"Job type {job_type} not found")
    
    # Validate employees exist
    if employees != "all":
        if isinstance(employees, str):
            employees = [employees]
        for emp in employees:
            if emp not in EMPLOYEES:
                raise ValueError(f"Employee {emp} not found")
    
    JOB_TYPE_RESTRICTIONS[job_type] = employees
    _save_restrictions_to_file()  # Persist changes
    return True

def remove_job_type_restriction(job_type):
    """Remove restrictions for a job type (making it available to all employees)"""
    
    if job_type in JOB_TYPE_RESTRICTIONS:
        del JOB_TYPE_RESTRICTIONS[job_type]
        _save_restrictions_to_file()  # Persist changes
        return True
    return False

def get_job_type_restrictions(job_type=None):
    """Get restrictions for a specific job type or all restrictions"""
    if job_type:
        return JOB_TYPE_RESTRICTIONS.get(job_type, "all")
    return JOB_TYPE_RESTRICTIONS.copy()

def list_restricted_job_types():
    """Get list of all job types that have restrictions"""
    return list(JOB_TYPE_RESTRICTIONS.keys())

def get_employees_allowed_for_job_type(job_type):
    """Get list of employees allowed to perform a specific job type"""
    
    if job_type in JOB_TYPE_RESTRICTIONS:
        restrictions = JOB_TYPE_RESTRICTIONS[job_type]
        if restrictions == "all":
            return list(EMPLOYEES.keys())
        elif isinstance(restrictions, list):
            return restrictions.copy()
    
    # No restrictions - all employees who have this job type in their rates
    allowed_employees = []
    for emp_name, rates in EMPLOYEES.items():
        if job_type in rates or job_type == "expense":
            allowed_employees.append(emp_name)
    return allowed_employees
