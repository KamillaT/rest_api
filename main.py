# -*- coding: utf8 -*-
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import Flask, redirect, render_template, request, abort, make_response, jsonify
from data import db_session, users, jobs, departments
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired
import jobs_api, users_api
import requests
from requests import get
import sys


def set_geocoder_params(toponym_to_find):
    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": toponym_to_find,
        "format": "json"}
    return geocoder_params


def set_map_params(toponym_coords):
    map_params = {
        "ll": ','.join(toponym_coords.split()),
        "l": "sat",
        "z": 13}
    return map_params


class LoginForm(FlaskForm):
    email = StringField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    login = StringField("Login / email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_again = PasswordField("Repeat password", validators=[DataRequired()])
    surname = StringField("Surname", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    age = StringField("Age", validators=[DataRequired()])
    position = StringField("Position", validators=[DataRequired()])
    speciality = StringField("Speciality", validators=[DataRequired()])
    address = StringField("Address", validators=[DataRequired()])
    hometown = StringField("Hometown", validators=[DataRequired()])
    submit = SubmitField("Submit")


class AddJob(FlaskForm):
    job_title = StringField("Job Title", validators=[DataRequired()])
    team_leader = IntegerField("Team Leader ID", validators=[DataRequired()])
    work_size = IntegerField("Work Size", validators=[DataRequired()])
    collaborators = StringField("Collaborators", validators=[DataRequired()])
    is_finished = BooleanField("Is job finished?")
    submit = SubmitField("Submit")


class AddDepartment(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    chief = IntegerField("Chief", validators=[DataRequired()])
    members = StringField("Members", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    submit = SubmitField("Submit")


def find_toponym(toponym_to_find):
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
    geocoder_params = set_geocoder_params(toponym_to_find)
    response = requests.get(geocoder_api_server, params=geocoder_params)
    if not response:
        print("Ошибка выполнения запроса")
        print("Http status:", response.status_code, '(', response.reason, ')')
        sys.exit(1)

    json_response = response.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    toponym_coords = toponym["Point"]["pos"]
    print("coords", toponym_coords)
    return toponym_coords


def getImage(toponym_coords, surname):
    map_api_server = "http://static-maps.yandex.ru/1.x/"
    map_params = set_map_params(toponym_coords)
    response = requests.get(map_api_server, params=map_params)
    if not response:
        print("Ошибка выполнения запроса:")
        print("Http status:", response.status_code, '(', response.reason, ')')
        sys.exit(1)
    with open(f"static/img/hometown_{surname}.jpg", "wb") as file:
        file.write(response.content)
        print("done")


app = Flask(__name__)
app.config["SECRET_KEY"] = "yandexlyceum_secret_key"

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(users.User).get(user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(users.User).filter(users.User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template("login.html", message="Неправильный логин или пароль", form=form,
                               current_user=current_user)
    return render_template("login.html", form=form, current_user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template("register.html", form=form, message="Пароли не совпадают", current_user=current_user)
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.email == form.login.data).first():
            return render_template("register.html", form=form, message="Такой пользователь уже есть",
                                   current_user=current_user)
        user = users.User(
            email=form.login.data,
            surname=form.surname.data,
            name=form.name.data,
            age=int(form.age.data),
            position=form.position.data,
            speciality=form.speciality.data,
            address=form.address.data,
            city_from=form.hometown.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template("register.html", form=form, current_user=current_user)


@app.route("/add_job", methods=["GET", "POST"])
@login_required
def add_job():
    form = AddJob()
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.id == form.team_leader.data).first():
            job = jobs.Jobs(
                team_leader=form.team_leader.data,
                job=form.job_title.data,
                work_size=form.work_size.data,
                collaborators=form.collaborators.data,
                is_finished=form.is_finished.data
            )
            session.add(job)
            session.commit()
            return redirect('/')
        return render_template("addjob.html", form=form, message="Несуществующий лидер", current_user=current_user,
                               title="Adding a Job")
    return render_template("addjob.html", form=form, current_user=current_user, title="Adding a Job")


@app.route("/edit_job/<int:id>", methods=["GET", "POST"])
@login_required
def edit_job(id):
    form = AddJob()
    if request.method == "GET":
        session = db_session.create_session()
        job = session.query(jobs.Jobs).filter(jobs.Jobs.id == id,
                                              (jobs.Jobs.user == current_user) | (current_user.id == 1)).first()
        if job:
            form.job_title.data = job.job
            form.team_leader.data = job.team_leader
            form.work_size.data = job.work_size
            form.collaborators.data = job.collaborators
            form.is_finished.data = job.is_finished
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        job = session.query(jobs.Jobs).filter(jobs.Jobs.id == id,
                                              (jobs.Jobs.user == current_user) | (current_user.id == 1)).first()
        if job:
            job.job = form.job_title.data
            job.team_leader = form.team_leader.data
            job.work_size = form.work_size.data
            job.collaborators = form.collaborators.data
            job.is_finished = form.is_finished.data
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template("addjob.html", title="Edit Job", form=form)


@app.route("/job_delete/<int:id>", methods=["POST", "GET"])
@login_required
def job_delete(id):
    session = db_session.create_session()
    job = session.query(jobs.Jobs).filter(jobs.Jobs.id == id,
                                          (jobs.Jobs.user == current_user) | (current_user.id == 1)).first()
    if job:
        session.delete(job)
        session.commit()
    else:
        abort(404)
    return redirect('/')


@app.route("/add_department", methods=["POST", "GET"])
@login_required
def add_department():
    form = AddDepartment()
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(users.User).filter(users.User.id == form.chief.data).first():
            department = departments.Department(
                title=form.title.data,
                chief=form.chief.data,
                members=form.members.data,
                email=form.email.data
            )
            session.add(department)
            session.commit()
            return redirect('/')
        return render_template("add_department.html", form=form, title="Add a Department",
                               message="Несуществующий лидер")
    return render_template("add_department.html", form=form, title="Add a Department")


@app.route("/edit_department/<int:id>", methods=["GET", "POST"])
@login_required
def edit_department(id):
    form = AddDepartment()
    if request.method == "GET":
        session = db_session.create_session()
        department = session.query(departments.Department).filter(departments.Department.id == id,
                                                                  (departments.Department.user == current_user) | (
                                                                          current_user.id == 1)).first()
        if department:
            form.title.data = department.title
            form.chief.data = department.chief
            form.members.data = department.members
            form.email.data = department.email
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        department = session.query(departments.Department).filter(departments.Department.id == id,
                                                                  (departments.Department.user == current_user) | (
                                                                          current_user.id == 1)).first()
        if department:
            department.title = form.title.data
            department.chief = form.chief.data
            department.members = form.members.data
            department.email = form.email.data
            session.commit()
            return redirect("/departments")
        else:
            abort(404)
    return render_template("add_department.html", title="Edit Department", form=form)


@app.route("/department_delete/<int:id>")
@login_required
def department_delete(id):
    session = db_session.create_session()
    department = session.query(departments.Department).filter(departments.Department.id == id,
                                                              (departments.Department.user == current_user) | (
                                                                      current_user.id == 1)).first()
    if department:
        session.delete(department)
        session.commit()
    else:
        abort(404)
    return redirect("/departments")


@app.route("/users_show/<int:user_id>", methods=["GET"])
def user_city(user_id):
    user = get(f"http://localhost:8080/api/users/{user_id}").json()
    print(user)
    town = user["user"]["city_from"]
    print(town)
    town_coords = find_toponym(town)
    getImage(town_coords, user["user"]["surname"])
    return render_template("hometown.html", user=user, surname=user["user"]["surname"])


@app.route('/')
def table():
    session = db_session.create_session()
    jobs_ = session.query(jobs.Jobs).all()
    return render_template("tables.html", jobs=jobs_, current_user=current_user)


@app.route("/departments")
def dprt_table():
    session = db_session.create_session()
    departments_ = session.query(departments.Department).all()
    return render_template("departments.html", departments=departments_, current_user=current_user)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)


if __name__ == "__main__":
    db_session.global_init("db/mars.sqlite")
    app.register_blueprint(jobs_api.blueprint)
    app.register_blueprint(users_api.blueprint)
    app.run(port=8080, host="127.0.0.1")
