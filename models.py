from enum import unique
from database import db
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
Base = declarative_base()

# ================= WORKER MODELS ===============================
class Worker(db.Model):
    __tablename__ = "worker"
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(200), nullable=True)

    # signup fields
    name = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    phone_no = db.Column(db.String(20), unique=True)

    # post-signup profile fields (✅ MUST be nullable)
    email = db.Column(db.String(128), unique=True, nullable=False)
    gender = db.Column(db.String(15), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(256), nullable=True)
    languages = db.Column(db.String(100), nullable=True)

    is_password_set = db.Column(db.Boolean, default=True)

    # KYC documents
    profile_photo = db.Column(db.String(200), nullable=True)
    aadhar_card = db.Column(db.String(200), nullable=True)
    pan_card = db.Column(db.String(200), nullable=True)
    resume = db.Column(db.String(200), nullable=True)

    kyc_status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WorkExperience(db.Model):
    __tablename__ = "work_experience"

    id = db.Column(db.Integer, primary_key=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey("worker.id"),
        nullable=False
    )

    job_title = db.Column(db.String(100), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)  # NULL = Present
    description = db.Column(db.Text,nullable=True)

    worker = db.relationship("Worker", backref="experiences")

class Certification(db.Model):
    __tablename__ = "certification"

    id = db.Column(db.Integer, primary_key=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey("worker.id"),
        nullable=False
    )

    title = db.Column(db.String(120), nullable=False)
    issuer = db.Column(db.String(120))
    valid_till = db.Column(db.Date, nullable=True)
    certificate_file = db.Column(db.String(200))  # PDF/Image path

    worker = db.relationship("Worker", backref="certifications")

class Education(db.Model):
    __tablename__ = "education"

    id = db.Column(db.Integer, primary_key=True)

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey("worker.id"),
        nullable=False
    )

    degree = db.Column(db.String(120), nullable=False)   # e.g. SSC, HSC, Diploma
    institution = db.Column(db.String(200), nullable=False)
    board_university = db.Column(db.String(120), nullable=True)
    year_of_passing = db.Column(db.Integer, nullable=True)
    grade = db.Column(db.String(50), nullable=True)

    worker = db.relationship("Worker", backref="educations")



# ================= COMPANY MODELS ===============================
class Company(db.Model):
    __tablename__ = "company"

    id = db.Column(db.Integer, primary_key=True)

    # ---------- AUTH / BASIC ----------
    company_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    google_id = db.Column(db.String(255), nullable=True)
    is_password_set = db.Column(db.Boolean, default=True)


    # ---------- PROFILE HEADER ----------
    company_category = db.Column(db.String(120),nullable=True)     # Manufacturing & Production
    company_size = db.Column(db.String(50), nullable=True)          # 150–200 employees
    company_city = db.Column(db.String(120), nullable=True)         # Mumbai

    # ---------- COMPANY INFORMATION ----------   
    founded_year = db.Column(db.Integer, nullable=True)              # 2010
    gst_number = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20),nullable=True)
    website = db.Column(db.String(150),nullable=True)
    address = db.Column(db.String(255),nullable=True)

    contact_person = db.Column(db.String(120),nullable=True)
    contact_designation = db.Column(db.String(80),nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================= JOB POST MODEL ===============================
class JobPost(db.Model):
    __tablename__ = "job_post"

    job_id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company.id"),
        nullable=False
    )
    
    job_title = db.Column(db.String(120), nullable=False)#
    job_type = db.Column(db.String(120), nullable=False)#
    city = db.Column(db.String(120), nullable=False)#
    specific_location = db.Column(db.String(128), nullable=False)#
    shift = db.Column(db.String(50), nullable=False)#
    job_start_time = db.Column(Time, nullable=False) #
    job_end_time = db.Column(Time, nullable=False) #
    job_opening_no = db.Column(db.Integer , nullable=False)      # Day / Night / General / Part Time
    salary = db.Column(db.String(50), nullable=False)#
    description = db.Column(db.Text, nullable=False) #
    job_contact = db.Column(db.String(28), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Active")

    company = db.relationship("Company", backref="jobs")


class Application(db.Model):
    application_id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.job_id'), nullable=False)
    applicant_name = db.Column(db.String(80), nullable=False)
    applicant_email = db.Column(db.String(120), nullable=True)
    applicant_phone = db.Column(db.String(20), nullable=False)
    applicant_age = db.Column(db.Integer, nullable=False)
    applicant_gender = db.Column(db.String(20), nullable=False)
    applicant_skill = db.Column(db.String(120), nullable=False)
    applicant_location = db.Column(db.String(120), nullable=False)
    applicant_status = db.Column(db.String(20), nullable=False, default="pending")
    application_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    worker_id = db.Column(db.Integer, db.ForeignKey("worker.id"), nullable=False)

    aadhar_card = db.Column(db.String(200), nullable=True)
    pan_card = db.Column(db.String(200), nullable=True)
    resume = db.Column(db.String(200), nullable=True)

  # Link to user who applied

    # Relationship to JobPOST
    job = db.relationship('JobPost', backref='applications')

    def __repr__(self):
        return f"<Application {self.applicant_name} for Job {self.job_id}>"

class sellitem(db.Model):
    __tablename__ = 'sell_item'
    
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"))

    sell_id = db.Column(db.Integer, primary_key=True)
    sell_name = db.Column(db.String(80), nullable=False) #
    sell_price = db.Column(db.Float, nullable=False)
    sell_quantity = db.Column(db.Integer, nullable=False)
    sell_description = db.Column(db.Text, nullable=False)                      #
    sell_image = db.Column(db.Text, nullable=True)  # Made optional for now
    sell_category = db.Column(db.String(80), nullable=True)  # Category field     #

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    company = db.relationship("Company", backref="sell_items")
    def __repr__(self):
        return f"<sellitem {self.sell_name} - ₹{self.sell_price}>"

from sqlalchemy.orm import foreign
class TradeRequest(db.Model):
    __tablename__ = "trade_request"

    id = db.Column(db.Integer, primary_key=True)

    sell_id = db.Column(
        db.Integer,
        db.ForeignKey("sell_item.sell_id"),
        nullable=False
    )

    buyer_id = db.Column(db.Integer, nullable=False)
    buyer_type = db.Column(db.String(20), nullable=False)  
    # "worker" or "company"

    quantity = db.Column(db.Integer, nullable=False)
    expected_price = db.Column(db.Float, nullable=True)
    message = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sell = db.relationship("sellitem", backref="trade_requests")
    
    @property
    def buyer_name(self):
        if self.buyer_type == "worker":
            worker = Worker.query.get(self.buyer_id)
            return worker.name if worker else "Unknown Worker"
        else:
            company = Company.query.get(self.buyer_id)
            return company.company_name if company else "Unknown Company"
