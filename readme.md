# 🚀 Abhay Singh Portfolio

A modern and responsive personal portfolio website built using **Django, Python, HTML, CSS, JavaScript, and Bootstrap**. This portfolio showcases my projects, technical skills, education, internships, certifications, and achievements in **Data Analytics, Data Science, Machine Learning, Deep Learning, and Web Development**.

---

## 🌟 Features

* Responsive Modern UI Design
* Personal Introduction & About Section
* Skills & Technologies Showcase
* Project Portfolio with Detailed Project Pages
* Contact Form with Email Integration
* Downloadable Resume/CV
* GitHub & LinkedIn Integration
* Mobile Friendly Navigation
* Professional Portfolio Layout

---

## 🛠️ Technologies Used

### Programming Languages

* Python
* SQL
* JavaScript

### Frontend

* HTML5
* CSS3
* Bootstrap
* JavaScript

### Backend

* Django

### Data Analytics & Machine Learning

* Pandas
* NumPy
* Matplotlib
* Seaborn
* Scikit-Learn
* TensorFlow
* Keras

### Database

* SQLite
* MySQL

### Tools

* Git
* GitHub
* VS Code
* Jupyter Notebook
* Power BI

---

## 📂 Website Sections

### 🏠 Home

Introduction, profile information, social links, and resume download.

### 👨‍💻 About

Education, internships, achievements, and professional background.

### 🛠️ Skills

Technical skills, frameworks, libraries, and tools.

### 📁 Projects

Machine Learning, Data Analytics, Django, Frontend, Dashboard, and Python projects.

### 📞 Contact

Contact form with email functionality.

---

## 📌 Featured Projects

* Car Marketplace & Management System
* Netflix AI Recommendation System
* Django Chatbot Web Application
* Heart Disease Prediction System
* Employee Attrition Prediction
* Loan Approval Prediction
* Iris Flower Classification
* Customer Purchase Prediction
* Weather Prediction System
* Placement Prediction System

---

## 🎓 Education

**B.Tech - Computer Science Engineering**
SR Institute of Management & Technology, Lucknow

---

## 💼 Internship Experience

### Softpro India

Data Science Intern

### Unified Mentor

Data Science Intern

---

## 📊 Areas of Interest

* Data Analytics
* Data Science
* Machine Learning
* Deep Learning
* Artificial Intelligence
* Django Development
* Data Visualization
* Business Intelligence
* Recommendation Systems

---

## 🔗 Connect With Me

### GitHub

https://github.com/abhaysingh-coder

### LinkedIn

https://www.linkedin.com/in/abhay-singh-581423257

### Email

[srinetabhaysingh14@gmail.com](mailto:srinetabhaysingh14@gmail.com)

### Phone

+91 7985397219

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/abhaysingh-coder/Portfolio.git
```

Move into the project directory:

```bash
cd Portfolio
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Create your admin account:

```bash
python manage.py createsuperuser
```

Start server:

```bash
python manage.py runserver
```

Open browser:

```text
http://127.0.0.1:8000/
```

## 🔐 Portfolio Admin

Sign in at `http://127.0.0.1:8000/admins` with the staff account created above.
The admin dashboard lets you add, edit, and remove projects and upload the
downloadable CV as a PDF (up to 5 MB). The Django administration site is also
available at `/admin/`.

The repository includes `render.yaml` with the Render build/start commands and
production environment settings. Create a Render PostgreSQL database in the
same region as the web service. In the database page, copy its **Internal
Database URL** and set it as `DATABASE_URL` in the web service's Environment
settings. If creating a new service from the Blueprint, Render prompts for the
`DATABASE_URL` value on its initial sync. For an existing service, add it
manually. Save the setting and redeploy; the application deliberately refuses
to use SQLite in production.

For manual web-service configuration, use:

* Build command: `./build.sh`
* Start command: `gunicorn Portfolio.wsgi:application`

The build script collects static files and then runs migrations as a separate
command. `collectstatic` itself does not run migrations. The project enables
HTTPS redirects, secure cookies, and HSTS when debug mode is disabled. If your
host uses ephemeral app storage, attach a persistent disk and set
`PROJECTS_CSV_PATH` and `PORTFOLIO_CV_PATH` to files on that disk so admin
changes survive restarts and deployments. Configure these Render service
environment variables:

* `SECRET_KEY`: a unique, randomly generated secret.
* `DEBUG=False`.
* `DATABASE_URL`: the Internal Database URL from the Render PostgreSQL database.
* `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD`: optional
  credentials used by the build script after migrations to create the initial
  deployment superuser. If the username already exists, its credentials and
  permissions are left unchanged; an existing non-superuser with that username
  causes the build to stop with a safe error. Rotate or remove these variables
  after provisioning if they are no longer needed.
* `RENDER`: set automatically by Render; this enables the production defaults
  and requires `DATABASE_URL`.
* `ALLOWED_HOSTS`: optional comma-separated hostnames; Render's
  `RENDER_EXTERNAL_HOSTNAME` is included automatically.
* `EMAIL_PERSONAL_USER` and `EMAIL_PERSONAL_PASSWORD`.
* `EMAIL_PORTFOLIO_USER` and `EMAIL_PORTFOLIO_PASSWORD`.
* `PROJECTS_CSV_PATH` and `PORTFOLIO_CV_PATH`: paths on the mounted persistent
  disk, for example `/var/data/Data.csv` and `/var/data/Abhay_Singh_CV.pdf`.

Copy the current `Data.csv` and CV PDF to those disk paths once before switching
the service to them. Back up the disk and database regularly. The build script
collects static assets, applies migrations, and then runs the idempotent
deployment-superuser command. Set both superuser variables in the Render
environment before deployment to create the account; the command does not
overwrite an existing account.

---

## 📄 License

This project is developed for educational and portfolio purposes.

---

⭐ If you like this project, don't forget to star the repository.
