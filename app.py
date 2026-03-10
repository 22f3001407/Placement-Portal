from flask import Flask, render_template, request,  redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = "mysecretkey123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///placement.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# USERS TABLE
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationship with Student
    student_profile = db.relationship("Student",back_populates="user",uselist=False)


# STUDENT PROFILE
class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    college_name = db.Column(db.String(150)) 
    branch = db.Column(db.String(50))
    cgpa = db.Column(db.Float)
    skills = db.Column(db.String(300)) 
    resume_link = db.Column(db.String(200))
    is_blacklisted = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # reverse relation
    user = db.relationship("User",back_populates="student_profile")

    # relationship with applications
    applications = db.relationship("Application",back_populates="student")


# COMPANY
class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    company_name = db.Column(db.String(100))
    industry = db.Column(db.String(100))
    location = db.Column(db.String(100))
    website = db.Column(db.String(200))
    company_size = db.Column(db.String(50))
    hr_name = db.Column(db.String(100))
    hr_email = db.Column(db.String(120))
    description = db.Column(db.Text)
    is_blacklisted = db.Column(db.Boolean, default=False)

    jobs = db.relationship("Job",back_populates="company")


# JOBS
class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100))
    skills = db.Column(db.String(200))
    experience = db.Column(db.String(50))
    salary = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"))

    company = db.relationship("Company",back_populates="jobs")

    applications = db.relationship("Application",back_populates="job")


# APPLICATIONS
class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), default="Applied")

    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("Student",back_populates="applications")

    job = db.relationship("Job",back_populates="applications")


                 #ROUTES
                
@app.route("/")
def index():
    return render_template('index.html')


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user:
            return "No user found"
        
        if user.password != password:
            return "Wrong password"
        
        session['role'] = user.role
        session['email'] = user.email
        session['id'] = user.id
        if user.role == "company" and not user.is_approved:
             return render_template("company_pending.html", user=user)

        if user.role == "admin":
            return redirect("/admin_dashboard")
        
        elif user.role == "company":
            return redirect('/company_dashboard')
        
        else:
            return redirect("/student_dashboard")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        approve_status = False
        if role == "student":
            approve_status = True

        if role == "admin":
            return "Admin cannot be registered"

        
        if User.query.filter_by(email=email).first():
            return "Email already registered"

        # save user in db
        user = User(
            name=name,
            email=email,
            password=password,
            role=role,
            is_approved= False if role == "company" else True
        )

        db.session.add(user)
        db.session.commit()

        # auto create student profile
        if role == "student":
            student = Student(user_id=user.id)
            db.session.add(student)
            db.session.commit()

        return redirect("/login")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


                    #ADMIN

@app.route("/admin_dashboard")
def admin_dashboard():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    pending_companies = User.query.filter_by(
        role="company",
        is_approved=False
    ).all()

    total_students = User.query.filter_by(role="student").count()
    total_companies = User.query.filter_by(role="company").count()
    total_jobs = Job.query.count()
    total_applications = Application.query.count()

    return render_template(
        "admin_dashboard.html",
        user=user,
        companies=pending_companies,
        total_students=total_students,
        total_companies=total_companies,
        total_jobs=total_jobs,
        total_applications=total_applications
    )

@app.route("/approve_companies")
def approve_companies():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    companies = User.query.filter_by(
        role="company",
        is_approved=False
    ).all()

    return render_template(
        "approve_companies.html",
        companies=companies
    )

@app.route("/approve_company/<int:user_id>")
def approve_company(user_id):

    # check login
    if "id" not in session:
        return redirect("/login")

    # get logged-in user
    user = User.query.get(session["id"])

    # admin check
    if user.role != "admin":
        return "Access denied"

    # approve company
    company = User.query.get(user_id)

    if company and company.role == "company":
        company.is_approved = True
        db.session.commit()

    return redirect("/admin_dashboard")

@app.route("/admin_jobs")
def admin_jobs():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    jobs = Job.query.all()

    return render_template("admin_jobs.html", jobs=jobs)


@app.route("/approve_job/<int:job_id>")
def approve_job(job_id):

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    job = Job.query.get(job_id)

    if job:
        job.status = "Approved"
        db.session.commit()

    return redirect("/admin_jobs")


@app.route("/reject_job/<int:job_id>")
def reject_job(job_id):

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    job = Job.query.get(job_id)

    if job:
        job.status = "Rejected"
        db.session.commit()

    return redirect("/admin_jobs")


@app.route("/admin_students")
def admin_students():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    # search input
    query = request.args.get("query")

    if query:
        students = Student.query.filter(
            Student.name.ilike(f"%{query}%")
        ).all()
    else:
        students = Student.query.all()

    return render_template(
        "admin_students.html",
        students=students
    )


@app.route("/admin_companies")
def admin_companies():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"
    query = request.args.get("query")

    if query:
        companies = Company.query.filter(
            Company.company_name.ilike(f"%{query}%")
        ).all()
    else:
        companies = Company.query.all()

    return render_template(
        "admin_companies.html",
        companies=companies
    )


@app.route("/toggle_blacklist_company/<int:company_id>")
def toggle_blacklist_company(company_id):

    # login check
    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    # admin only
    if user.role != "admin":
        return "Access denied"

    company = Company.query.get(company_id)

    if company:
        # TOGGLE LOGIC
        company.is_blacklisted = not company.is_blacklisted
        db.session.commit()

    return redirect("/admin_companies")


@app.route("/toggle_blacklist_student/<int:student_id>")
def toggle_blacklist_student(student_id):

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    student = Student.query.get(student_id)

    if student:
        student.is_blacklisted = not student.is_blacklisted
        db.session.commit()

    return redirect("/admin_students")

@app.route("/admin_applications")
def admin_applications():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "admin":
        return "Access denied"

    applications = Application.query.all()

    return render_template(
        "admin_applications.html",
        applications=applications
    )


                    # COMPANY

@app.route("/company_dashboard")
def company_dashboard():

    # check login
    if "id" not in session:
        return redirect("/login")

    # get logged-in user
    user = User.query.get(session["id"])

    # fetch company profile
    company = Company.query.filter_by(user_id=user.id).first()

    # blacklist check
    if company and company.is_blacklisted:
        return "Your company account has been blacklisted by admin."
    
    # FIRST CHECK PROFILE
    if not company:
        return redirect("/complete-company-profile")

    # NOW SAFE
    jobs = Job.query.filter_by(company_id=company.id).all()

    total_jobs = len(jobs)

    total_applications = 0
    shortlisted = 0

    for job in jobs:
        total_applications += len(job.applications)

        for app in job.applications:
            if app.status == "Shortlisted":
                shortlisted += 1

    # approval check
    if not user.is_approved:
        return "waiting for admin approval"
    

    return render_template(
        "company_dashboard.html",
        user=user,
        company=company,
        jobs=jobs,
        total_jobs=total_jobs,
        total_applications=total_applications,
        shortlisted=shortlisted
    )


@app.route("/complete-company-profile", methods=["GET", "POST"])
def complete_company_profile():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    # check existing profile
    company = Company.query.filter_by(user_id=user.id).first()

    # SAVE OR UPDATE
    if request.method == "POST":

        # if company doesn't exist → create
        if not company:
            company = Company(user_id=user.id)

        company.company_name = request.form["company_name"]
        company.industry = request.form["industry"]
        company.location = request.form["location"]
        company.website = request.form["website"]
        company.company_size = request.form["company_size"]
        company.hr_name = request.form["hr_name"]
        company.hr_email = request.form["hr_email"]
        company.description = request.form["description"]

        db.session.add(company)
        db.session.commit()

        return redirect("/company_dashboard")

    return render_template(
        "complete_company_profile.html",
        company=company
    )


@app.route("/post_job", methods=["GET","POST"])
def post_job():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])
    company = Company.query.filter_by(user_id=user.id).first()

    if company.is_blacklisted:
        return "Blacklisted companies cannot post jobs"

    if request.method == "POST":
        # Get deadline from form
        deadline_str = request.form["deadline"]
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")

        job = Job(
            role=request.form["title"],
            skills=request.form["skills"],
            experience=request.form["experience"],
            salary=request.form["salary"],
            description=request.form["description"],
            deadline=deadline,
            company_id=company.id
        )

        db.session.add(job)
        db.session.commit()

        return redirect("/company_dashboard")
    return render_template("post_job.html")

@app.route("/manage_jobs")
def manage_jobs():
    if "id" not in session:
        return redirect("/login")
    
    user=User.query.get(session["id"])
    company=Company.query.filter_by(user_id=user.id).first()

    if company.is_blacklisted:
        return "Account blacklisted"

    if not company:
        return redirect("/complete-company-profile")
    
     # fetch jobs of this company
    jobs = Job.query.filter_by(company_id=company.id).all()

    return render_template(
        "manage_jobs.html",
        jobs=jobs
    )

@app.route("/edit_job/<int:job_id>", methods=["GET","POST"])
def edit_job(job_id):

    job = Job.query.get(job_id)

    if request.method == "POST":

        job.role = request.form["role"]
        job.skills = request.form["skills"]
        job.experience = request.form["experience"]
        job.salary = request.form["salary"]

        db.session.commit()

        return redirect("/manage_jobs")
    return render_template("edit_job.html", job=job)

@app.route("/delete_job/<int:job_id>")
def delete_job(job_id):

    if "id" not in session:
        return redirect("/login")

    job = Job.query.get(job_id)

    if job:
        db.session.delete(job)
        db.session.commit()

    return redirect("/manage_jobs")

@app.route("/close_job/<int:job_id>")
def close_job(job_id):

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "company":
        return "Access denied"

    job = Job.query.get(job_id)

    if job:
        job.status = "Closed"
        db.session.commit()

    return redirect("/manage_jobs")


@app.route("/company_applications")
def company_applications():

    # login check
    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    # get company profile
    company = Company.query.filter_by(user_id=user.id).first()

    # get all jobs of this company
    jobs = Job.query.filter_by(company_id=company.id).all()

    # collect applications
    applications = []

    for job in jobs:
        applications.extend(job.applications)

    return render_template(
        "company_applications.html",
        applications=applications
    )

@app.route("/update_application_status/<int:app_id>/<string:new_status>")
def update_application_status(app_id, new_status):

    # login check
    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    # company only
    if user.role != "company":
        return "Access denied"

    application = Application.query.get(app_id)

    if application:
        application.status = new_status
        db.session.commit()

    return redirect("/company_applications")


                   # STUDENT

@app.route("/student_dashboard")
def student_dashboard():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "student":
        return "Access denied"

    # student profile
    student = Student.query.filter_by(user_id=user.id).first()

    if student and student.is_blacklisted:
        return "Your account has been blacklisted by admin."

    # ONLY approved jobs
    jobs = Job.query.filter_by(status="Approved").all()

    # applications
    my_applications = []

    if student:
        my_applications = Application.query.filter_by(
            student_id=student.id
        ).all()

    # applied job ids (for button change)
    applied_job_ids = [
        app.job_id for app in my_applications
    ]

    # stats
    applied_jobs = len(my_applications)

    shortlisted = len([
        app for app in my_applications
        if app.status == "Shortlisted"
    ])

    placed = len([
        app for app in my_applications
        if app.status == "Selected"
    ])

    return render_template(
        "student_dashboard.html",
        user=user,
        student=student,
        jobs=jobs,
        my_applications=my_applications,
        applied_job_ids=applied_job_ids,
        applied_jobs=applied_jobs,
        shortlisted=shortlisted,
        placed=placed
    )

@app.route("/apply_job/<int:job_id>", methods=["POST"])
def apply_job(job_id):


    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "student":
        return "Access denied"

    student = Student.query.filter_by(user_id=user.id).first()

    if not student:
        return redirect("/edit_profile")

    if student.is_blacklisted:
        return "Blacklisted students cannot apply for jobs."
    
    job = Job.query.get(job_id)

    if job.deadline and job.deadline < datetime.utcnow():
        return "Application deadline has passed."

    # prevent duplicate apply
    existing = Application.query.filter_by(
        student_id=student.id,
        job_id=job_id
    ).first()

    if not existing:
        application = Application(
            student_id=student.id,
            job_id=job_id,
            status="Applied"
        )
        db.session.add(application)
        db.session.commit()

    return redirect("/student_dashboard")


@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "student":
        return "Access denied"

    # ALWAYS ensure student exists
    student = Student.query.filter_by(user_id=user.id).first()

    if not student:
        student = Student(user_id=user.id)
        db.session.add(student)
        db.session.commit()

    if request.method == "POST":

        student.name = request.form.get("name")
        student.college_name = request.form.get("college_name")
        student.branch = request.form.get("branch")

        cgpa_value = request.form.get("cgpa")
        if cgpa_value and cgpa_value.strip() != "":
            student.cgpa = float(cgpa_value)
        else:
            student.cgpa = None

        student.skills = request.form.get("skills")
        student.resume_link = request.form.get("resume_link")

        db.session.commit()

        return redirect("/student_dashboard")

    return render_template("edit_profile.html", user=user, student=student)


@app.route("/available_jobs")
def available_jobs():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "student":
        return "Access denied"

    student = Student.query.filter_by(user_id=user.id).first()

    if student and student.is_blacklisted:
        return "Your account has been blacklisted by admin."

    # SEARCH INPUT
    query = request.args.get("query")

    if query:
        jobs = Job.query.filter(
            Job.status == "Approved",
            (Job.role.ilike(f"%{query}%") |
             Job.skills.ilike(f"%{query}%"))
        ).all()
    else:
        jobs = Job.query.filter_by(status="Approved").all()

    my_applications = []

    if student:
        my_applications = Application.query.filter_by(
            student_id=student.id
        ).all()

    applied_job_ids = [app.job_id for app in my_applications]

    return render_template(
        "available_jobs.html",
        user=user,
        jobs=jobs,
        applied_job_ids=applied_job_ids
    )

@app.route("/my_applications")
def my_applications():

    if "id" not in session:
        return redirect("/login")

    user = User.query.get(session["id"])

    if user.role != "student":
        return "Access denied"

    student = Student.query.filter_by(user_id=user.id).first()

    applications = []

    if student:
        applications = Application.query.filter_by(
            student_id=student.id
        ).all()

    return render_template(
        "my_applications.html",
        user=user,
        my_applications=applications
    )




# MAIN
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        existing_admin = User.query.filter_by(name="admin").first()
        if not existing_admin:
            admin = User(
                name="admin",
                email="admin@gmail.com",
                password="admin",
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)