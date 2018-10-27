from flask import (
    Blueprint, render_template, request, url_for, redirect
)
from werkzeug.exceptions import abort
import database

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
        db = database.Database()
        user_id = db.validate_session(session_token)
        if user_id:
            authorized = db.validate_permission(user_id, "view-event-log")
            if authorized:
                event_types = db.list_event_types()
                json_data = None
                csv_data = None
                html_data = None
                render_template("admin/admin_view_event_log.jinja2",
                                session_token=session_token,
                                event_types=event_types,
                                json_data=json_data,
                                csv_data=csv_data,
                                html_data=html_data)
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


