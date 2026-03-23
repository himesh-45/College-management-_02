from flask import Flask, render_template, request, redirect, session, flash, jsonify
from models import db, Student, Faculty, User, StudentMark, Department, Attendance, Course, FeeRecord, Notice, Timetable
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = "college_secret_2026"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db.init_app(app)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="ADMIN").first():
        db.session.add(User(username="ADMIN", password=generate_password_hash("ADMIN123"), role="admin"))
        db.session.commit()
    # Seed sample departments
    if not Department.query.first():
        for d in [
            Department(dept_id="CSE", name="Computer Science & Engineering", hod="Dr. Sharma", established="1995", total_seats=120),
            Department(dept_id="ECE", name="Electronics & Communication", hod="Dr. Patel", established="1998", total_seats=60),
            Department(dept_id="MECH", name="Mechanical Engineering", hod="Dr. Kumar", established="1990", total_seats=60),
            Department(dept_id="CIVIL", name="Civil Engineering", hod="Dr. Reddy", established="1992", total_seats=60),
        ]:
            db.session.add(d)
        db.session.commit()


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def require_role(*roles):
    if session.get("role") not in roles:
        return redirect("/")
    return None


# ─── LOGIN / LOGOUT ───────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        r = request.form["role"]
        user = User.query.filter_by(username=u, role=r).first()
        if user and check_password_hash(user.password, p):
            session["user"] = u
            session["role"] = r
            return redirect(f"/{r}")
        flash("Invalid credentials. Please try again.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─── ADMIN ────────────────────────────────────────────────────────────────────
@app.route("/admin")
def admin_dashboard():
    if g := require_role("admin"): return g
    students = Student.query.all()
    faculty = Faculty.query.all()
    departments = Department.query.all()
    notices = Notice.query.order_by(Notice.id.desc()).limit(5).all()
    toppers = sorted(students, key=lambda x: (x.cgpa or 0), reverse=True)[:5]
    fee_pending = Student.query.filter_by(fee_status="Pending").count()
    fee_paid = Student.query.filter_by(fee_status="Paid").count()
    return render_template("admin_dashboard.html",
                           students=students, faculty=faculty,
                           departments=departments, notices=notices,
                           toppers=toppers, fee_pending=fee_pending,
                           fee_paid=fee_paid)


# ─── DEPARTMENTS ──────────────────────────────────────────────────────────────
@app.route("/departments")
def departments():
    if g := require_role("admin"): return g
    depts = Department.query.all()
    return render_template("departments.html", departments=depts)


@app.route("/add_department", methods=["POST"])
def add_department():
    if g := require_role("admin"): return g
    db.session.add(Department(
        dept_id=request.form["dept_id"].upper(),
        name=request.form["name"],
        hod=request.form["hod"],
        established=request.form["established"],
        total_seats=int(request.form["total_seats"])
    ))
    db.session.commit()
    return redirect("/departments")


@app.route("/delete_department/<did>")
def delete_department(did):
    if g := require_role("admin"): return g
    Department.query.filter_by(dept_id=did).delete()
    db.session.commit()
    return redirect("/departments")


# ─── COURSES ──────────────────────────────────────────────────────────────────
@app.route("/courses")
def courses():
    if g := require_role("admin", "faculty"): return g
    courses = Course.query.all()
    departments = Department.query.all()
    faculty_list = Faculty.query.all()
    return render_template("courses.html", courses=courses, departments=departments, faculty_list=faculty_list)


@app.route("/add_course", methods=["POST"])
def add_course():
    if g := require_role("admin"): return g
    db.session.add(Course(
        course_id=request.form["course_id"].upper(),
        name=request.form["name"],
        dept_id=request.form["dept_id"],
        credits=int(request.form["credits"]),
        semester=int(request.form["semester"]),
        faculty_id=request.form.get("faculty_id") or None
    ))
    db.session.commit()
    return redirect("/courses")


@app.route("/delete_course/<cid>")
def delete_course(cid):
    if g := require_role("admin"): return g
    Course.query.filter_by(course_id=cid).delete()
    db.session.commit()
    return redirect("/courses")


# ─── NOTICES ──────────────────────────────────────────────────────────────────
@app.route("/notices")
def notices():
    if g := require_role("admin", "faculty", "student"): return g
    role = session.get("role")
    if role == "admin":
        all_notices = Notice.query.order_by(Notice.id.desc()).all()
    else:
        all_notices = Notice.query.filter(
            (Notice.target == "all") | (Notice.target == role)
        ).order_by(Notice.id.desc()).all()
    return render_template("notices.html", notices=all_notices, role=role)


@app.route("/add_notice", methods=["POST"])
def add_notice():
    if g := require_role("admin", "faculty"): return g
    db.session.add(Notice(
        title=request.form["title"],
        content=request.form["content"],
        posted_by=session["user"],
        posted_on=datetime.now().strftime("%d %b %Y %H:%M"),
        category=request.form["category"],
        target=request.form.get("target", "all")
    ))
    db.session.commit()
    return redirect("/notices")


@app.route("/delete_notice/<int:nid>")
def delete_notice(nid):
    if g := require_role("admin"): return g
    Notice.query.filter_by(id=nid).delete()
    db.session.commit()
    return redirect("/notices")


# ─── ATTENDANCE ───────────────────────────────────────────────────────────────
@app.route("/attendance")
def attendance():
    if g := require_role("admin", "faculty"): return g
    students = Student.query.all()
    records = Attendance.query.order_by(Attendance.date.desc()).limit(200).all()
    return render_template("attendance.html", students=students, records=records)


@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    if g := require_role("admin", "faculty"): return g
    date = request.form["date"]
    subject = request.form["subject"]
    rolls = request.form.getlist("rolls")
    present = request.form.getlist("present")

    for roll in rolls:
        Attendance.query.filter_by(roll_no=roll, date=date, subject=subject).delete()
        db.session.add(Attendance(
            roll_no=roll,
            date=date,
            subject=subject,
            status="Present" if roll in present else "Absent"
        ))
    db.session.commit()
    flash("Attendance marked successfully!", "success")
    return redirect("/attendance")


@app.route("/attendance_report/<roll>")
def attendance_report(roll):
    if g := require_role("admin", "faculty", "student"): return g
    if session.get("role") == "student" and session.get("user") != roll:
        return redirect("/student")
    student = Student.query.get(roll)
    records = Attendance.query.filter_by(roll_no=roll).order_by(Attendance.date.desc()).all()
    total = len(records)
    present = sum(1 for r in records if r.status == "Present")
    pct = round((present / total * 100), 1) if total > 0 else 0
    return render_template("attendance_report.html", student=student, records=records,
                           total=total, present=present, pct=pct)


# ─── FEE MANAGEMENT ──────────────────────────────────────────────────────────
@app.route("/fees")
def fees():
    if g := require_role("admin"): return g
    students = Student.query.all()
    records = FeeRecord.query.order_by(FeeRecord.id.desc()).all()
    total_collected = sum(r.amount for r in records)
    return render_template("fees.html", students=students, records=records, total_collected=total_collected)


@app.route("/add_fee", methods=["POST"])
def add_fee():
    if g := require_role("admin"): return g
    roll = request.form["roll_no"]
    db.session.add(FeeRecord(
        roll_no=roll,
        amount=float(request.form["amount"]),
        paid_date=request.form["paid_date"],
        fee_type=request.form["fee_type"],
        transaction_id=request.form.get("transaction_id", ""),
        remarks=request.form.get("remarks", "")
    ))
    # update student fee_status
    student = Student.query.get(roll)
    if student:
        student.fee_status = "Paid"
    db.session.commit()
    flash("Fee record added!", "success")
    return redirect("/fees")


# ─── TIMETABLE ────────────────────────────────────────────────────────────────
@app.route("/timetable")
def timetable():
    if g := require_role("admin", "faculty", "student"): return g
    role = session.get("role")
    departments = Department.query.all()
    faculty_list = Faculty.query.all()

    dept_filter = request.args.get("dept", "")
    year_filter = request.args.get("year", "")

    query = Timetable.query
    if dept_filter:
        query = query.filter_by(dept_id=dept_filter)
    if year_filter:
        query = query.filter_by(year=year_filter)

    slots = query.order_by(Timetable.day, Timetable.period).all()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    return render_template("timetable.html", slots=slots, days=days,
                           departments=departments, faculty_list=faculty_list,
                           dept_filter=dept_filter, year_filter=year_filter, role=role)


@app.route("/add_timetable", methods=["POST"])
def add_timetable():
    if g := require_role("admin"): return g
    db.session.add(Timetable(
        dept_id=request.form["dept_id"],
        year=request.form["year"],
        day=request.form["day"],
        period=int(request.form["period"]),
        subject=request.form["subject"],
        faculty_id=request.form.get("faculty_id", ""),
        time_slot=request.form.get("time_slot", "")
    ))
    db.session.commit()
    return redirect(f"/timetable?dept={request.form['dept_id']}&year={request.form['year']}")


@app.route("/delete_timetable/<int:tid>")
def delete_timetable(tid):
    if g := require_role("admin"): return g
    Timetable.query.filter_by(id=tid).delete()
    db.session.commit()
    return redirect("/timetable")


# ─── STUDENT MANAGEMENT ───────────────────────────────────────────────────────
@app.route("/add_student", methods=["POST"])
def add_student():
    if g := require_role("admin"): return g
    roll = request.form["roll_no"].upper()
    if Student.query.get(roll):
        flash("Student with this Roll No already exists!", "danger")
        return redirect("/admin")
    db.session.add(Student(
        roll_no=roll,
        name=request.form["name"],
        year=request.form["year"],
        grade=request.form["grade"],
        backlogs=int(request.form.get("backlogs", 0)),
        cgpa=0,
        email=request.form.get("email", ""),
        phone=request.form.get("phone", ""),
        dept_id=request.form.get("dept_id") or None,
        dob=request.form.get("dob", ""),
        guardian_name=request.form.get("guardian_name", ""),
        guardian_phone=request.form.get("guardian_phone", ""),
        admission_date=request.form.get("admission_date", ""),
        fee_status="Pending"
    ))
    db.session.add(User(username=roll, password=generate_password_hash("1234"), role="student"))
    db.session.commit()
    flash("Student added successfully!", "success")
    return redirect("/admin")


@app.route("/update_student/<roll>", methods=["GET", "POST"])
def update_student(roll):
    if g := require_role("admin"): return g
    student = Student.query.get(roll)
    departments = Department.query.all()
    if request.method == "POST":
        student.name = request.form["name"]
        student.year = request.form["year"]
        student.grade = request.form["grade"]
        student.backlogs = int(request.form["backlogs"])
        student.email = request.form["email"]
        student.phone = request.form["phone"]
        student.dept_id = request.form.get("dept_id") or None
        student.dob = request.form.get("dob", "")
        student.guardian_name = request.form.get("guardian_name", "")
        student.guardian_phone = request.form.get("guardian_phone", "")
        student.fee_status = request.form.get("fee_status", "Pending")
        db.session.commit()
        flash("Student updated!", "success")
        return redirect("/admin")
    return render_template("edit_student.html", s=student, departments=departments)


@app.route("/delete_student/<roll>")
def delete_student(roll):
    if g := require_role("admin"): return g
    StudentMark.query.filter_by(roll_no=roll).delete()
    Attendance.query.filter_by(roll_no=roll).delete()
    FeeRecord.query.filter_by(roll_no=roll).delete()
    User.query.filter_by(username=roll).delete()
    Student.query.filter_by(roll_no=roll).delete()
    db.session.commit()
    return redirect("/admin")


# ─── FACULTY MANAGEMENT ───────────────────────────────────────────────────────
@app.route("/add_faculty", methods=["POST"])
def add_faculty():
    if g := require_role("admin"): return g
    fid = request.form["faculty_id"].upper()
    db.session.add(Faculty(
        faculty_id=fid,
        name=request.form["name"],
        branch=request.form["branch"],
        salary=int(request.form["salary"]),
        performance=request.form["performance"],
        specialization=request.form["specialization"],
        achievements=request.form["achievements"],
        dept_id=request.form.get("dept_id") or None,
        email=request.form.get("email", ""),
        phone=request.form.get("phone", ""),
        qualification=request.form.get("qualification", ""),
        joining_date=request.form.get("joining_date", "")
    ))
    db.session.add(User(username=fid, password=generate_password_hash("1234"), role="faculty"))
    db.session.commit()
    flash("Faculty added successfully!", "success")
    return redirect("/admin")


@app.route("/update_faculty/<fid>", methods=["GET", "POST"])
def update_faculty(fid):
    if g := require_role("admin"): return g
    faculty = Faculty.query.get(fid)
    departments = Department.query.all()
    if request.method == "POST":
        faculty.name = request.form["name"]
        faculty.branch = request.form["branch"]
        faculty.salary = int(request.form["salary"])
        faculty.performance = request.form["performance"]
        faculty.specialization = request.form["specialization"]
        faculty.achievements = request.form["achievements"]
        faculty.dept_id = request.form.get("dept_id") or None
        faculty.email = request.form.get("email", "")
        faculty.phone = request.form.get("phone", "")
        faculty.qualification = request.form.get("qualification", "")
        db.session.commit()
        flash("Faculty updated!", "success")
        return redirect("/admin")
    return render_template("edit_faculty.html", f=faculty, departments=departments)


@app.route("/delete_faculty/<fid>")
def delete_faculty(fid):
    if g := require_role("admin"): return g
    Faculty.query.filter_by(faculty_id=fid).delete()
    User.query.filter_by(username=fid).delete()
    db.session.commit()
    return redirect("/admin")


# ─── MARKS ────────────────────────────────────────────────────────────────────
def _smart_read_excel(path):
    """
    Read Excel intelligently — handles title rows, merged headers, and no-header files.
    Scans first 10 rows to find the actual header row containing known keywords.
    Falls back to positional column assignment if no header is found.
    """
    KEYWORDS = {"roll", "name", "sub", "mark", "semester", "sem",
                "year", "grade", "email", "phone", "dept", "branch",
                "backlog", "subject", "cgpa", "sgpa"}

    # Read raw without assuming header
    raw = pd.read_excel(path, header=None)

    # Find the first row that contains at least 2 keyword hits — that's the header
    header_row = None
    for i in range(min(10, len(raw))):
        row_str = " ".join(str(v).lower() for v in raw.iloc[i].values if pd.notna(v))
        hits = sum(1 for kw in KEYWORDS if kw in row_str)
        if hits >= 2:
            header_row = i
            break

    if header_row is not None:
        df = pd.read_excel(path, header=header_row)
    else:
        # No recognisable header — use positional assignment
        df = raw.copy()
        ncols = len(df.columns)
        pos_names = ["roll_no", "sub1", "sub2", "sub3", "sub4", "sub5"]
        df.columns = pos_names[:ncols] + [f"extra_{j}" for j in range(ncols - len(pos_names))] if ncols >= 6 else pos_names[:ncols]
        # Drop obvious title rows (first col not matching a roll-number pattern)
        df = df[df.iloc[:, 0].astype(str).str.match(r"^[A-Za-z]{1,6}\d+", na=False)].reset_index(drop=True)

    return _normalize_columns(df)


def _normalize_columns(df):
    """Normalize column names: strip, lowercase, replace spaces with underscore, apply aliases."""
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\.]+", "_", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    # Drop columns that are still fully unnamed after normalization
    df = df.loc[:, ~df.columns.str.fullmatch(r"unnamed_\d+")]
    aliases = {
        "roll": "roll_no", "rollno": "roll_no", "roll_number": "roll_no",
        "student_name": "name", "full_name": "name", "fullname": "name",
        "subject1": "sub1", "subject2": "sub2", "subject3": "sub3",
        "subject4": "sub4", "subject5": "sub5",
        "marks1": "sub1", "marks2": "sub2", "marks3": "sub3",
        "marks4": "sub4", "marks5": "sub5",
        "sub1_marks": "sub1", "sub2_marks": "sub2", "sub3_marks": "sub3",
        "sub4_marks": "sub4", "sub5_marks": "sub5",
        "backlog": "backlogs", "back_logs": "backlogs",
        "phone_number": "phone", "mobile": "phone", "contact": "phone",
        "email_id": "email", "mail": "email",
        "department": "dept_id", "dept": "dept_id",
        "academic_year": "year", "yr": "year",
    }
    df.rename(columns=aliases, inplace=True)
    return df


@app.route("/upload_marks", methods=["POST"])
def upload_marks():
    if g := require_role("admin", "faculty"): return g
    file = request.files["file"]
    semester = int(request.form["semester"])
    if file:
        path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(path)
        try:
            df = _smart_read_excel(path)

            # Try to find roll_no column
            if "roll_no" not in df.columns:
                flash(f"❌ 'roll_no' column not found. Columns detected: {list(df.columns)}", "danger")
                return redirect("/admin")

            df["roll_no"] = df["roll_no"].astype(str).str.strip().str.upper()

            # Check required mark columns
            for col in ["sub1", "sub2", "sub3", "sub4", "sub5"]:
                if col not in df.columns:
                    flash(f"❌ '{col}' column not found. Columns detected: {list(df.columns)}", "danger")
                    return redirect("/admin")

            count = 0
            for _, row in df.iterrows():
                roll = row["roll_no"]
                if roll in ("", "NAN", "NONE"):
                    continue
                try:
                    marks = [float(row["sub1"]), float(row["sub2"]), float(row["sub3"]),
                             float(row["sub4"]), float(row["sub5"])]
                except (ValueError, TypeError):
                    continue
                sgpa = round((sum(marks) / 5) / 9.5, 2)
                existing = StudentMark.query.filter_by(roll_no=roll, semester=semester).first()
                if existing:
                    existing.sub1, existing.sub2, existing.sub3 = int(marks[0]), int(marks[1]), int(marks[2])
                    existing.sub4, existing.sub5, existing.sgpa = int(marks[3]), int(marks[4]), sgpa
                else:
                    db.session.add(StudentMark(roll_no=roll, semester=semester,
                        sub1=int(marks[0]), sub2=int(marks[1]), sub3=int(marks[2]),
                        sub4=int(marks[3]), sub5=int(marks[4]), sgpa=sgpa))
                count += 1

            for s in Student.query.all():
                sems = StudentMark.query.filter_by(roll_no=s.roll_no).all()
                if sems:
                    s.cgpa = round(sum(x.sgpa for x in sems) / len(sems), 2)

            db.session.commit()
            flash(f"✅ Marks uploaded successfully! {count} records processed.", "success")
        except Exception as e:
            flash(f"❌ Upload failed: {str(e)}", "danger")
    return redirect("/admin")


@app.route("/upload_students", methods=["POST"])
def upload_students():
    if g := require_role("admin"): return g
    file = request.files["file"]
    if file:
        path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(path)
        try:
            df = _smart_read_excel(path)

            if "roll_no" not in df.columns:
                flash(f"❌ 'roll_no' column not found. Columns detected: {list(df.columns)}", "danger")
                return redirect("/admin")

            added, skipped = 0, 0
            for _, row in df.iterrows():
                roll = str(row["roll_no"]).strip().upper()
                if roll in ("", "NAN", "NONE"):
                    continue
                if Student.query.get(roll):
                    skipped += 1
                    continue

                def safe_get(col, default=""):
                    return str(row[col]).strip() if col in row.index and str(row[col]) not in ("nan", "None", "") else default

                db.session.add(Student(
                    roll_no=roll,
                    name=safe_get("name", roll),
                    year=safe_get("year", "1st Year"),
                    grade=safe_get("grade", "B"),
                    backlogs=int(float(row["backlogs"])) if "backlogs" in row.index and str(row["backlogs"]) not in ("nan","None") else 0,
                    cgpa=0,
                    email=safe_get("email"),
                    phone=safe_get("phone"),
                    dept_id=safe_get("dept_id") or None,
                    dob=safe_get("dob"),
                    guardian_name=safe_get("guardian_name"),
                    guardian_phone=safe_get("guardian_phone"),
                    admission_date=safe_get("admission_date"),
                    fee_status=safe_get("fee_status", "Pending")
                ))
                db.session.add(User(username=roll, password=generate_password_hash("1234"), role="student"))
                added += 1

            db.session.commit()
            flash(f"✅ Upload complete! {added} students added, {skipped} already existed.", "success")
        except Exception as e:
            flash(f"❌ Upload failed: {str(e)}", "danger")
    return redirect("/admin")


# ─── FACULTY DASHBOARD ────────────────────────────────────────────────────────
@app.route("/faculty")
def faculty_dashboard():
    if g := require_role("faculty"): return g
    fid = session["user"]
    faculty = Faculty.query.get(fid)
    students = Student.query.all()
    notices = Notice.query.filter((Notice.target == "all") | (Notice.target == "faculty")).order_by(Notice.id.desc()).limit(5).all()
    my_courses = Course.query.filter_by(faculty_id=fid).all()
    return render_template("faculty_dashboard.html", faculty=faculty,
                           students=students, notices=notices, my_courses=my_courses)


@app.route("/faculty_profile")
def faculty_profile():
    if g := require_role("faculty"): return g
    fid = session["user"]
    faculty = Faculty.query.get(fid)
    dept = Department.query.get(faculty.dept_id) if faculty and faculty.dept_id else None
    return render_template("faculty_profile.html", faculty=faculty, dept=dept)


# ─── STUDENT DASHBOARD ────────────────────────────────────────────────────────
@app.route("/student")
def student_dashboard():
    if g := require_role("student"): return g
    roll = session["user"]
    student = Student.query.get(roll)
    marks = StudentMark.query.filter_by(roll_no=roll).all()
    notices = Notice.query.filter((Notice.target == "all") | (Notice.target == "student")).order_by(Notice.id.desc()).limit(5).all()
    att_records = Attendance.query.filter_by(roll_no=roll).all()
    total_att = len(att_records)
    present_att = sum(1 for r in att_records if r.status == "Present")
    att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0
    fees = FeeRecord.query.filter_by(roll_no=roll).all()
    dept = Department.query.get(student.dept_id) if student and student.dept_id else None
    return render_template("student_dashboard.html", student=student, marks=marks,
                           notices=notices, att_pct=att_pct, total_att=total_att,
                           present_att=present_att, fees=fees, dept=dept)


@app.route("/student_profile")
def student_profile():
    if g := require_role("student"): return g
    roll = session["user"]
    student = Student.query.get(roll)
    marks = StudentMark.query.filter_by(roll_no=roll).all()
    dept = Department.query.get(student.dept_id) if student and student.dept_id else None
    return render_template("student_profile.html", student=student, marks=marks, dept=dept)


# ─── RANK LIST ────────────────────────────────────────────────────────────────
@app.route("/rank")
def rank():
    if g := require_role("admin", "faculty"): return g
    students = Student.query.all()
    ranked = sorted(students, key=lambda x: (x.cgpa or 0), reverse=True)
    return render_template("rank.html", students=ranked)


# ─── API: Stats for charts ─────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    if g := require_role("admin"): return jsonify({"error": "unauthorized"}), 403
    dept_counts = {}
    for s in Student.query.all():
        key = s.dept_id or "Unknown"
        dept_counts[key] = dept_counts.get(key, 0) + 1
    return jsonify({"dept_counts": dept_counts,
                    "total_students": Student.query.count(),
                    "total_faculty": Faculty.query.count()})


if __name__ == "__main__":
    app.run(debug=True)
