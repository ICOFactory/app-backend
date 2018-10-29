from flask import (
    Blueprint, render_template, request, url_for, redirect
)
from werkzeug.exceptions import abort
import database
import json
from hashlib import sha256

admin_blueprint = Blueprint('admin', __name__, url_prefix="/admin")


@admin_blueprint.route('/')
def admin_no_session():
    return render_template("admin/admin_login.jinja2")


@admin_blueprint.route('/<session_token>')
def admin_main(session_token):
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        admin_permissions = db.list_permissions(user_id)
        if len(admin_permissions) > 0:
            return render_template("admin/admin_main.jinja2",
                                   session_token=session_token,
                                   admin_permissions=admin_permissions)
    return render_template("admin/admin_login.jinja2",
                           error="Invalid session.")


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        db = database.Database()
        session_data = db.login(username, password, request.remote_addr)
        if session_data:
            return redirect(url_for("admin.admin_main", session_token=session_data[1]))
        else:
            return render_template("admin/admin_login.jinja2",
                                   error="Invalid email/password combination.")
    return render_template("admin/admin_login.jinja2")


@admin_blueprint.route('/event_log/<session_token>')
def view_event_log(session_token):
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        authorized = db.validate_permission(user_id, "view-event-log")
        if authorized:
            event_types = db.list_event_types()
            return render_template("admin/admin_view_event_log.jinja2",
                            session_token=session_token,
                            event_types=event_types)
    abort(403)


@admin_blueprint.route('/event_log/filter', methods=['GET', 'POST'])
def filter_event_log():
    if request.method == "POST":

        session_token = request.form['session_token']
        output_format = request.form['output_format']
        event_limit = int(request.form['event_limit'])
        event_filters = request.form.getlist('event_filter')
        db = database.Database()
        user_id = db.validate_session(session_token)
        if user_id:
            authorized = db.validate_permission(user_id, "view-event-log")
            if authorized:
                event_types = db.list_event_types()
                events = []
                for each in event_filters:
                    event_type_id = int(each)
                    event_type_name = None
                    for every_type in event_types:
                        if every_type["event_type_id"] == event_type_id:
                            event_type_name = every_type["event_type_name"]
                            break
                    events_of_type = db.get_latest_events(event_type_id, event_limit)
                    for each_event in events_of_type:
                        new_event_obj = dict(each_event)
                        new_event_obj["event_type"] = event_type_name
                        events.append(new_event_obj)

                events = sorted(events, key=lambda event: event['event_id'])
                events.reverse()
                for every_event in events:
                    every_event['event_created'] = every_event['event_created'].isoformat()
                events = events[:event_limit]
                json_data = None
                if output_format == "json":
                    json_data = json.dumps(events)
                csv_data = None
                if output_format == "csv" and len(events) > 0:
                    event_keys = events[0].keys()
                    csv_data = ""
                    for every_key in event_keys:
                        csv_data += every_key + ","
                    csv_data = csv_data[:len(csv_data)-1] + "\n"
                    for every_event in events:
                        event_row = ""
                        for every_key in event_keys:
                            event_row += str(every_event[every_key]) + ","
                        event_row += event_row[:len(event_row)-1] + "\n"
                        csv_data += event_row
                html_data = None
                if output_format == "html":
                    html_data = events
                return render_template("admin/admin_view_event_log.jinja2",
                                       session_token=session_token,
                                       event_types=event_types,
                                       json_data=json_data,
                                       csv_data=csv_data,
                                       html_data=html_data,
                                       event_filters=event_filters)
        else:
            abort(403)
    abort(500)


@admin_blueprint.route('/eth_network/<session_token>')
def eth_network_admin(session_token):
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        authorized = db.validate_permission(user_id, "ethereum-network")
        if authorized:
            eth_nodes = db.list_ethereum_nodes()
            return render_template("admin/admin_eth_network.jinja2",
                                   session_token=session_token,
                                   eth_nodes=eth_nodes)
    abort(403)


@admin_blueprint.route('/users/create/<session_token>')
def admin_create_user(session_token):
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        authorized = db.validate_permission(user_id, "onboard-users")
        if authorized:
            return render_template("admin/admin_create_user.jinja2",
                                   session_token=session_token)
    abort(403)


@admin_blueprint.route('/users/create', methods=["POST"])
def admin_create_user_acl():
    session_token = request.form["session_token"]
    full_name = request.form["full_name"]
    email_address = request.form["email_address"]
    password = request.form["password"]
    password_repeat = request.form["password_repeat"]
    if password == password_repeat:
        data = email_address + password
        pw_hash = sha256(data.encode("utf-8"))
    else:
        return render_template("admin/admin_create_user.jinja2",
                               session_token=session_token,
                               error="Password must match both times.")
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        authorized = db.validate_permission(user_id, "onboard-users")
        if authorized:
            return render_template("admin/admin_create_user_acl.jinja2",
                                   session_token=session_token,
                                   full_name=full_name,
                                   email_address=email_address,
                                   password_hash=pw_hash)
    abort(403)