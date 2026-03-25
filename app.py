import email
from enum import unique
from flask import Flask, render_template, request, redirect, session, url_for , jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime , date
from sqlalchemy import Time
import os
import re
from werkzeug.utils import secure_filename
import uuid
from flask import Flask
from database import db
import config
import json

from authlib.integrations.flask_client import OAuth


import secrets


from flask import flash
app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

from models import Worker, TradeRequest , WorkExperience, Certification, Education ,Company, JobPost, sellitem, Application  # import AFTER db.init_app

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url="https://oauth2.googleapis.com/token",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    api_base_url="https://www.googleapis.com/oauth2/v2/",
    client_kwargs={
        "scope": "email profile",
        "token_endpoint_auth_method": "client_secret_post"
    }
)



@app.route('/login/google')
def login_google():
    role = request.args.get("role")   # worker or company
    session["oauth_role"] = role
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = google.get("userinfo").json()

    email = user_info.get("email")
    name = user_info.get("name")
    google_id = user_info.get("id")

    role = session.get("oauth_role")   # worker / company
    temp_password = secrets.token_urlsafe(16)

    if role == "company":
        user = Company.query.filter_by(email=email).first()
        if not user:
            user = Company(
                company_name=name,
                email=email,
                google_id=google_id,
                password=temp_password,
                is_password_set=False
            )
            db.session.add(user)
            db.session.commit()

        session.clear()
        session["company_id"] = user.id
        session["user_type"] = "company"

        if not user.is_password_set:
            return redirect(url_for("set_company_password"))

        return redirect(url_for("companyprofile"))

    # -------- WORKER --------
    user = Worker.query.filter_by(email=email).first()
    if not user:
        user = Worker(
            name=name,
            email=email,
            google_id=google_id,
            password=temp_password,
            is_password_set=False
        )
        db.session.add(user)
        db.session.commit()

    session.clear()
    session["worker_id"] = user.id
    session["user_type"] = "worker"

    if not user.is_password_set:
        return redirect(url_for("set_password"))

    return redirect(url_for("workerprofile"))

@app.route("/set-password", methods=["GET","POST"])
def set_password():
    if request.method == "POST":
        pwd = request.form["password"]
        
        user = Worker.query.get(session["worker_id"])
        user.password = pwd
        user.is_password_set = True
        db.session.commit()
        return redirect(url_for("workerprofile"))
    return render_template("set_password.html")

@app.route("/set-company-password", methods=["GET","POST"])
def set_company_password():
    if "company_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        pwd = request.form["password"]
        company = Company.query.get(session["company_id"])
        company.password = pwd
        company.is_password_set = True
        db.session.commit()
        return redirect(url_for("companyprofile"))

    return render_template("set_password.html")  # same UI can be reused

@app.route("/")
def home():

    jobs = JobPost.query.order_by(
        JobPost.created_at.desc()
    ).limit(6).all()
    
    return render_template("home.html", jobs=jobs)

@app.route("/industry-map")
def industrymap():
    search_query = request.args.get("search", "")
    return render_template("industrymap.html", search_query=search_query)

@app.route('/product_view')
def productview():
    return render_template('product_view.html')
@app.route("/jobportal")
def jobportal():
    page = request.args.get("page", 1, type=int)
    per_page = 12

    category = request.args.get("category")
    city = request.args.get("city")
    shift = request.args.get("shift")
    salary = request.args.get("salary", type=int)
    openings = request.args.get("openings", type=int)

    query = JobPost.query.filter_by(status="Active")

    if category:
        query = query.filter(JobPost.job_title.ilike(f"%{category}%"))

    if city:
        query = query.filter(JobPost.city.ilike(f"%{city}%"))

    if shift:
        query = query.filter(JobPost.shift == shift)

    if salary:
        query = query.filter(
            JobPost.salary.cast(db.Integer) >= salary
        )

    if openings:
        query = query.filter(JobPost.job_opening_no >= openings)

    pagination = query.order_by(
        JobPost.created_at.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template(
        "jobportal.html",
        jobs=pagination.items,
        pagination=pagination
    )


@app.route("/trade/<int:sell_id>")
def tradevisit(sell_id):
    sell = sellitem.query.get_or_404(sell_id)

    worker = None
    if session.get("user_type") == "worker":
        worker = Worker.query.get(session.get("worker_id"))

    images = []
    if sell.sell_image:
        images = json.loads(sell.sell_image)  

    worker_age = None
    if worker and worker.dob:
        today = date.today()
        worker_age = today.year - worker.dob.year - (
            (today.month, today.day) < (worker.dob.month, worker.dob.day)
        )

    

    return render_template(
        "product_view.html",
        sell=sell,
        images=images
    )

@app.route("/job/<int:job_id>")
def jobvisit(job_id):
    job = JobPost.query.get_or_404(job_id)

    worker = None
    if session.get("user_type") == "worker":
        worker = Worker.query.get(session.get("worker_id"))
     
    worker_age = None
    if worker and worker.dob:
        today = date.today()
        worker_age = today.year - worker.dob.year - (
            (today.month, today.day) < (worker.dob.month, worker.dob.day)
        )

    return render_template(
        "jobvisit.html",
        job=job,
        worker=worker,
        worker_age=worker_age
    )



from sqlalchemy.exc import SQLAlchemyError
from flask import abort

@app.route("/application/<int:application_id>/status", methods=["POST"])
def update_application_status(application_id):

    # 🔐 Only company allowed
    if session.get("user_type") != "company":
        abort(403)

    new_status = request.form.get("status")  # Accepted / Rejected

    application = Application.query.get_or_404(application_id)
    job = application.job

    # 🔐 Ownership check
    if job.company_id != session.get("company_id"):
        abort(403)

    # 🚫 Already processed → STOP
    if application.applicant_status != "pending":
        flash("This application has already been processed.", "warning")
        return redirect(request.referrer)

    try:
        if new_status == "Accepted":

            # 🚫 No openings left
            if job.job_opening_no <= 0:
                flash("No openings left for this job.", "danger")
                return redirect(request.referrer)

            # ✅ Accept
            application.applicant_status = "Accepted"
            job.job_opening_no -= 1

            # 🔒 Auto close job
            if job.job_opening_no == 0:
                job.status = "Closed"

        elif new_status == "Rejected":
            application.applicant_status = "Rejected"

        else:
            flash("Invalid action", "danger")
            return redirect(request.referrer)

        db.session.commit()
        flash("Application updated successfully.", "success")

    except SQLAlchemyError:
        db.session.rollback()
        flash("Database error. Try again.", "danger")

    return redirect(request.referrer)

@app.route("/company/application/<int:application_id>/delete", methods=["POST"])
def delete_company_application(application_id):
    if session.get("user_type") != "company":
        return redirect(url_for("login"))

    application = Application.query.get_or_404(application_id)

    # security check
    if application.job.company_id != session.get("company_id"):
        abort(403)

    db.session.delete(application)
    db.session.commit()

    flash("Application removed successfully", "success")
    return redirect(request.referrer)

@app.route("/company/trade/<int:sell_id>/applications")
def view_trade_applications(sell_id):

    if session.get("user_type") != "company":
        return redirect(url_for("login"))

    company_id = session.get("company_id")

    item = sellitem.query.filter_by(
        sell_id=sell_id,
        company_id=company_id
    ).first_or_404()

    applications = TradeRequest.query.filter_by(
        sell_id=sell_id
    ).order_by(
        TradeRequest.created_at.desc()
    ).all()

    return render_template(
        "trade_application.html",
        item=item,
        applications=applications
    )


@app.route("/company/job/<int:job_id>/applications")
def view_job_applications(job_id):
    if session.get("user_type") != "company":
        return redirect(url_for("login"))

    company_id = session.get("company_id")

    job = JobPost.query.filter_by(
        job_id=job_id,
        company_id=company_id
    ).first_or_404()

    applications = Application.query.filter_by(job_id=job_id)\
                                    .order_by(Application.application_date.desc())\
                                    .all()

    return render_template(
        "job_applications.html",
        job=job,
        applications=applications
    )

@app.route("/worker/<int:worker_id>")
def workerprofile_public(worker_id):
    # Only company can view worker public profile
    if session.get("user_type") != "company":
        return redirect(url_for("login"))

    worker = Worker.query.get_or_404(worker_id)

    return render_template(
        "workerpublic.html",   # the template I gave you earlier
        worker=worker
    )


@app.route("/company/<int:company_id>")
def companyprofile_public(company_id):
    company = Company.query.get_or_404(company_id)
    jobs = JobPost.query.filter_by(
        company_id=company.id,
        status="Active"
    ).all()

    return render_template(
        "company.html",
        company=company,
        jobs=jobs
    )

@app.route('/trade')
def trade():
    page = request.args.get("page", 1, type=int)
    per_page = 9

    
    
    date = request.args.get("date")
    qty = request.args.get("qty")
    price = request.args.get("price")

    query = sellitem.query

    # Quantity filter
    if qty == "050":
        query = query.filter(sellitem.sell_quantity < 50)
    elif qty == "50100":
        query = query.filter(sellitem.sell_quantity >= 50)
    elif qty == "100":
        query = query.filter(sellitem.sell_quantity >= 100)

    # Date sort
    if date == "NF":
        query = query.order_by(sellitem.created_at.desc())
    elif date == "OF":
        query = query.order_by(sellitem.created_at.asc())

    # Price sort
    if price == "l2h":
        query = query.order_by(sellitem.sell_price.asc())
    elif price == "h2l":
        query = query.order_by(sellitem.sell_price.desc())

    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    for item in pagination.items:
        if item.sell_image:
            item.images = json.loads(item.sell_image)
        else:
            item.images = [] 
    return render_template(
        "trade.html",
        sell_items=pagination.items,
        pagination=pagination
    )

@app.route('/company/job/delete/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    job = JobPost.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return redirect(url_for('companyprofile'))


@app.route('/company/trade/delete/<int:sell_id>', methods=['POST'])
def delete_trade(sell_id):
    item = sellitem.query.get_or_404(sell_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('companyprofile'))


@app.route('/login')
def login():
    return render_template('login.html')

@app.route("/login/worker", methods=["POST"])
def login_worker():
    email = request.form.get("mail")
    password = request.form.get("password")

    if not email or not password:
        flash("All fields are required", "error")
        return redirect(url_for("login"))

    worker = Worker.query.filter_by(email=email).first()

    if not worker or worker.password != password:
        flash("Invalid phone number or password", "error")
        return redirect(url_for("login"))

    # ---------- SESSION ----------
    session.clear()
    session["worker_id"] = worker.id
    session["user_type"] = "worker"

    return redirect(url_for("workerprofile"))

@app.route("/login/company", methods=["POST"])
def login_company():
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("All fields are required", "error")
        return redirect(url_for("login"))

    company = Company.query.filter_by(email=email).first()

    if not company or company.password != password:
        flash("Invalid email or password", "error")
        return redirect(url_for("login"))

    session.clear()
    session["company_id"] = company.id
    session["user_type"] = "company"

    return redirect(url_for("companyprofile"))

# ======================== WORKER =========================
@app.route("/signup/worker", methods=["POST"])
def signup_worker():
    worker = Worker(
        name=request.form["full_name"],
        email=request.form["mail"],
        password=request.form["password"]
    )
    db.session.add(worker)
    db.session.commit()

    session["worker_id"] = worker.id
    session["user_type"] = "worker" 
    return redirect(url_for("workerprofile"))

@app.route("/worker-profile")
def workerprofile():
    if session.get("user_type") != "worker":
        return redirect(url_for("login"))

    worker_id = session.get('worker_id')
    worker = Worker.query.get(session["worker_id"])
    initial = worker.name[0].upper() if worker.name else "U"

    applications = Application.query \
        .filter_by(worker_id=worker_id) \
        .order_by(Application.application_date.desc()) \
        .all()

    return render_template(
        "workerprofile.html",
        worker=worker,
        initial=initial,
        applications=applications
    )

@app.route('/worker/application/delete/<int:app_id>', methods=['POST'])
def delete_worker_application(app_id):
    if session.get("user_type") != "worker":
        abort(403)

    app = Application.query.get_or_404(app_id)

    if app.worker_id != session.get('worker_id'):
        abort(403)

    # only pending applications can be deleted
    if app.applicant_status != "pending":
        flash("You cannot delete a processed application", "warning")
        return redirect(url_for("workerprofile"))

    db.session.delete(app)
    db.session.commit()
    flash("Application deleted", "success")
    return redirect(url_for('workerprofile'))



@app.route('/application/edit', methods=['POST'])
def edit_application():
    app = Application.query.get_or_404(request.form['application_id'])

    if app.worker_id != session.get('worker_id'):
        abort(403)

    app.applicant_skill = request.form['applicant_skill']
    app.applicant_location = request.form['applicant_location']

    db.session.commit()
    return redirect(url_for('workerprofile'))




from sqlalchemy.exc import IntegrityError
from datetime import datetime

@app.route("/worker/update-profile", methods=["POST"])
def update_worker_profile():
    if session.get("user_type") != "worker":
        return jsonify(success=False, message="Unauthorized")

    worker = Worker.query.get(session["worker_id"])
    if not worker:
        return jsonify(success=False, message="Worker not found")

    email = request.form.get("email")
    phone = request.form.get("phone")
    gender = request.form.get("gender")
    dob = request.form.get("dob")
    address = request.form.get("address")
    languages = request.form.getlist("languages")

    # phone uniqueness
    if phone != worker.phone_no:
        if Worker.query.filter_by(phone_no=phone).first():
            return jsonify(success=False, message="Phone already in use")
        worker.phone_no = phone

    # email uniqueness
    if email and email != worker.email:
        if Worker.query.filter_by(email=email).first():
            return jsonify(success=False, message="Email already in use")
        worker.email = email

    worker.gender = gender or None
    worker.address = address or None

    if dob:
        worker.dob = datetime.strptime(dob, "%Y-%m-%d").date()

    # sanitize & store
    allowed = {"Hindi", "English", "Marathi"}
    languages = [l for l in languages if l in allowed]

    worker.languages = ",".join(languages) if languages else None


    db.session.commit()
    return jsonify(success=True)


    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, message="Database error")

    return jsonify(success=True)

@app.route("/worker/upload-profile-photo", methods=["POST"])
def upload_profile_photo():
    worker_id = session.get("worker_id")
    if not worker_id:
        return redirect(url_for("login"))

    file = request.files.get("profile_photo")
    if not file or file.filename == "":
        return redirect(url_for("workerprofile"))

    filename = secure_filename(file.filename)
    path = os.path.join("static/uploads", filename)
    file.save(path)

    worker = Worker.query.get(worker_id)
    worker.profile_photo = filename
    db.session.commit()

    return redirect(url_for("workerprofile"))

@app.route("/worker/upload-documents", methods=["POST"])
def upload_worker_documents():
    if session.get("user_type") != "worker":
        return redirect(url_for("logintype"))

    worker = Worker.query.get(session.get("worker_id"))
    if not worker:
        return redirect(url_for("logintype"))

    upload_folder = "static/uploads"
    os.makedirs(upload_folder, exist_ok=True)

    # -------- AADHAR --------
    aadhar = request.files.get("aadhar_card")
    if aadhar and aadhar.filename:
        aadhar_filename = f"{uuid.uuid4()}_{secure_filename(aadhar.filename)}"
        aadhar.save(os.path.join(upload_folder, aadhar_filename))
        worker.aadhar_card = aadhar_filename

    # -------- PAN --------
    pan = request.files.get("pan_card")
    if pan and pan.filename:
        pan_filename = f"{uuid.uuid4()}_{secure_filename(pan.filename)}"
        pan.save(os.path.join(upload_folder, pan_filename))
        worker.pan_card = pan_filename

    # -------- RESUME --------
    resume = request.files.get("resume")
    if resume and resume.filename:
        resume_filename = f"{uuid.uuid4()}_{secure_filename(resume.filename)}"
        resume.save(os.path.join(upload_folder, resume_filename))
        worker.resume = resume_filename

    # -------- KYC STATUS --------
    if worker.aadhar_card and worker.pan_card:
        worker.kyc_status = "submitted"
        session.pop("kyc_started", None)


    db.session.commit()
    flash("Document uploaded successfully.", "success")

    return redirect(url_for("workerprofile"))

@app.route("/worker/start-kyc")
def start_kyc():
    session["kyc_started"] = True
    return "", 204

@app.route("/worker/add-experience", methods=["POST"])
def add_experience():
    if session.get("user_type") != "worker":
        return jsonify(success=False)

    start_date = datetime.strptime(
        request.form["start_date"], "%Y-%m-%d"
    ).date()

    end_date_raw = request.form.get("end_date")
    end_date = (
        datetime.strptime(end_date_raw, "%Y-%m-%d").date()
        if end_date_raw else None
    )

    exp = WorkExperience(
        worker_id=session["worker_id"],
        job_title=request.form["job_title"],
        company_name=request.form["company_name"],
        location=request.form.get("location"),
        start_date=start_date,
        end_date=end_date,
        description=request.form.get("description")
    )

    db.session.add(exp)
    db.session.commit()

    return jsonify(success=True)


@app.route("/worker/add-certification", methods=["POST"])
def add_certification():
    worker_id = session.get("worker_id")
    if not worker_id:
        return redirect(url_for("login"))

    title = request.form.get("title")
    issuer = request.form.get("issuer")

    valid_till_raw = request.form.get("valid_till")
    valid_till = None
    if valid_till_raw:
        valid_till = datetime.strptime(valid_till_raw, "%Y-%m-%d").date()

    file = request.files.get("certificate_file")
    filename = None
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join("static/uploads", filename))

    cert = Certification(
        worker_id=worker_id,
        title=title,
        issuer=issuer,
        valid_till=valid_till,
        certificate_file=filename
    )

    db.session.add(cert)
    db.session.commit()

    return redirect(url_for("workerprofile"))

from datetime import datetime

@app.route("/worker/add-education", methods=["POST"])
def add_education():
    worker_id = session.get("worker_id")

    if not worker_id:
        return jsonify({"success": False, "message": "Not logged in"})

    edu = Education(
        worker_id=worker_id,
        degree=request.form.get("degree"),
        institution=request.form.get("institution"),
        board_university=request.form.get("board_university"),
        year_of_passing=request.form.get("year_of_passing") or None,
        grade=request.form.get("grade")
    )

    db.session.add(edu)
    db.session.commit()

    return jsonify({"success": True})

# ========================= COMPANY ================================
@app.route("/signup/company", methods=["POST"])
def signup_company():
    if request.method == "GET":
        return render_template("signup.html")

    # ---------- READ FORM DATA ----------
    company_name = request.form.get("company_name")
    email = request.form.get("email")
    password = request.form.get("password")
 

    # ---------- VALIDATION ----------
    if not all([
        email, password, company_name,
    
    ]):
        return "All required fields must be filled", 400

    # ---------- DUPLICATE EMAIL CHECK ----------
    existing_company = Company.query.filter_by(email=email).first()
    if existing_company:
        return "Company already registered with this email", 400

    # ---------- CREATE COMPANY ----------
    company = Company(
        email=email,
        password=password,  # (hash later)
        company_name=company_name
    )

    db.session.add(company)
    db.session.commit()

    # ---------- SESSION ----------
    session.clear()
    session["company_id"] = company.id
    session["user_type"] = "company"

    return redirect(url_for("companyprofile"))

@app.route("/company-profile")
def companyprofile():
    if session.get("user_type") != "company":
        return redirect(url_for("login"))

    company = Company.query.get(session["company_id"])
    sell_items = sellitem.query.filter_by(
    company_id=company.id
).order_by(sellitem.created_at.desc()).all()

    initial = company.company_name[0].upper() if company.company_name else "U"

    return render_template(
        "companyprofile.html",
        company=company,
        initial=initial,
        sell_items=sell_items
    )

@app.route("/company/upload-profile-photo", methods=["POST"])
def upload_company_photo():
    company_id = session.get("company_id")
    if not company_id:
        return redirect(url_for("login"))

    file = request.files.get("profile_photo")
    if not file or file.filename == "":
        return redirect(url_for("companyprofile"))

    filename = secure_filename(file.filename)
    path = os.path.join("static/uploads", filename)
    file.save(path)

    company = Company.query.get(company_id)
    company.profile_photo = filename
    db.session.commit()

    return redirect(url_for("companyprofile"))


@app.route("/company/update-profile", methods=["POST"])
def update_company_profile():
    if session.get("user_type") != "company":
        return jsonify(success=False, message="Unauthorized")

    company = Company.query.get(session["company_id"])
    if not company:
        return jsonify(success=False, message="Company not found")

    company.company_category = request.form.get("company_category") or None
    company.company_city = request.form.get("company_city") or None
    company.company_size = request.form.get("company_size") or None
    company.founded_year = request.form.get("founded_year") or None
    company.gst_number = request.form.get("gst_number") or None

    db.session.commit()
    return jsonify(success=True)


@app.route("/company/update-contact", methods=["POST"])
def update_company_contact():
    if session.get("user_type") != "company":
        return jsonify(success=False, message="Unauthorized")

    company = Company.query.get(session["company_id"])
    if not company:
        return jsonify(success=False, message="Company not found")

    company.phone = request.form.get("phone") or None
    company.website = request.form.get("website") or None
    company.address = request.form.get("address") or None
    company.contact_person = request.form.get("contact_person") or None
    company.contact_designation = request.form.get("contact_designation") or None

    db.session.commit()
    return jsonify(success=True)

# ========================= JOB POST ==========================
@app.route("/company/job", methods=["POST"])
def create_or_edit_job():
    if session.get("user_type") != "company":
        return redirect(url_for("login"))

    job_id = request.form.get("job_id")

    # -------- Job Type --------
    job_type = request.form.get("job_type")
    if job_type == "Other":
        job_type = request.form.get("job_type_other")

    # -------- Shift --------
    shift = request.form.get("shift")
    if shift == "Other":
        shift = request.form.get("shift_other")

    # -------- Convert TIME --------
    job_start_time = datetime.strptime(
        request.form.get("job_start_time"), "%H:%M"
    ).time()

    job_end_time = datetime.strptime(
        request.form.get("job_end_time"), "%H:%M"
    ).time()

    if job_id:
        # ===== EDIT JOB =====
        job = JobPost.query.get(job_id)

        job.job_title = request.form.get("job_title")
        job.job_type = job_type
        job.city = request.form.get("city")
        job.specific_location = request.form.get("specific_location")
        job.shift = shift
        job.job_start_time = job_start_time
        job.job_end_time = job_end_time
        job.job_opening_no = int(request.form.get("job_opening_no"))
        job.salary = request.form.get("salary")
        job.description = request.form.get("description")
        job.job_contact = request.form.get("job_contact")

    else:
        # ===== CREATE JOB =====
        job = JobPost(
            company_id=session["company_id"],
            job_title=request.form.get("job_title"),
            job_type=job_type,
            city=request.form.get("city"),
            specific_location=request.form.get("specific_location"),
            shift=shift,
            job_start_time=job_start_time,
            job_end_time=job_end_time,
            job_opening_no=int(request.form.get("job_opening_no")),
            salary=request.form.get("salary"),
            description=request.form.get("description"),
            job_contact=request.form.get("job_contact"),
        )

        db.session.add(job)

    db.session.commit()
    return redirect(url_for("companyprofile"))
@app.route("/trade/apply", methods=["POST"])
def apply_trade():
    user_type = session.get("user_type")

    if user_type not in ["company", "worker"]:
        flash("Please login to apply for trade", "danger")
        return redirect(url_for("login"))

    buyer_id = session.get("worker_id") if user_type == "worker" else session.get("company_id")

    sell_id = int(request.form.get("sell_id"))
    sell = sellitem.query.get_or_404(sell_id)

    if user_type == "company" and sell.company_id == buyer_id:
        flash("You cannot apply to your own product", "danger")
        return redirect(request.referrer)

    quantity = request.form.get("quantity")
    expected_price = request.form.get("expected_price")
    message = request.form.get("message")

    if not quantity:
        flash("Quantity is required", "danger")
        return redirect(request.referrer)

    existing = TradeRequest.query.filter_by(
        sell_id=sell_id,
        buyer_id=buyer_id,
        buyer_type=user_type,
        status="pending"
    ).first()

    if existing:
        flash("You already sent a request for this product", "warning")
        return redirect(request.referrer)

    trade_request = TradeRequest(
        sell_id=sell_id,
        buyer_id=buyer_id,
        buyer_type=user_type,
        quantity=int(quantity),
        expected_price=float(expected_price) if expected_price else None,
        message=message
    )

    db.session.add(trade_request)
    db.session.commit()

    flash("Trade request sent successfully!", "success")
    return redirect(request.referrer)


@app.route("/apply", methods=["POST"])
def applyjob():
    if session.get("user_type") != "worker":
        return redirect(url_for("login"))

    worker_id = session.get("worker_id")
    worker = Worker.query.get_or_404(worker_id)

    job_id = request.form.get("job_id")
    if not job_id:
        abort(400, "Job ID missing")

    # Prevent duplicate application
    existing = Application.query.filter_by(
        job_id=job_id,
        worker_id=worker_id
    ).first()

    if existing:
        flash("You have already applied for this job", "warning")
        return redirect(url_for("jobvisit", job_id=job_id))

    application = Application(
        job_id=job_id,
        applicant_name=request.form.get("applicant_name"),
        applicant_email=request.form.get("applicant_email"),
        applicant_phone=request.form.get("applicant_phone"),
        applicant_age=request.form.get("applicant_age"),
        applicant_gender=request.form.get("applicant_gender"),
        applicant_skill=request.form.get("applicant_skill"),
        applicant_location=request.form.get("applicant_location"),
        worker_id=worker_id,
        aadhar_card=worker.aadhar_card,
        pan_card=worker.pan_card,
        resume=worker.resume
    )

    db.session.add(application)
    db.session.commit()

    flash("Application submitted successfully!", "success")
    return redirect(url_for("jobvisit", job_id=job_id))


# ========================= TRADE =============================
UPLOAD_FOLDER = "static/uploads/sell_items"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/company/additem", methods=["GET", "POST"])
def add_selling_item():

    if session.get("user_type") != "company":
        return redirect(url_for("home"))

    if request.method == "POST":
        # ---------- FORM DATA ----------
        sell_name = request.form.get("sell_name")
        sell_category = request.form.get("sell_category")
        sell_quantity_raw = request.form.get("sell_quantity")
        sell_location = request.form.get("sell_location")
        sell_price_raw = request.form.get("sell_price")
        sell_description = request.form.get("sell_description")

        files = request.files.getlist("sell_images[]")

        # ---------- VALIDATION ----------
        if not all([sell_name, sell_quantity_raw, sell_price_raw, sell_description]):
            return "All required fields must be filled", 400

        # ---------- CLEAN PRICE ----------
        price_match = re.search(r'[\d.]+', sell_price_raw.replace(',', ''))
        if not price_match:
            return "Invalid price format", 400
        sell_price = float(price_match.group())

        # ---------- CLEAN QUANTITY ----------
        qty_match = re.search(r'\d+', sell_quantity_raw)
        if not qty_match:
            return "Invalid quantity format", 400
        sell_quantity = int(qty_match.group())

        # ---------- SAVE IMAGES ----------
        image_filenames = []

        for file in files:
            if file and file.filename != "" and allowed_file(file.filename):
                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4().hex}{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_filenames.append(filename)

        sell_id = request.form.get("sell_id")
        if sell_id:
        # ===== EDIT JOB =====
            
            sell = sellitem.query.get(sell_id)

            # 🔐 ownership check (VERY IMPORTANT)
            if sell.company_id != session["company_id"]:
                abort(403)
                
            sell.sell_name = request.form.get("sell_name") or sell_name
            sell.sell_category = request.form.get("sell_category") or sell_category
            sell.sell_quantity = request.form.get("sell_quantity") or sell_quantity
            # sell.sell_location = request.form.get("sell_location") or sell_location
            sell.sell_price = request.form.get("sell_price") or sell_price
            sell.sell_description = request.form.get("sell_description") or sell_description

        else:
            # ---------- CREATE DB ENTRY ----------
            sell_item = sellitem(
                sell_name=sell_name,  
                company_id=session["company_id"],
                sell_category=sell_category or "General",
                sell_quantity=sell_quantity,
                sell_price=sell_price,
                sell_description=sell_description,
                sell_image=json.dumps(image_filenames),  # ✅ MULTIPLE IMAGES
                created_at=datetime.utcnow()
            )

            db.session.add(sell_item)
        db.session.commit()

    
    return redirect(url_for("companyprofile"))
    

@app.route('/signup')
def signup():
    return render_template("signup.html")

# ===================== LOGOUT =====================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# class Worker(db.Model):
#     __tablename__ = "worker"
#     id = db.Column(db.Integer, primary_key=True)

#     username = db.Column(db.String(80), unique=True, nullable=False)
#     password = db.Column(db.String(128), nullable=False)
#     email = db.Column(db.String(128), unique=True ,nullable=False)
#     phone_no = db.Column(db.String(20), nullable=False)

#     # KYC documents (post-signup)
#     aadhar_card = db.Column(db.String(200), nullable=True)
#     pan_card = db.Column(db.String(200), nullable=True)
#     resume = db.Column(db.String(200), nullable=True)

#     # KYC workflow
#     kyc_status = db.Column(
#         db.String(20),
#         nullable=False,
#         default="pending"  
#         # pending | submitted | verified | rejected
#     )

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

# class Company(db.Model):
#     __tablename__ = "company"

#     id = db.Column(db.Integer, primary_key=True)

#     # LOGIN CREDENTIALS
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password = db.Column(db.String(128), nullable=False)

#     # COMPANY DETAILS
#     company_name = db.Column(db.String(120), nullable=False)
#     company_category = db.Column(db.String(120), nullable=False)
#     company_location = db.Column(db.String(120), nullable=False)
#     company_contact = db.Column(db.String(20), nullable=False)
#     company_address = db.Column(db.String(256), nullable=False)
#     company_website = db.Column(db.String(120), nullable=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)


# class JobPOST(db.Model):
#     __tablename__ = "job_post"

#     job_id = db.Column(db.Integer, primary_key=True)
#     company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

#     job_title = db.Column(db.String(80), nullable=False)
#     job_category = db.Column(db.String(128), nullable=False)
#     job_location = db.Column(db.String(128), nullable=False)
#     job_specific_location = db.Column(db.String(128), nullable=False)
#     job_start_time = db.Column(Time, nullable=False) 
#     job_end_time = db.Column(Time, nullable=False)              ================= job start time and end time ====================
#     job_opening_no = db.Column(db.Integer , nullable=False)               ================= job openings no ====================
#     job_experience = db.Column(db.String(128), nullable=False)
#     job_shift = db.Column(db.String(128), nullable=False)
#     job_salary = db.Column(db.String(128), nullable=False)
#     job_contact = db.Column(db.String(128), nullable=False)
#     job_description = db.Column(db.Text, nullable=False)

#     company = db.relationship('Company', backref='jobs')



# class Application(db.Model):
#     application_id = db.Column(db.Integer, primary_key=True)
#     job_id = db.Column(db.Integer, db.ForeignKey('job_post.job_id'), nullable=False)
#     applicant_name = db.Column(db.String(80), nullable=False)
#     applicant_email = db.Column(db.String(120), nullable=False)
#     applicant_phone = db.Column(db.String(20), nullable=False)
#     applicant_age = db.Column(db.Integer, nullable=False)
#     applicant_gender = db.Column(db.String(20), nullable=False)
#     applicant_skill = db.Column(db.String(120), nullable=False)
#     applicant_experience = db.Column(db.String(120), nullable=False)
#     applicant_expected_salary = db.Column(db.String(120), nullable=False)
#     applicant_location = db.Column(db.String(120), nullable=False)
#     applicant_preferred_shift = db.Column(db.String(120), nullable=False)
#     applicant_status = db.Column(db.String(20), nullable=False, default="pending")
#     application_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     worker_id = db.Column(db.Integer, db.ForeignKey("worker.id"), nullable=False)

#     aadhar_card = db.Column(db.String(200), nullable=True)
#     pan_card = db.Column(db.String(200), nullable=True)
#     resume = db.Column(db.String(200), nullable=True)

#   # Link to user who applied

#     # Relationship to JobPOST
#     job = db.relationship('JobPOST', backref='applications')

#     def __repr__(self):
#         return f"<Application {self.applicant_name} for Job {self.job_id}>"

# class sellitem(db.Model):
#     __tablename__ = 'sell_item'
#     sell_id = db.Column(db.Integer, primary_key=True)
#     sell_name = db.Column(db.String(80), nullable=False)
#     sell_price = db.Column(db.Float, nullable=False)
#     sell_quantity = db.Column(db.Integer, nullable=False)
#     sell_description = db.Column(db.Text, nullable=False)
#     sell_image = db.Column(db.String(200), nullable=True)  # Made optional for now
#     sell_status = db.Column(db.String(20), nullable=False, default="available")
#     sell_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     posted_by = db.Column(db.String(80), nullable=False)  # Store business username/email
#     sell_category = db.Column(db.String(80), nullable=True)  # Category field
#     sell_location = db.Column(db.String(128), nullable=True)  # Location field

#     def __repr__(self):
#         return f"<sellitem {self.sell_name} - ₹{self.sell_price}>"


# class buyitem(db.Model):
#     __tablename__ = 'buy_item'
#     buy_id = db.Column(db.Integer, primary_key=True)
#     buy_name = db.Column(db.String(80), nullable=False)
#     buy_budget = db.Column(db.Float, nullable=True)  # Optional budget
#     buy_quantity = db.Column(db.Integer, nullable=False)
#     buy_description = db.Column(db.Text, nullable=False)
#     buy_image = db.Column(db.String(200), nullable=True)  # Optional image URL
#     buy_status = db.Column(db.String(20), nullable=False, default="open")
#     buy_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
#     posted_by = db.Column(db.String(80), nullable=False)  # Store business username/email
#     buy_category = db.Column(db.String(80), nullable=True)  # Category field
#     buy_location = db.Column(db.String(128), nullable=True)  # Location field

#     def __repr__(self):
#         return f"<buyitem {self.buy_name} - Budget: ₹{self.buy_budget if self.buy_budget else 'Negotiable'}>"

    
# ===================== HOME =====================
# @app.route("/")
# def home():
#     # Always show home page; user can choose where to go next
#     return render_template("home.html")


# @app.route("/index")
# def index():
#     # Legacy route used by old template; just reuse home page
#     return redirect(url_for("home"))

# @app.route("/dashboard")
# def dashboard():
#     if session.get("user_type") == "worker":
#         return redirect(url_for("workerprofile"))

#     if session.get("user_type") == "company":
#         return redirect(url_for("companyprofile"))

#     return redirect(url_for("logintype"))




# @app.route("/jobportal")
# def jobportal():
#     role = session.get("user_type") 


#     # If not logged in at all, send to login type selector page
#     if role is None:
#         return redirect(url_for("logintype"))

#     # Only normal users can see the job portal
#     if role != "worker":
#         return redirect(url_for("dashboard"))

#     # Fetch all jobs from database
#     jobs = JobPOST.query.all()
#     return render_template("job-portal.html", jobs=jobs)

# # ===================== BUSINESS ROUTES =====================
# @app.route("/companyprofile")
# def companyprofile():
#     if session.get("user_type") != "company":
#         return redirect(url_for("login"))

#     company = Company.query.get(session["company_id"])

#     jobs = JobPOST.query.filter_by(company_id=company.id).all()
#     sell_items = sellitem.query.filter_by(
#         posted_by=company.email
#     ).order_by(sellitem.sell_date.desc()).all()

#     buy_items = buyitem.query.filter_by(
#         posted_by=company.email
#     ).order_by(buyitem.buy_date.desc()).all()

    
#     total_b2b_listings = len(sell_items) + len(buy_items)

#     return render_template(
#         "company-profile.html",
#         company=company,
#         jobs=jobs,
#         sell_items=sell_items,
#         buy_items=buy_items,
#         total_jobs_posted=len(jobs),
#         total_b2b_listings=total_b2b_listings
#     )

# @app.route("/company/update-profile", methods=["POST"])
# def update_company_profile():
#     if session.get("user_type") != "company":
#         return jsonify(success=False, message="Not logged in")

#     company = Company.query.get(session["company_id"])
#     if not company:
#         return jsonify(success=False, message="Company not found")

#     data = request.get_json()

#     company.company_name = data.get("company_name", company.company_name)
#     company.company_contact = data.get("company_contact", company.company_contact)
#     company.company_website = data.get("company_website", company.company_website)
#     company.company_address = data.get("company_address", company.company_address)
#     company.company_location = data.get("company_location", company.company_location)

#     db.session.commit()

#     return jsonify(
#         success=True,
#         company_name=company.company_name,
#         company_contact=company.company_contact,
#         company_website=company.company_website,
#         company_address=company.company_address,
#         company_location=company.company_location
#     )


# @app.route("/jobpost", methods=["GET", "POST"])
# def jobpost():
#     if session.get("user_type") != "company":
#         return redirect(url_for("login"))

#     if request.method == "POST":
#         job = JobPOST(
#             company_id=session["company_id"],
#             job_title=request.form.get("job_title"),
#             job_category=request.form.get("job_category"),
#             job_location=request.form.get("job_location"),
#             job_specific_location=request.form.get("job_specific_location"),
#             job_experience=request.form.get("job_experience"),
#             job_shift=request.form.get("job_shift"),
#             job_salary=request.form.get("job_salary"),
#             job_contact=request.form.get("job_contact"),
#             job_description=request.form.get("job_description"),
#         )

#         db.session.add(job)
#         db.session.commit()
#         return redirect(url_for("companyprofile"))

#     return render_template("post-job.html")



# @app.route("/application")
# def application():
#     if session.get("user_type") != "company":
#         return redirect(url_for("dashboard"))

#     job_id = request.args.get("job_id")
#     company_id = session["company_id"]

#     # All jobs posted by this company
#     business_jobs = JobPOST.query.filter_by(company_id=company_id).all()

#     if job_id:
#         job = JobPOST.query.get(job_id)

#         # ✅ FIX: check ownership using company_id
#         if not job or job.company_id != company_id:
#             return "Job not found or unauthorized", 404

#         applications = Application.query.filter_by(job_id=job_id).order_by(
#             Application.application_date.desc()
#         ).all()

#         return render_template(
#             "view-applications.html",
#             applications=applications,
#             job=job,
#             all_jobs=business_jobs
#         )

#     # ---------- SHOW ALL APPLICATIONS ----------
#     if business_jobs:
#         job_ids = [job.job_id for job in business_jobs]
#         applications = Application.query.filter(
#             Application.job_id.in_(job_ids)
#         ).order_by(Application.application_date.desc()).all()
#     else:
#         applications = []

#     return render_template(
#         "view-applications.html",
#         applications=applications,
#         job=None,
#         all_jobs=business_jobs
#     )

# @app.route("/company/update-application-status", methods=["POST"])
# def update_application_status():
#     if session.get("user_type") != "company":
#         return jsonify(success=False, message="Unauthorized")

#     data = request.get_json()
#     app_id = data.get("application_id")
#     status = data.get("status")

#     if status not in ["selected", "rejected"]:
#         return jsonify(success=False, message="Invalid status")

#     application = Application.query.get(app_id)
#     if not application:
#         return jsonify(success=False, message="Application not found")

#     application.applicant_status = status
#     db.session.commit()

#     return jsonify(success=True)


# @app.route("/cancel_application/<int:app_id>", methods=["POST"])
# def cancel_application(app_id):
#     if session.get("user_type") != "worker":
#         return redirect(url_for("dashboard"))

#     application = Application.query.get_or_404(app_id)


#     # Only allow cancel if pending
#     if application.applicant_status != "pending":
#         return "Cannot cancel this application", 400

#     db.session.delete(application)
#     db.session.commit()

#     return redirect(url_for("workerprofile"))


# # ===================== B2B (OPTIONAL BUSINESS PAGES) =====================
# @app.route("/homeb2b")
# def b2bhome():
#     role = session.get("user_type")

#     # If not logged in at all, send to login type selector page
#     if role is None:
#         return redirect(url_for("logintype"))

#     if role != "company":
#         return redirect(url_for("dashboard"))

#     return render_template("b2b-home.html")


# @app.route("/b2bsell", methods=["GET", "POST"])
# def b2bpost():
#     if session.get("user_type") != "company":
#         return redirect(url_for("dashboard"))

#     if request.method == "POST":
#         sell_name = request.form.get("sell_name")
#         sell_category = request.form.get("sell_category")
#         sell_quantity_raw = request.form.get("sell_quantity")
#         sell_location = request.form.get("sell_location")
#         sell_price_raw = request.form.get("sell_price")
#         sell_description = request.form.get("sell_description")
#         sell_image = request.form.get("sell_image")

#         # ---------- VALIDATION ----------
#         if not all([sell_name, sell_quantity_raw, sell_price_raw, sell_description]):
#             return "All required fields must be filled", 400

#         # ---------- PRICE CLEAN ----------
#         price_match = re.search(r'[\d.]+', sell_price_raw.replace(',', ''))
#         if not price_match:
#             return "Invalid price format", 400
#         sell_price = float(price_match.group())

#         # ---------- QUANTITY CLEAN ----------
#         qty_match = re.search(r'\d+', sell_quantity_raw)
#         if not qty_match:
#             return "Invalid quantity format", 400
#         sell_quantity = int(qty_match.group())

#         # ---------- CREATE SELL ITEM ----------
#         sell_item = sellitem(
#             sell_name=sell_name,
#             sell_category=sell_category or "General",
#             sell_quantity=sell_quantity,
#             sell_location=sell_location or "Not specified",
#             sell_price=sell_price,
#             sell_description=sell_description,
#             sell_image=sell_image,
#             sell_status="available",
#             posted_by=Company.query.get(session["company_id"]).email
#         )

#         db.session.add(sell_item)
#         db.session.commit()

#         return redirect(url_for("companyprofile"))

#     return render_template("b2b-post.html")


# @app.route("/b2bbuy")
# def buyerlist():
#     if session.get("user_type") != "company":
#         return redirect(url_for("dashboard"))

#     # Fetch all available sell items
#     sell_items = sellitem.query.filter_by(sell_status="available").order_by(
#         sellitem.sell_date.desc()
#     ).all()

#     # Fetch all open buy requirements
#     buy_items = buyitem.query.filter_by(buy_status="open").order_by(
#         buyitem.buy_date.desc()
#     ).all()

#     return render_template("buyer-list.html", sell_items=sell_items, buy_items=buy_items)


# @app.route("/hostseller", methods=["GET", "POST"])
# def hostseller():
#     if session.get("user_type") != "company":
#         return redirect(url_for("dashboard"))

#     if request.method == "POST":
#         # Get form data for buy requirement
#         buy_name = request.form.get("buy_name")
#         buy_category = request.form.get("buy_category")
#         buy_quantity = request.form.get("buy_quantity")
#         buy_location = request.form.get("buy_location")
#         buy_budget = request.form.get("buy_budget", "")
#         buy_description = request.form.get("buy_description")
#         buy_image = request.form.get("buy_image", "")  # Optional image URL

#         # Validate required fields
#         if not all([buy_name, buy_quantity, buy_description]):
#             return "Name, quantity, and description are required", 400

#         try:
#             # Convert quantity - extract number from string
#             quantity_match = re.search(r'\d+', buy_quantity)
#             if quantity_match:
#                 quantity_int = int(quantity_match.group())
#             else:
#                 return "Invalid quantity format. Please enter a number.", 400

#             # Convert budget if provided
#             budget_float = None
#             if buy_budget and buy_budget.strip().lower() not in ['negotiable', 'na', '']:
#                 budget_str = buy_budget.replace('₹', '').replace(',', '').replace(' ', '').strip()
#                 budget_match = re.search(r'[\d.]+', budget_str)
#                 if budget_match:
#                     budget_float = float(budget_match.group())

#         except (ValueError, AttributeError):
#             return "Invalid quantity or budget format", 400

#         # Create new buy item
#         buy_item = buyitem(
#             buy_name=buy_name,
#             buy_category=buy_category or "General",
#             buy_quantity=quantity_int,
#             buy_location=buy_location or "Not specified",
#             buy_budget=budget_float,
#             buy_description=buy_description,
#             buy_image=buy_image,
#             posted_by=session.get("user", "unknown")
#         )

#         db.session.add(buy_item)
#         db.session.commit()

#         # Redirect to B2B home with success
#         return redirect(url_for("b2bhome"))

#     return render_template("seller-host.html")


# # ===================== LOGOUT =====================
# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect(url_for("home"))


# ===================== DATABASE INITIALIZATION =====================
# Create all database tables if they don't exist
with app.app_context():
    db.create_all()
    print("Database tables created/verified successfully!")


# # ===================== RUN =====================
# if __name__ == "__main__":
#     app.run(debug=False, host='0.0.0.0', port=5000)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
