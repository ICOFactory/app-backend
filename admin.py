from flask import (
    Blueprint, render_template, request, url_for, redirect, current_app
)
from werkzeug.exceptions import abort
import database
import json
from hashlib import sha256
from users import UserContext
from smart_contract import SmartContract
import re

TOKEN_NAME_REGEX = re.compile("^[A-Za-z0-9]{4,36}$")
TOKEN_SYMBOL_REGEX = re.compile("^[A-Z0-9]{1,5}$")
TOKEN_COUNT_REGEX = re.compile("^[0-9]{1,16}$")


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


@admin_blueprint.route('/tokens/<session_token>')
def admin_tokens(session_token):
    if session_token:
        db = database.Database()
        db.logger = current_app.logger
        user_id = db.validate_session(session_token)
        ctx = UserContext(user_id, db=db, logger=db.logger)
        can_launch_ico = ctx.check_acl("launch-ico")
        can_launch_ico = True
        if can_launch_ico or len(ctx.acl()["management"]) > 0:
            owned_tokens = []
            for key in ctx.acl()["management"].keys():
                token_id = ctx.acl()["management"][key]["token_id"]
                token_info = db.get_smart_contract_info(token_id)
                owned_tokens.append(token_info)
            smart_contracts = db.get_smart_contracts(user_id)
            for each in smart_contracts:
                owned_tokens.append({"token_id": each["token_id"],
                                        "token_name": each["token_name"],
                                        "ico_tokens": each["tokens"],
                                        "token_symbol": each["token_symbol"],
                                        "eth_address": each["eth_address"]})
            if len(owned_tokens) == 0:
                owned_tokens = None
            return render_template("admin/admin_tokens.jinja2",
                                   session_token=session_token,
                                   owned_tokens=owned_tokens,
                                   can_launch_ico=can_launch_ico)
    abort(403)


@admin_blueprint.route('/tokens/create', methods=["POST"])
def create_tokens_form():
    session_token = request.form["session_token"]
    if session_token:
        db = database.Database()
        logger = current_app.logger
        user_id = db.validate_session(session_token)
        ctx = UserContext(user_id, db, logger)
        auth = ctx.check_acl("launch-ico")
        auth = True
        token_name = request.form['token_name']
        if not TOKEN_NAME_REGEX.match(token_name):
            return render_template("admin/admin_tokens.jinja2",
                                   session_token=session_token,
                                   create_token_error="Invalid token name, must consist of 4-36 alphanumeric characters only.")
        token_symbol = request.form['token_symbol']
        if len(token_symbol) > 0 and not TOKEN_SYMBOL_REGEX.match(token_symbol):
            return render_template("admin/admin_tokens.jinja2",
                                   session_token=session_token,
                                   create_token_error="Invalid token symbol, must consist of between 1-5 uppercase letters or numbers. This field is optional.")
        elif len(token_symbol) == 0:
            token_symbol = None
        token_count = request.form['token_count']
        if not TOKEN_COUNT_REGEX.match(token_count):
            return render_template("admin/admin_tokens.jinja2",
                                   session_token=session_token,
                                   create_token_error="Invalid inital token count value, must be a positive integer.")
        token_count = int(token_count)
        if auth:
            sc = SmartContract(token_name=token_name,
                               token_symbol=token_symbol,
                               token_count=token_count,
                               logger=current_app.logger,
                               owner_id=user_id)
            smart_contracts = db.get_smart_contracts(user_id)
            owned_contracts = []
            for each in smart_contracts:
                owned_contracts.append({"token_id": each["token_id"],
                                        "token_name": each["token_name"],
                                        "ico_tokens": each["tokens"],
                                        "token_symbol": each["token_symbol"],
                                        "eth_address": each["eth_address"]})
            return render_template("admin/admin_tokens.jinja2",
                                   session_token=session_token,
                                   owned_tokens=owned_contracts,
                                   can_launch_ico=True)

    abort(403)


@admin_blueprint.route('/tokens/view_source/<token_id>/<session_token>')
def admin_view_source(token_id,session_token):
    token_id = int(token_id)
    db = database.Database()
    db.logger = current_app.logger
    user_id = db.validate_session(session_token)
    if user_id and token_id > 0:
        token_info = db.get_smart_contract_info(token_id)
        if token_info["owner_id"] == user_id:
            sc = SmartContract(smart_token_id=token_id)
            return render_template("view_smart_contract.html",
                                   new_solidity_contract=sc.solidity_code)
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


@admin_blueprint.route('/users/<session_token>')
def view_users(session_token):
    if session_token:
        db = database.Database()
        db.logger = current_app.logger
        user_id = db.validate_session(session_token)
        if user_id:
            user_data = db.list_users()
            augmented_user_data = []
            for each_user in user_data:
                new_obj = dict(each_user)
                new_obj['transactions'] = 0
                new_obj['credits_balance'] = 0
                new_obj['member_tokens'] = 0
                new_obj['manager_tokens'] = 0
                new_obj['issued_tokens'] = 0
                new_obj['owned_tokens'] = 0
                augmented_user_data.append(new_obj)
            return render_template("admin/admin_users.jinja2",
                                   session_token=session_token,
                                   users=augmented_user_data)
