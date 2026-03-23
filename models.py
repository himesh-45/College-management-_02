from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Department(db.Model):
    __tablename__ = 'department'
    dept_id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hod = db.Column(db.String(100))
    established = db.Column(db.String(10))
    total_seats = db.Column(db.Integer, default=60)


class Student(db.Model):
    __tablename__ = 'student'
    roll_no = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    year = db.Column(db.String(10))
    grade = db.Column(db.String(10))
    backlogs = db.Column(db.Integer, default=0)
    cgpa = db.Column(db.Float, default=0.0)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    dept_id = db.Column(db.String(20), db.ForeignKey('department.dept_id'), nullable=True)
    dob = db.Column(db.String(20))
    address = db.Column(db.Text)
    guardian_name = db.Column(db.String(100))
    guardian_phone = db.Column(db.String(20))
    admission_date = db.Column(db.String(20))
    fee_status = db.Column(db.String(20), default='Pending')


class Faculty(db.Model):
    __tablename__ = 'faculty'
    faculty_id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    branch = db.Column(db.String(50))
    salary = db.Column(db.Integer)
    performance = db.Column(db.String(50))
    specialization = db.Column(db.String(200))
    achievements = db.Column(db.Text)
    dept_id = db.Column(db.String(20), db.ForeignKey('department.dept_id'), nullable=True)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    qualification = db.Column(db.String(100))
    joining_date = db.Column(db.String(20))


class StudentMark(db.Model):
    __tablename__ = 'student_mark'
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20))
    semester = db.Column(db.Integer)
    sub1 = db.Column(db.Integer)
    sub2 = db.Column(db.Integer)
    sub3 = db.Column(db.Integer)
    sub4 = db.Column(db.Integer)
    sub5 = db.Column(db.Integer)
    sgpa = db.Column(db.Float)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), db.ForeignKey('student.roll_no'))
    date = db.Column(db.String(20))
    subject = db.Column(db.String(100))
    status = db.Column(db.String(10))


class Course(db.Model):
    __tablename__ = 'course'
    course_id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100))
    dept_id = db.Column(db.String(20), db.ForeignKey('department.dept_id'))
    credits = db.Column(db.Integer)
    semester = db.Column(db.Integer)
    faculty_id = db.Column(db.String(20), db.ForeignKey('faculty.faculty_id'), nullable=True)


class FeeRecord(db.Model):
    __tablename__ = 'fee_record'
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), db.ForeignKey('student.roll_no'))
    amount = db.Column(db.Float)
    paid_date = db.Column(db.String(20))
    fee_type = db.Column(db.String(50))
    transaction_id = db.Column(db.String(50))
    remarks = db.Column(db.String(200))


class Notice(db.Model):
    __tablename__ = 'notice'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    posted_by = db.Column(db.String(100))
    posted_on = db.Column(db.String(30))
    category = db.Column(db.String(50))
    target = db.Column(db.String(20), default='all')


class Timetable(db.Model):
    __tablename__ = 'timetable'
    id = db.Column(db.Integer, primary_key=True)
    dept_id = db.Column(db.String(20))
    year = db.Column(db.String(10))
    day = db.Column(db.String(20))
    period = db.Column(db.Integer)
    subject = db.Column(db.String(100))
    faculty_id = db.Column(db.String(20))
    time_slot = db.Column(db.String(30))


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))
