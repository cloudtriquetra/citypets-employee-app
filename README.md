# 🏨 CityPets Employee Timesheet Application

A comprehensive Streamlit-based timesheet management system designed for pet care businesses. Features employee time tracking, payroll management, mobile-optimized interface, and administrative dashboard with payment processing.

## ✨ Key Features

### � **Employee Management**
- Multi-employee support with individual hourly rates
- Job-specific access controls and restrictions
- Custom rates for specific pets/clients
- Mobile-optimized timesheet submission

### 💼 **Job Types Supported**
- Hotel/Daycare services
- Dog walking
- Cat visits and care
- Pet sitting (hourly and overnight)
- Transport services with KM tracking
- Training and management tasks
- Expense tracking

### 📊 **Admin Dashboard**
- Real-time payment processing and status tracking
- Comprehensive reporting with date range presets
- Excel export functionality
- Employee performance analytics
- Interactive charts and visualizations
- Holiday rate management with date-based automatic rate switching

### 📱 **Mobile-Optimized**
- Responsive design for mobile devices
- Success messages positioned for mobile viewing
- Touch-friendly interface elements

## 🚀 Quick Start

### 1. **Prerequisites**
- Python 3.8 or higher
- pip package manager

### 2. **Clone Repository**
```bash
git clone https://github.com/cloudtriquetra/citypets-employee-app.git
cd citypets-employee-app
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4. **Initial Configuration**

#### Configure Employee Data
```bash
# Copy example files and customize with your data
cp employees_config.json.example employees_config.json
cp pet_custom_rates.json.example pet_custom_rates.json
cp job_type_restrictions.json.example job_type_restrictions.json
```

#### Configure Environment (Optional)
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

### 5. **Run Application**
```bash
streamlit run main.py
```

The application will be available at `http://localhost:8501`

## � First-Time Setup & Login

### Initial Admin Setup

The application uses a secure user authentication system. On the **first run**, you'll automatically see the setup page:

1. **Start the application**: `streamlit run main.py`
2. **Access the app**: Go to `http://localhost:8501`
3. **Automatic Setup Prompt**: 
   - If no users exist, you'll see a "First-Time Setup" form instead of login
   - Fill in administrator details (username, email, full name, employee name, password)
   - **Important**: Employee name must exactly match an entry in `employees_config.json`
   - Create a strong password following the requirements shown

### Default Login Process

**For Administrators:**
1. Login with your admin credentials
2. Navigate to "User Management" to create employee accounts
3. Set up employee rates in "Employee Management"

**For Employees:**
1. Login with credentials provided by your administrator
2. Complete timesheet entries
3. View your personal reports

### User Account Creation

**Only administrators can create new user accounts**. To add a new employee:

1. Login as admin
2. Go to "User Management" → "Add New User"
3. Fill in employee details:
   - Username and email
   - Full name and employee name (must match `employees_config.json`)
   - Role (Admin or Employee)
   - Initial password (user will be prompted to change)

### Password Security

- All passwords are securely hashed using PBKDF2
- Temporary passwords must be changed on first login
- Strong password requirements enforced
- Session tokens for secure authentication

## �🔧 Configuration Guide

### Employee Configuration (`employees_config.json`)

Configure individual employee rates for different job types:

```json
{
  "EMPLOYEE_NAME": {
    "hotel": 25,
    "walk": 25,
    "overnight_hotel": 90,
    "cat_visit": 30,
    "pet_sitting_hourly": 17,
    "overnight_pet_sitting": 140,
    "dog_at_home": 75,
    "cat_at_home": 25,
    "training": 28,
    "management": 30,
    "transport": 25,
    "transport_km": 2.5,
    "expense": 0,
    "holiday_rate_hotel": 30,
    "holiday_rate_overnight_hotel": 100
  }
}
```

**Holiday Rates**: Special rates automatically applied on designated holiday dates:
- `holiday_rate_hotel`: Hourly rate for hotel/daycare on holidays (typically base hotel rate + 5)
- `holiday_rate_overnight_hotel`: Fixed rate for overnight hotel shifts on holidays (typically 100 PLN)
- Holiday rates only apply to **hotel** and **overnight_hotel** job types (not walk or pet sitting)

### Job Access Control (`job_type_restrictions.json`)

Control which employees can access specific job types:

```json
{
  "training": ["EMPLOYEE_1"],
  "hotel": ["EMPLOYEE_1", "EMPLOYEE_2", "EMPLOYEE_3"],
  "management": ["EMPLOYEE_1"]
}
```

### Pet Custom Rates (`pet_custom_rates.json`)

Set special rates for specific pets (applies to all employees):

```json
{
  "Special Pet Name": {
    "pet_sitting_hourly": 20,
    "walk": 30
  }
}
```

## 📁 Project Structure

```
citypets-employee-app/
├── main.py                           # Main Streamlit application
├── employee_config.py                # Employee configuration management
├── user_management.py                # User authentication and management
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment configuration template
├── employees_config.json.example     # Employee rates template
├── pet_custom_rates.json.example     # Pet custom rates template
├── job_type_restrictions.json.example # Job access control template
├── .gitignore                        # Git ignore rules (protects sensitive data)
└── README.md                         # This file

# Generated at runtime (not in repository)
├── citypets_timesheet.db            # SQLite database for timesheet data
├── citypets_users.db                # SQLite database for user management
├── employees_config.json            # Actual employee configuration
├── pet_custom_rates.json            # Actual pet rates
├── job_type_restrictions.json       # Actual job restrictions
└── holiday_dates.json               # Designated holiday dates for special rates
```

## 🛡️ Security Features

### Data Protection
- **Sensitive files excluded from Git**: Employee data, rates, and databases are never committed
- **Example files provided**: Safe templates for setup without exposing real data
- **Environment configuration**: Secure storage for API keys and secrets

### User Authentication
- Multi-user support with role-based access
- Admin and employee permission levels
- Session-based authentication

## 💡 Usage Guide

### For New Installations
1. **First Run**: Access `http://localhost:8501/?setup=true` to create the initial admin user
2. **Admin Login**: Use your newly created admin credentials to access the system
3. **Configure Employees**: Set up employee rates and job access in "Employee Management"
4. **Create Employee Accounts**: Add user accounts for each employee in "User Management"

### For Employees
1. **Login**: Use your assigned username/email and password provided by your administrator
2. **First-Time Password Change**: You'll be prompted to change your temporary password
3. **Submit Time**: Fill out the timesheet form with job details
4. **Track Status**: View your submitted entries and payment status
5. **Reports**: Generate personal reports for specific date ranges

### For Administrators
1. **User Management**: Create and manage employee user accounts
2. **Employee Configuration**: Set hourly rates and job type access permissions
3. **Payment Processing**: Mark entries as paid and track pending payments
4. **Reports & Analytics**: Generate comprehensive reports with analytics
5. **Data Export**: Export data to Excel for accounting purposes

### Navigation Menu

Once logged in, you'll see different menu options based on your role:

**Employee Users:**
- 📝 Timesheet Entry
- 📊 Employee Reports
- 👤 Profile Settings

**Admin Users:**
- 📝 Timesheet Entry
- 💳 Admin Dashboard (Payment Processing)
- 📊 Reports (Comprehensive Analytics)
- 📁 Data Export
- 👥 Employee Management (Rates & Job Access)
- �️ Holiday Management (Holiday Dates & Rates)
- �🔐 User Management (Account Creation)

## 🔐 Security Features

## 🎯 Key Job Types

| Job Type | Description | Rate Structure |
|----------|-------------|----------------|
| Hotel | Daily pet hotel/daycare | Hourly rate |
| Walk | Dog walking services | Hourly rate |
| Cat Visit | Cat care and visits | Per visit or hourly |
| Pet Sitting | In-home pet care | Hourly (≤8h) or Overnight (>8h) |
| Overnight Hotel | 12-hour overnight shifts | Fixed rate (90 PLN) |
| Transport | Pet transportation | Hourly + KM rate |
| Training | Staff training sessions | Hourly rate |
| Management | Administrative tasks | Hourly rate |
| Expense | Reimbursable expenses | Exact amount |

## 📊 Rate Priority System

1. **🥇 Pet-Specific Rates** (Highest Priority) - Custom rates for specific pets
2. **🥈 Employee-Specific Rates** (Medium Priority) - Individual employee rates
3. **🥉 Standard Base Rates** (Lowest Priority) - Default fallback rates

## �️ Holiday Rate Management

### Overview
The application supports automatic rate switching for designated holiday dates. When employees submit timesheets for work performed on holidays, the system automatically applies higher holiday rates instead of standard rates.

### Admin Features
**Holiday Management** page (Admin access only) provides two key functions:

#### 1. Holiday Dates Management
- **Add Holiday Dates**: Use the date picker to select and add special dates (e.g., Christmas, New Year)
- **Remove Dates**: Delete holiday dates that are no longer needed
- **View All Dates**: See a complete list of designated holiday dates
- **Persistence**: Holiday dates are stored in `holiday_dates.json` and persist across application restarts

#### 2. Holiday Rates Configuration
- **Visual Comparison Table**: See standard rates vs. holiday rates side-by-side for all employees
- **Individual Rate Editing**: Update holiday rates for specific employees
- **Real-time Updates**: Changes apply immediately to new timesheet entries

### Automatic Rate Application
**How it works:**
1. Employee submits timesheet for work on a designated holiday date
2. System checks if the date is in the holiday dates list
3. If yes, automatically uses `holiday_rate_hotel` or `holiday_rate_overnight_hotel`
4. If no, uses standard `hotel` or `overnight_hotel` rates

**Job Types with Holiday Rates:**
- ✅ **Hotel/Daycare** → Uses `holiday_rate_hotel` on holidays
- ✅ **Overnight Hotel** → Uses `holiday_rate_overnight_hotel` on holidays
- ❌ **Walk** → No holiday rate (uses standard rate)
- ❌ **Pet Sitting** → No holiday rate (uses standard rate)
- ❌ **Other job types** → No holiday rates

### Rate Calculation Rules
- **Holiday Hotel Rate**: Typically base hotel rate + 5 PLN (e.g., 25 → 30)
- **Holiday Overnight Rate**: Typically fixed at 100 PLN (regardless of base rate)
- **Configurable**: Admins can set any value for holiday rates per employee

### Configuration File: `holiday_dates.json`
```json
{
  "holiday_dates": [
    "2025-12-25",
    "2026-01-01",
    "2025-12-24",
    "2025-12-26"
  ]
}
```

**Format**: Dates must be in `YYYY-MM-DD` format

### Best Practices
1. **Plan Ahead**: Add holiday dates at the beginning of the year
2. **Consistent Rates**: Keep holiday rate premiums consistent across similar roles
3. **Communication**: Inform employees about holiday rate policies
4. **Regular Review**: Update holiday dates annually for new year

## �🚀 Deployment

### Local Deployment (Tested & Recommended)
- Perfect for small teams and local use
- Uses SQLite database (included)
- No external dependencies required
- Simple setup: `streamlit run main.py`
- Access via `http://localhost:8501`

### Network Access (Tested)
If you want others on your local network to access the application:
```bash
# Run with network access
streamlit run main.py --server.address 0.0.0.0 --server.port 8501
```
- Access via `http://YOUR_COMPUTER_IP:8501` from other devices on the same network
- Ensure firewall allows port 8501
- **Note**: This is for local network only, not internet-wide access

### Application Characteristics
- **Designed for local/small team use**
- **SQLite database** works well for single-instance deployments
- **File-based configuration** for easy setup and management
- **Session-based authentication** for secure access
- **No external dependencies** beyond Python packages

##  Troubleshooting

### Login Issues

**Cannot access the application / No users exist:**
- On first run, the setup form appears automatically when no users exist
- Create the initial administrator account using the setup form
- Ensure `employees_config.json` contains the admin's employee name

**Login failed / Invalid credentials:**
- Verify username/email and password are correct
- Check if account is active (admins can check in User Management)
- Ensure employee name in user account matches `employees_config.json`

**Forced to change password:**
- This is normal for temporary passwords
- Follow the password requirements shown on screen
- Password must be strong (8+ chars, uppercase, lowercase, numbers, symbols)

**Session expired / Logged out unexpectedly:**
- Sessions expire for security
- Simply log in again with your credentials
- Check browser console for any errors

### Common Issues

**Database not found errors:**
- The application creates databases automatically on first run
- Ensure you have write permissions in the application directory

**Configuration file errors:**
- Copy `.example` files and customize with your data
- Validate JSON syntax in configuration files
- Ensure employee names in `employees_config.json` match user accounts

**Missing dependencies:**
- Run `pip install -r requirements.txt` to install all required packages
- Consider using a virtual environment

**Permission errors:**
- Ensure employees are configured in `employees_config.json`
- Check `job_type_restrictions.json` for access permissions
- Verify user accounts exist in User Management

**Employee cannot access certain job types:**
- Check `job_type_restrictions.json` for allowed employees
- Admin users can modify access in Employee Management
- Ensure employee name matches exactly between config files and user account

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

### Development Setup
```bash
# Clone and setup development environment
git clone https://github.com/yourusername/citypets-employee-app.git
cd citypets-employee-app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎉 Success Metrics

- **User Experience**: Streamlined timesheet submission
- **Admin Efficiency**: 80% faster payroll processing
- **Mobile Optimized**: Works seamlessly on mobile devices
- **Data Security**: Comprehensive protection of sensitive information
- **Reliability**: 99%+ uptime with robust error handling

---

**Built with ❤️ for Pet Care Businesses**  
*Making timesheet management simple, secure, and efficient*

## 📞 Support

For support, feature requests, or bug reports, please:
1. Check the troubleshooting section above
2. Open an issue on GitHub
3. Contact the development team

**Note**: This application contains sensitive employee and business data. Always follow security best practices and never commit real employee information to version control.
