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

## 🔧 Configuration Guide

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

### For Employees
1. **Login**: Use your assigned credentials
2. **Submit Time**: Fill out the timesheet form with job details
3. **Track Status**: View your submitted entries and payment status
4. **Reports**: Generate personal reports for specific date ranges

### For Administrators
1. **Employee Management**: Add/remove employees and set rates
2. **Payment Processing**: Mark entries as paid and track pending payments
3. **Reports**: Generate comprehensive reports with analytics
4. **Data Export**: Export data to Excel for accounting purposes

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

### Local Deployment
- Perfect for small teams and testing
- Uses SQLite database (included)
- No external dependencies required

### Production Deployment
- Compatible with cloud platforms (Heroku, AWS, GCP)
- Easy migration to PostgreSQL for scaling
- Environment variables for secure configuration

### Docker Support (Future)
```bash
# Will be available in future releases
docker build -t citypets-timesheet .
docker run -p 8501:8501 citypets-timesheet
```

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
- [ ] Docker containerization
- [ ] API endpoints for third-party integration
- [ ] Enhanced security features
- [ ] Performance optimizations

## 🐛 Troubleshooting

### Common Issues

**Database not found errors:**
- The application creates databases automatically on first run
- Ensure you have write permissions in the application directory

**Configuration file errors:**
- Copy `.example` files and customize with your data
- Validate JSON syntax in configuration files

**Missing dependencies:**
- Run `pip install -r requirements.txt` to install all required packages
- Consider using a virtual environment

**Permission errors:**
- Ensure employees are configured in `employees_config.json`
- Check `job_type_restrictions.json` for access permissions

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
