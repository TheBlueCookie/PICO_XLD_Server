from multiprocessing import Process
from flask import Flask, request, render_template, redirect, url_for, flash
import flask_login
from flask_login import LoginManager, UserMixin
import json

from tempcomm import XLDTempHandler
from database_sqlite import ServerDB
from passkey import key, users, blueftc_ip

db = ServerDB()
db.prep_tables()

tccontrol = XLDTempHandler(database=db, ip=blueftc_ip, update_interval=60)

app = Flask(__name__)
app.secret_key = key

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id):
        self.id = id


def exec_flask():
    app.run()

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route("/meas/register", methods=['POST'])
def meas_reg():
    cont = json_request_handler()
    token = db.register_measurement(user=cont['user'], group=cont['group'])

    return json.dumps({'id': token})


@app.route("/meas/deregister", methods=['POST'])
def meas_dereg():
    cont = json_request_handler()
    db.deregister_measurement(meas_id=cont['id'])

    return json.dumps({'deregistered': True})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("username")
        entered_password = request.form.get("password")
        if user_id in users and users[user_id]['password'] == entered_password:
            user = User(user_id)
            flask_login.login_user(user)
            flash('Login successful', 'Success!')
            return redirect('/')

        flash('Login failed!')

    return render_template("login.html")


@app.route('/meas/status', methods=['GET', 'POST'])
@flask_login.login_required
def meas_status_get():
    if request.method == 'GET':
        return render_template('measurements.html', measurements=db.get_html_meas_dict())

    else:
        if request.form['go button'] == 'set go':
            db.set_all_meas_to_go()

        flash("All signal flags set to GO")
        return render_template('measurements.html', measurements=db.get_html_meas_dict())


@app.route('/meas/status/set', methods=['POST'])
def meas_status_set_post():
    payload = json_request_handler()
    db.set_meas_status(meas_id=payload['id'], status=payload['running'])

    return json.dumps({'running': True})


@app.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    flash('Logged out!')
    return redirect('/')


@app.route("/control", methods=["GET", "POST"])
@flask_login.login_required
def control():
    if request.method == "POST":
        new_power = request.form.get("power")
        heater_id = request.form.get("heater select")
        if heater_id == 'still':
            db.write_heater(index=db.still_ind, val=float(new_power))

    return render_template("control.html", powers=get_all_powers(), temps=get_all_temps())


@app.route('/temps/base', methods=['GET'])
def get_temps():
    return json.dumps({'base temp': db.read_temp(channel=db.mxc_ch)})


@app.route('/meas/signal', methods=['POST'])
def get_meas_signal():
    payload = json_request_handler()

    return json.dumps({'signal': db.get_meas_signal(payload['id'])})


@app.route('/', methods=['GET'])
def index():
    return render_template('home.html', temps=get_all_temps(), powers=get_all_powers())


def json_request_handler():
    if request.is_json:
        return request.json

    else:
        return


def get_all_temps():
    temps = {'mxc': db.read_temp(db.mxc_ch),
             'still': db.read_temp(db.still_ch),
             'four_k': db.read_temp(db.fourk_ch),
             'fifty_k': db.read_temp(db.fiftyk_ch)}

    return temps


def get_all_powers():
    powers = {'mxc': db.read_heater(db.mxc_ind),
              'still': db.read_heater(db.still_ind),
              'mxc_switch': db.read_heater(db.mxc_switch_ind),
              'still_switch': db.read_heater(db.still_switch_ind)}

    return powers


flask_server = Process(target=exec_flask, name='Flask Process')
tc_process = Process(target=tccontrol.exec, name='Temp Controller')

if __name__ == "__main__":
    flask_server.start()
    tc_process.start()
