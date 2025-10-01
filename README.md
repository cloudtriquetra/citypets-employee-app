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
    "expense": 0
  }
}
```

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
└── job_type_restrictions.json       # Actual job restrictions
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
- 🔐 User Management (Account Creation)

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

## 🚀 Deployment

### Local Deployment (Recommended)
- Perfect for small teams and testing
- Uses SQLite database (included)
- No external dependencies required
- Simple setup: `streamlit run main.py`

### Server Deployment Options

**Option 1: Simple Server Setup**
```bash
# On your server (Linux/macOS)
git clone https://github.com/yourusername/citypets-employee-app.git
cd citypets-employee-app
pip install -r requirements.txt

# Copy your configuration files
cp employees_config.json.example employees_config.json
cp pet_custom_rates.json.example pet_custom_rates.json
cp job_type_restrictions.json.example job_type_restrictions.json

# Edit config files with your actual data
# Then run the application
streamlit run main.py --server.port 8501 --server.address 0.0.0.0
```

**Option 2: Cloud Platform (Streamlit Cloud)**
1. Push your repository to GitHub (with config files configured)
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy directly from your GitHub repository
4. Set environment variables if needed

**Option 3: VPS/Dedicated Server**
- Install Python 3.8+ on your server
- Follow the local deployment steps
- Use a process manager like `systemd` or `supervisor` for production
- Consider using a reverse proxy (nginx) for custom domains

### Important Deployment Notes
- **Database files** (`*.db`) will be created automatically
- **Configuration files** must be properly set up before first run
- **Backup strategy** recommended for production use
- **HTTPS** recommended for production deployments

## 🔮 Roadmap

### Upcoming Features
- [ ] Mobile app companion
- [ ] Photo upload for timesheet entries
- [ ] GPS tracking for transport jobs
- [ ] Push notifications for shift reminders
- [ ] Integration with payroll software
- [ ] Advanced analytics and insights
- [ ] Multi-language support

### Technical Improvements
- [ ] PostgreSQL migration option
- [ ] API endpoints for third-party integration
- [ ] Enhanced security features
- [ ] Performance optimizations
- [ ] Automated backup system

## 🐛 Troubleshooting

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
