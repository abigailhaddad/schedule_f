import json
import random
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker
fake = Faker()
Faker.seed(42)  # For reproducible results

# Number of records to generate
NUM_RECORDS = 200

# Define possible values for categorical fields
departments = ['Engineering', 'Marketing', 'Sales', 'Finance', 'Human Resources', 
               'Product Management', 'Customer Support', 'Research & Development',
               'Operations', 'Legal', 'Information Technology']

locations = ['New York', 'San Francisco', 'Chicago', 'Austin', 'Boston', 'Seattle', 
             'Denver', 'Los Angeles', 'Portland', 'Remote', 'Atlanta', 'Dallas',
             'Phoenix', 'Miami', 'Minneapolis', 'Toronto', 'London', 'Berlin', 'Sydney']

statuses = [
    ('Active', 'bg-success'),
    ('On Leave', 'bg-warning'),
    ('Contract', 'bg-info'),
    ('Probation', 'bg-secondary'),
    ('Terminated', 'bg-danger')
]

seniority_levels = ['Junior', 'Mid-level', 'Senior', 'Lead', 'Principal', 'Director', 'VP', 'C-Suite']

# Job titles by department
job_titles = {
    'Engineering': ['Software Engineer', 'Frontend Developer', 'Backend Developer', 'DevOps Engineer', 
                    'QA Engineer', 'Security Engineer', 'Data Engineer', 'ML Engineer'],
    'Marketing': ['Marketing Specialist', 'Content Writer', 'SEO Specialist', 'Marketing Analyst', 
                  'Social Media Manager', 'Brand Strategist', 'Growth Marketer'],
    'Sales': ['Sales Representative', 'Account Executive', 'Sales Manager', 'Business Development Rep',
              'Sales Operations Analyst', 'Sales Director', 'Customer Success Manager'],
    'Finance': ['Financial Analyst', 'Accountant', 'Controller', 'Tax Specialist', 'Auditor',
                'Financial Planner', 'Treasurer', 'Payroll Specialist'],
    'Human Resources': ['HR Specialist', 'Recruiter', 'HR Business Partner', 'Talent Acquisition Manager',
                        'Benefits Administrator', 'Employee Relations Manager', 'Diversity & Inclusion Specialist'],
    'Product Management': ['Product Manager', 'Product Owner', 'UX Designer', 'UI Designer', 
                           'Product Marketing Manager', 'Product Analyst'],
    'Customer Support': ['Customer Support Representative', 'Technical Support Specialist', 'Support Manager',
                         'Customer Experience Specialist', 'Customer Success Advocate'],
    'Research & Development': ['Research Scientist', 'R&D Engineer', 'Innovation Specialist', 
                               'Research Analyst', 'Lab Technician'],
    'Operations': ['Operations Manager', 'Project Manager', 'Business Analyst', 'Operations Analyst',
                   'Process Improvement Specialist', 'Supply Chain Manager'],
    'Legal': ['Corporate Counsel', 'Legal Assistant', 'Compliance Officer', 'Contract Manager', 
              'Patent Attorney', 'Paralegal'],
    'Information Technology': ['IT Support Specialist', 'Network Administrator', 'Systems Analyst',
                              'Database Administrator', 'IT Manager', 'Cybersecurity Analyst']
}

# Performance ratings
performance_ratings = ['Exceptional', 'Exceeds Expectations', 'Meets Expectations', 'Needs Improvement', 'Unsatisfactory']

# Performance history templates
performance_templates = [
    "Consistently {rating}. {employee} has shown excellent leadership in {project_type} projects.",
    "{employee} {rating} in quarterly reviews. Strong skills in {skill}, though could improve in {improvement_area}.",
    "Performance has been {rating}. Successfully completed {project_count} major projects this year.",
    "{rating} performance overall. {strength}, but {weakness}.",
    "Recent performance: {rating}. {employee} demonstrates {quality} and {quality2}."
]

# Project templates
project_templates = [
    "Currently leading the {project_name} initiative, which aims to {project_goal}.",
    "Recently completed work on {project_name}, resulting in {project_outcome}.",
    "Assigned to {project_name} team, focusing on {project_focus}.",
    "Contributing to cross-departmental {project_name} project, collaborating with {collaborating_dept}.",
    "Spearheading the {project_name} with expected completion in {timeline}."
]

# Comprehensive skills list - expanded for better variety
all_skills = [
    # Technical Skills
    'Python', 'JavaScript', 'React', 'Angular', 'Vue.js', 'Node.js', 'Express.js', 'Django', 'Flask',
    'Java', 'Spring', 'C++', 'C#', '.NET', 'PHP', 'Laravel', 'Ruby', 'Ruby on Rails', 'Go',
    
    # Cloud & Infrastructure
    'AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'Terraform', 'Jenkins', 'GitLab CI',
    'CircleCI', 'Travis CI', 'Ansible', 'Puppet', 'Chef',
    
    # Databases
    'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Cassandra', 'Oracle',
    'SQL Server', 'DynamoDB',
    
    # Data & Analytics
    'Data Analysis', 'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Scikit-learn',
    'Pandas', 'NumPy', 'R', 'Tableau', 'Power BI', 'Spark', 'Hadoop', 'Apache Airflow',
    
    # Design & Frontend
    'UI/UX Design', 'Photoshop', 'Illustrator', 'Sketch', 'Figma', 'InVision', 'HTML', 'CSS',
    'Sass', 'Bootstrap', 'Tailwind CSS', 'Material Design',
    
    # Project Management & Methodology
    'Agile', 'Scrum', 'Kanban', 'Jira', 'Confluence', 'Monday.com', 'Asana', 'Trello',
    'Project Management', 'Team Leadership', 'Sprint Planning',
    
    # Business & Communication
    'Business Analysis', 'Strategic Planning', 'Public Speaking', 'Technical Writing',
    'Content Creation', 'SEO', 'SEM', 'Google Analytics', 'A/B Testing', 'Market Research',
    
    # Soft Skills
    'Leadership', 'Communication', 'Problem Solving', 'Team Collaboration', 'Time Management',
    'Critical Thinking', 'Adaptability', 'Creativity', 'Conflict Resolution', 'Mentoring',
    'Customer Service', 'Negotiation', 'Presentation Skills', 'Change Management',
    
    # Security
    'Information Security', 'Penetration Testing', 'Cybersecurity', 'Network Security',
    'Compliance', 'GDPR', 'SOX', 'HIPAA', 'ISO 27001',
    
    # Sales & Marketing
    'Salesforce', 'HubSpot', 'Lead Generation', 'Customer Acquisition', 'Sales Funnel Optimization',
    'Digital Marketing', 'Social Media Marketing', 'Email Marketing', 'PPC', 'Conversion Optimization'
]

# Skills by department to make it more realistic
department_skills = {
    'Engineering': ['Python', 'JavaScript', 'React', 'Node.js', 'Docker', 'Kubernetes', 'AWS', 'Git', 'SQL', 'MongoDB', 'CI/CD', 'Agile', 'TensorFlow', 'Machine Learning'],
    'Marketing': ['Google Analytics', 'SEO', 'SEM', 'Content Creation', 'Social Media Marketing', 'Email Marketing', 'A/B Testing', 'Photoshop', 'Canva', 'HubSpot', 'WordPress', 'Copywriting'],
    'Sales': ['Salesforce', 'Customer Acquisition', 'Lead Generation', 'Negotiation', 'CRM', 'Sales Funnel Optimization', 'Prospecting', 'Presentation Skills', 'Account Management', 'Territory Management'],
    'Finance': ['Excel', 'SQL', 'Financial Modeling', 'QuickBooks', 'SAP', 'Power BI', 'Tableau', 'Risk Management', 'Budget Planning', 'Financial Analysis', 'Accounting', 'Auditing'],
    'Human Resources': ['HRIS', 'Workday', 'BambooHR', 'Recruiting', 'Performance Management', 'Compensation Analysis', 'Employee Relations', 'Training Development', 'Diversity & Inclusion', 'Change Management'],
    'Product Management': ['Jira', 'Confluence', 'User Research', 'Roadmap Planning', 'A/B Testing', 'Analytics', 'Wireframing', 'Agile', 'Scrum', 'Product Strategy', 'Market Research'],
    'Customer Support': ['Zendesk', 'Freshdesk', 'Intercom', 'Customer Service', 'Technical Support', 'Troubleshooting', 'Empathy', 'Communication', 'Patience', 'Product Knowledge'],
    'Research & Development': ['R', 'Python', 'Statistics', 'Hypothesis Testing', 'Research Design', 'Data Analysis', 'SPSS', 'SAS', 'Laboratory Management', 'Patent Research'],
    'Operations': ['Process Improvement', 'Six Sigma', 'Lean', 'Project Management', 'Supply Chain Management', 'Vendor Management', 'Quality Assurance', 'Continuous Improvement'],
    'Legal': ['Contract Review', 'Legal Research', 'Intellectual Property', 'Compliance', 'Risk Assessment', 'Litigation Support', 'Legal Writing', 'Negotiation'],
    'Information Technology': ['Network Administration', 'System Administration', 'Active Directory', 'Windows Server', 'Linux', 'VMware', 'Help Desk', 'Asset Management', 'Backup Solutions']
}

# Generate employees data
employees = []

for i in range(1, NUM_RECORDS + 1):
    # Basic info
    employee_id = f"EMP{i:05d}"
    first_name = fake.first_name()
    last_name = fake.last_name()
    name = f"{first_name} {last_name}"
    email = f"{first_name.lower()}.{last_name.lower()}@example.com"
    
    # Department and role
    department = random.choice(departments)
    base_title = random.choice(job_titles[department])
    seniority = random.choice(seniority_levels)
    title = f"{seniority} {base_title}" if random.random() > 0.3 else base_title
    
    # Location and status
    location = random.choice(locations)
    status, status_class = random.choice(statuses)
    
    # Employment details
    start_date = fake.date_between(start_date='-10y', end_date='today')
    salary_base = random.randint(50000, 180000)
    salary_factor = {'Junior': 0.7, 'Mid-level': 1.0, 'Senior': 1.3, 'Lead': 1.5, 
                     'Principal': 1.8, 'Director': 2.2, 'VP': 2.5, 'C-Suite': 3.5}
    salary_multiplier = salary_factor.get(seniority, 1.0)
    salary = int(salary_base * salary_multiplier)
    
    # Generate employee skills - mix of department-specific and general skills
    dept_skills = department_skills.get(department, [])
    general_skills = [skill for skill in all_skills if skill not in dept_skills]
    
    # Pick 3-5 department skills and 1-3 general skills
    dept_skill_count = random.randint(3, min(5, len(dept_skills)))
    general_skill_count = random.randint(1, 3)
    
    selected_dept_skills = random.sample(dept_skills, k=dept_skill_count)
    selected_general_skills = random.sample(general_skills, k=general_skill_count)
    
    # Combine and format as comma-separated string
    all_selected_skills = selected_dept_skills + selected_general_skills
    skills_str = ", ".join(sorted(all_selected_skills))
    
    # Performance data
    last_review_date = fake.date_between(start_date='-1y', end_date='today')
    performance = random.choice(performance_ratings)
    
    # Create detailed performance notes
    template = random.choice(performance_templates)
    performance_note = template.format(
        rating=performance.lower(),
        employee=first_name,
        project_type=random.choice(['client', 'internal', 'strategic', 'technical']),
        skill=random.choice(all_selected_skills),
        improvement_area=random.choice(['communication', 'time management', 'delegation', 'strategic thinking']),
        project_count=random.randint(2, 8),
        strength=f"Excels at {random.choice(all_selected_skills)}",
        weakness=f"needs development in {random.choice(['communication', 'leadership', 'technical expertise', 'strategic thinking'])}",
        quality=random.choice(['initiative', 'attention to detail', 'strategic thinking', 'technical expertise']),
        quality2=random.choice(['reliability', 'innovation', 'commitment', 'analytical thinking'])
    )
    
    # Project information
    current_project = random.choice(project_templates).format(
        project_name=fake.bs().title(),
        project_goal=fake.catch_phrase(),
        project_outcome=f"a {random.randint(10, 50)}% increase in {random.choice(['efficiency', 'revenue', 'user engagement', 'customer satisfaction'])}",
        project_focus=random.choice(['UI/UX improvements', 'performance optimization', 'new feature development', 'security enhancements', 'process automation']),
        collaborating_dept=random.choice([d for d in departments if d != department]),
        timeline=f"{random.randint(1, 6)} months"
    )
    
    # Notes field with lorem ipsum
    notes_paragraphs = random.randint(1, 3)
    notes = " ".join([fake.paragraph(nb_sentences=random.randint(3, 6)) for _ in range(notes_paragraphs)])
    
    # Create employee record
    employee = {
        "id": employee_id,
        "name": name,
        "email": email,
        "department": department,
        "title": title,
        "salary": salary,
        "location": location,
        "joined": start_date.strftime("%Y-%m-%d"),
        "status": status,
        "status_class": status_class,
        "skills": skills_str,  # Added skills field as comma-separated string
        "notes": notes
    }
    
    employees.append(employee)

# Save the data to data.json
with open('data.json', 'w') as f:
    json.dump(employees, f, indent=2)

print(f"Generated {NUM_RECORDS} employee records with skills field and saved to data.json")
print(f"Sample skills from first employee: {employees[0]['skills']}")