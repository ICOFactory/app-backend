from flask import (
    Blueprint, render_template, request, url_for, redirect, current_app
)
from werkzeug.exceptions import abort
import database
import json
from hashlib import sha256
from users import UserContext
from events import Event
import datetime
from ledger import TransactionLedger
from credits import Credits
from smart_contract import SmartContract
from charting import Charting
from mailer import Mailer
import re

TOKEN_NAME_REGEX = re.compile("^[A-Za-z0-9]{4,36}$")
TOKEN_SYMBOL_REGEX = re.compile("^[A-Z0-9]{1,5}$")
TOKEN_COUNT_REGEX = re.compile("^[0-9]{1,16}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$")

admin_blueprint = Blueprint('admin', __name__, url_prefix="/admin")

PAGE_LIMIT = 20
MOVING_AVERAGE_WINDOW = 100


@admin_blueprint.route('/')
def admin_no_session():
    return render_template("admin/admin_login.jinja2")


@admin_blueprint.route('/<session_token>/transactions')
def admin_main_transactions(session_token):
    return admin_main(session_token, transactions=True)


@admin_blueprint.route('/<session_token>')
def admin_main(session_token, transactions=False):
    db = database.Database(logger=current_app.logger)
    user_id = db.validate_session(session_token)
    if user_id:
        user_ctx = UserContext(user_id, db, current_app.logger)
        launch_ico = user_ctx.check_acl("launch-ico")
        onboard_users = user_ctx.check_acl("onboard-users")
        reset_passwords = user_ctx.check_acl("reset-passwords")
        ethereum_network = user_ctx.check_acl("ethereum-network")
        view_event_log = user_ctx.check_acl("view-event-log")
        issue_credits = user_ctx.check_acl("issue-credits")
        manager = len(user_ctx.acl()["administrator"]) > 0 or len(user_ctx.get_manager_tokens()) > 0
        if user_ctx.user_info["email_address"] == "admin":
            manager = True
        charting = Charting(db, logger=current_app.logger)
        eth_nodes = db.list_ethereum_nodes()

        epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
        node_gas_prices = {}
        moving_average_gas_price_data = charting.get_gas_price_moving_average(start=epoch)
        for node in eth_nodes:
            node_gas_prices[node["node_identifier"]] = charting.get_gas_price_for_node_id(node["id"], start=epoch)

        graphing_metrics = {
            "moving_average": {"gas_price": json.dumps(moving_average_gas_price_data)},
        }

        for each in node_gas_prices.keys():
            graphing_metrics[each] = json.dumps(node_gas_prices[each])

        cr = Credits(user_id, db, current_app.logger)

        return render_template("admin/admin_main.jinja2",
                               full_name=user_ctx.user_info['full_name'],
                               email_address=user_ctx.user_info['email_address'],
                               last_logged_in=user_ctx.user_info['last_logged_in'],
                               credits=cr.get_credit_balance(),
                               session_token=session_token,
                               launch_ico=launch_ico,
                               onboard_users=onboard_users,
                               reset_passwords=reset_passwords,
                               ethereum_network=ethereum_network,
                               view_event_log=view_event_log,
                               issue_credits=issue_credits,
                               manager=manager,
                               metrics=graphing_metrics)
    else:
        return render_template("admin/admin_login.jinja2", error="Invalid session.")


@admin_blueprint.route('/users/issue_credits/<user_id>/<session_token>')
def issue_credits(user_id, session_token):
    db = database.Database(logger=current_app.logger)
    auth_user_id = db.validate_session(session_token)
    if auth_user_id:
        auth_user_ctx = UserContext(auth_user_id, db, current_app.logger)
        if auth_user_ctx.check_acl("issue-credits"):
            user_info = db.get_user_info(user_id)
            return render_template("admin/admin_confirmation.jinja2",
                                   confirmation_type="issue-credits",
                                   confirmation_value=user_id,
                                   title="Issue Credits",
                                   confirmation_title="Issue Credits",
                                   confirmation_message="Issue credits to <span class=\"sky_blue\">{0}</span>?".format(
                                       user_info["email_address"]),
                                   issue_credits=True,
                                   choices=["Cancel"],
                                   default_choice="Issue Credits",
                                   session_token=session_token)
    abort(403)


@admin_blueprint.route('/users/reset-password/<user_id>/<session_token>')
def reset_password(user_id, session_token):
    user_id = int(user_id)
    if user_id < 1:
        raise ValueError
    db = database.Database()
    auth_user_id = db.validate_session(session_token)
    if auth_user_id:
        auth_user_ctx = UserContext(auth_user_id, db, current_app.logger)
        if auth_user_ctx.check_acl("reset-passwords"):
            user_info = db.get_user_info(user_id)
            return render_template("admin/admin_confirmation.jinja2",
                                   confirmation_type="reset-password",
                                   confirmation_value=user_id,
                                   title="Reset Password",
                                   confirmation_title="Reset Password",
                                   confirmation_message="Reset password for <span class=\"sky_blue\">{0}</span>?".format(
                                       user_info["email_address"]),
                                   new_password=True,
                                   choices=["Cancel"],
                                   default_choice="Reset Password",
                                   session_token=session_token)
    abort(403)


@admin_blueprint.route('/credits/purchase/<session_token>')
def purchase_credits(session_token):
    db = database.Database(logger=current_app.logger)
    user_id = db.validate_session(session_token)
    if user_id:
        return render_template("admin/purchase_credits.jinja2",
                               session_token=session_token)
    abort(403)


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        db = database.Database(logger=current_app.logger)
        session_data = db.login(username, password, request.access_route[-1])
        if session_data:
            return redirect(url_for("admin.admin_main", session_token=session_data[1]))
        else:
            return render_template("admin/admin_login.jinja2",
                                   error="Invalid email/password combination.")
    return render_template("admin/admin_login.jinja2")


@admin_blueprint.route('/users/recover_account')
def view_account_recovery():
    confirmation_message = "If your e-mail is in our database, you will receive an e-mail with "
    confirmation_message += "instructions on resetting your password"
    return render_template("admin/admin_confirmation.jinja2",
                           email_address=True,
                           title="Recover Account",
                           confirmation_type="recover_email",
                           confirmation_title="Recover your account",
                           confirmation_message=confirmation_message,
                           default_choice="Send E-mail",
                           choices=["Cancel"])


@admin_blueprint.route('/event_log/<session_token>')
def view_event_log(session_token):
    db = database.Database(logger=current_app.logger)
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

        db = database.Database(logger=current_app.logger)
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
                    csv_data = csv_data[:len(csv_data) - 1] + "\n"
                    for every_event in events:
                        event_row = ""
                        for every_key in event_keys:
                            event_row += str(every_event[every_key]) + ","
                        event_row += event_row[:len(event_row) - 1] + "\n"
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
    db = database.Database(logger=current_app.logger)
    user_id = db.validate_session(session_token)
    if user_id:
        authorized = db.validate_permission(user_id, "ethereum-network")
        if authorized:
            peer_data = {}
            syncing_status = {}
            update_node_event_type = Event("Ethereum Node Update", db, logger=current_app.logger)
            epoch = datetime.datetime.today() - datetime.timedelta(hours=24)
            nodes = db.list_ethereum_nodes()
            shortest_data_set = 0

            for each_node in nodes:
                peer_data[each_node["node_identifier"]] = []
                syncing_status[each_node["node_identifier"]] = []
                node_id = each_node["id"]
                updates = update_node_event_type.get_events_since(epoch, node_id)

                for each_update in updates:
                    if each_update[2] == node_id:
                        event_data = json.loads(each_update[0])
                        if event_data["synchronized"]:
                            peer_count = event_data["peers"]
                            peer_data[each_node["node_identifier"]].append(peer_count)
                            syncing_status[each_node["node_identifier"]].append({"count": 0,
                                                                                 "node_id": node_id})
                        else:
                            syncing_status[each_node["node_identifier"]].append({"count": event_data['blocks_behind'],
                                                                                 "node_id": node_id})
                # truncate the peer count data window to the shortest series to
                # make the charts look better
                if len(peer_data[each_node["node_identifier"]]) > 0:
                    if shortest_data_set == 0:
                        shortest_data_set = len(peer_data[each_node["node_identifier"]])
                    else:
                        if len(peer_data[each_node["node_identifier"]]) < shortest_data_set:
                            shortest_data_set = len(peer_data[each_node["node_identifier"]])

            peer_strings = {}
            for key in peer_data.keys():
                if len(syncing_status[key]) > 0:
                    syncing_status[key] = syncing_status[key][-1]
                peer_strings[key] = str(peer_data[key][:shortest_data_set])

            return render_template("admin/admin_eth_network.jinja2",
                                   session_token=session_token,
                                   eth_nodes=nodes,
                                   peer_data=peer_strings,
                                   blocks_behind=syncing_status)
    abort(403)


@admin_blueprint.route('/users/create/<session_token>')
def admin_create_user(session_token):
    db = database.Database(current_app.logger)
    user_id = db.validate_session(session_token)
    if user_id:
        authorized = db.validate_permission(user_id, "onboard-users")
        if authorized:
            smart_contracts = db.get_smart_contracts(user_id)
            if type(smart_contracts) is list and len(smart_contracts) > 0:
                return render_template("admin/admin_create_user.jinja2",
                                       session_token=session_token)
            else:
                return render_template("admin/admin_confirmation.jinja2",
                                       session_token=session_token,
                                       title="Error",
                                       confirmation_title="No ERC20 Tokens",
                                       confirmation_message="You must first create an ERC20 token before you can onboard users.",
                                       confirmation_type="no_erc20_tokens",
                                       default_choice="Create ERC20 Token")
    abort(403)


def get_owned_tokens(user_id, db, logger=None):
    smart_contracts = db.get_smart_contracts(user_id)
    owned_tokens = []
    for each in smart_contracts:
        pending = False
        if each["published"] is not None and each["eth_address"] is None:
            pending = True
        token_data = {"token_id": each["token_id"],
                      "token_name": each["token_name"],
                      "ico_tokens": each["tokens"],
                      "token_symbol": each["token_symbol"],
                      "eth_address": each["eth_address"],
                      "created": each["created"],
                      "published": each["published"],
                      "pending": pending,
                      "max_priority": each["max_priority"]}
        if not pending:
            sc = SmartContract(each["token_id"], logger=logger)
            token_data["issued_tokens"] = sc.get_issued_token_count()
            token_data["issued_not_confirmed"] = 0
            token_data["confirmed_not_assigned"] = 0
        owned_tokens.append(token_data)
    owned_tokens = sorted(owned_tokens, key=lambda token: token['created'], reverse=True)
    return owned_tokens


@admin_blueprint.route('/tokens/<session_token>')
def admin_tokens(session_token):
    if session_token:
        db = database.Database(logger=current_app.logger)
        user_id = db.validate_session(session_token)
        ctx = UserContext(user_id, db=db, logger=db.logger)
        can_launch_ico = ctx.check_acl("launch-ico")

        erc20_mined = Event("ERC20 Token Mined", db, logger=current_app.logger)
        mined_count = erc20_mined.get_event_count(user_id)
        mined_ids = []

        if mined_count:
            mined_erc20_events = erc20_mined.get_latest_events(mined_count, user_id)
            for each in mined_erc20_events:
                json_data = json.loads(each[0])
                token_id = json_data["token_id"]
                if token_id not in mined_ids:
                    mined_ids.append(token_id)

        erc20_published = Event("ERC20 Token Published", db, logger=current_app.logger)
        published_count = erc20_published.get_event_count(user_id)
        published_ids = []

        if published_count:
            published_erc20_events = erc20_published.get_latest_events(published_count, user_id)
            for each in published_erc20_events:
                json_data = json.loads(each[0])
                contract_address = json_data["contract_id"]
                if contract_address not in published_ids:
                    published_ids.append(contract_id)

        if can_launch_ico or len(ctx.acl()["management"]) > 0:
            owned_tokens = []
            for key in ctx.acl()["management"].keys():
                token_id = ctx.acl()["management"][key]["token_id"]
                token_info = db.get_smart_contract_info(token_id)
                owned_tokens.append(token_info)
            owned_tokens.extend(get_owned_tokens(user_id, db, current_app.logger))
            if len(owned_tokens) == 0:
                owned_tokens = None
            email_address = ctx.user_info["email_address"]
            last_logged_in = ctx.user_info["last_logged_in"].isoformat()
            last_logged_in_ip = ctx.user_info["last_logged_in_ip"]
            credit_ctx = Credits(user_id, db, current_app.logger)
            credit_balance = credit_ctx.get_credit_balance()
            if owned_tokens:
                for each in owned_tokens:
                    if each["token_id"] in published_ids:
                        each["published"] = True
                        each["pending"] = False
                    elif each["token_id"] in mined_ids:
                        each["published"] = True
                        each["pending"] = True
            return render_template("admin/admin_tokens.jinja2",
                                   session_token=session_token,
                                   owned_tokens=owned_tokens,
                                   can_launch_ico=can_launch_ico,
                                   email_address=email_address,
                                   last_logged_in=last_logged_in,
                                   last_logged_in_ip=last_logged_in_ip,
                                   credit_balance=credit_balance)
    abort(403)


@admin_blueprint.route('/confirm', methods=["POST"])
def admin_confirm():
    session_token = request.form["session_token"]
    confirmation_type = request.form["confirmation_type"]
    confirmation_val = request.form["confirmation_value"]
    choice = request.form["choice"]
    if confirmation_type == "recover_email":
        if choice == "Send E-mail":
            email_address = request.form['email_address']
            mailer = Mailer(email_address, request.access_route[-1], current_app.logger)
            mailer.recover_password()
            return render_template("admin/admin_login.jinja2", error="""
            If the e-mail address is in the database, instructions have been sent on how to recover 
            your password. Please check your spam/junk mail folder.
            """)
        return redirect(url_for('homepage'))
    elif confirmation_type == "no_erc20_tokens":
        return redirect(url_for('admin.admin_tokens', session_token=session_token))
    elif confirmation_type == "erc20_publish" and choice == "Cancel":
        return redirect(url_for('admin.admin_tokens', session_token=session_token))
    elif confirmation_type == "create_erc20_failed" and choice == "OK":
        return redirect(url_for('admin.admin_tokens', session_token=session_token))
    elif confirmation_type == "onboarded_new_user":
        if choice == "Administration":
            return redirect(url_for('admin.admin_main', session_token=session_token))
        else:
            return redirect(url_for('admin.create_user', session_token=session_token))
    elif confirmation_type == "reset-password":
        if choice == "Cancel":
            return redirect(url_for("admin.view_users", session_token=session_token, limit=PAGE_LIMIT, offset=0))
    elif confirmation_type == "acl_updated":
        if choice == "OK":
            return redirect(url_for("admin.view_users", session_token=session_token, limit=PAGE_LIMIT, offset=0))
    db = database.Database(logger=current_app.logger)
    user_id = db.validate_session(session_token)
    if user_id:
        user_ctx = UserContext(user_id, db, current_app.logger)
        if confirmation_type == "erc20_publish":
            token_id = int(confirmation_val)
            sc = SmartContract(smart_token_id=token_id)
            credits = Credits(user_id, db, logger=current_app.logger)
            if sc.smart_contract_id > 0:
                event_data = {"token_name": sc.token_name,
                              "token_symbol": sc.token_symbol,
                              "token_count": sc.tokens,
                              "token_id": sc.smart_contract_id,
                              "ip_address": request.access_route[-1]}
                if user_ctx.check_acl("launch-ico"):
                    credits_balance = credits.get_credit_balance()
                    if credits_balance >= credits.erc20_publish_price:
                        new_event = Event("ERC20 Token Mined", db, logger=current_app.logger)
                        event_id = new_event.log_event(user_id, event_data)
                        event_data["event_id"] = event_id
                        credits.debit(credits.erc20_publish_price, event_data)
                        command_id = db.post_command(json.dumps({"erc20_function":"publish",
                                                                 "token_name":sc.token_name,
                                                                 "token_symbol":sc.token_symbol,
                                                                 "token_count":sc.tokens}), 100)
                        if command_id:
                            return redirect(url_for("admin.admin_tokens", session_token=session_token))
                        else:
                            abort(500)
                    else:
                        credits.logger.error("Insufficient credits for ERC20 Publish: "
                                             + user_ctx.user_info["email_address"])
                abort(403)
        elif confirmation_type == "reset-password":
            user_id = int(confirmation_val)
            if request.form["password"] != request.form["repeat_password"]:
                return render_template("admin/admin_confirmation.jinja2",
                                       confirmation_type="reset-password",
                                       confirmation_value=user_id,
                                       title="Reset Password",
                                       confirmation_title="Reset Password",
                                       confirmation_message="Passwords must match both times.",
                                       new_password=True,
                                       choices=["Cancel"],
                                       default_choice="Reset Password",
                                       session_token=session_token)
            if db.reset_password(int(confirmation_val), request.form["password"]):
                return redirect(url_for("admin.view_users", session_token=session_token, limit=PAGE_LIMIT, offset=0))
        elif confirmation_type == "issue-credits":
            if choice == "Issue Credits" and user_ctx.check_acl("issue-credits"):
                user_credits = Credits(confirmation_val, db, current_app.logger)
                amount = int(request.form["credits"])
                # max issued credits 10,000
                if 0 < amount < 100000:
                    user_credits.issue_credits(amount, {"ip_addr": request.access_route[-1], "admin": user_id})
                    return redirect(
                        url_for("admin.view_users", session_token=session_token, limit=PAGE_LIMIT, offset=0))
                else:
                    raise ValueError

    abort(403)


@admin_blueprint.route('/users/new-user-acl', methods=["POST"])
def onboard_user():
    session_token = request.form["session_token"]
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        user_ctx = UserContext(user_id, db, current_app.logger)
        auth = user_ctx.check_acl("onboard-users")
        if auth:
            acl = json.loads(request.form["acl"])
            # TODO make sure the user is not issuing permissions they don't have themselves
            full_name = request.form["full_name"]
            email = request.form["email_address"]
            pw_hash = request.form["pw_hash"]
            ip_addr = request.access_route[-1]
            new_user_id = db.onboard_user(full_name, email, pw_hash, json.dumps(acl), ip_addr)
            if new_user_id:
                new_user_context = UserContext(new_user_id, db, current_app.logger)
                new_user_event = Event("Users Create User", db, current_app.logger)
                new_user_event.log_event(user_id, {"user_id": new_user_id,
                                                   "email": email,
                                                   "full_name": full_name,
                                                   "acl": json.dumps(acl)})

                db.update_user_permissions(new_user_id, json.dumps(acl))
                message = "Successfully created new user " + new_user_context.user_info["email_address"]
                return render_template("admin/admin_confirmation.jinja2",
                                       session_token=session_token,
                                       confirmation_type="onboarded_new_user",
                                       confirmation_title="Created New User",
                                       confirmation_message=message,
                                       default_choice="Create Another User",
                                       choices=["Administration"])
            else:
                abort(500)
    abort(403)


@admin_blueprint.route('/tokens/erc20_publish', methods=["POST"])
def erc20_publish():
    session_token = request.form["session_token"]
    token_id_form_field = request.form["token_id"]
    confirmation = request.form["confirmation"]
    db = database.Database()
    user_id = db.validate_session(session_token)
    if user_id:
        token_id = int(token_id_form_field)
        if token_id < 1:
            raise ValueError
        sc = SmartContract(smart_token_id=token_id)
        if sc.smart_contract_id < 1:
            abort(404)
        if confirmation == "true":
            credits = Credits(user_id, db, current_app.logger)
            current_balance = credits.get_credit_balance()
            if current_balance < credits.erc20_publish_price:
                message = "Your credit balance of <span class=\"credit_balance\">"
                message += str(current_balance) + "</span> is less than the <span class=\"credit_price\">"
                message += str(credits.erc20_publish_price) + "</span> required to publish an ERC20 token."
                message += "<p>[ <a class=\"login_anchor\" href=\"/admin/credits/purchase/"
                message += session_token + "\">purchase credits</a> ]</p>"
                return render_template("admin/admin_confirmation.jinja2",
                                       title="Unable to publice ERC20 contract",
                                       session_token=session_token,
                                       confirmation_value=token_id,
                                       confirmation_title="Insufficient Credits",
                                       confirmation_type="insufficient_credits",
                                       confirmation_message=message,
                                       default_choice="Cancel")
            message = "Are you sure you want to publish <em>" + sc.token_name + "</em> permanently to the Ethereum "
            message += "blockchain, costing <span class=\"credit_price\">"
            message += str(credits.erc20_publish_price) + "</span> credits?"
            return render_template("admin/admin_confirmation.jinja2",
                                   title="Confirm",
                                   session_token=session_token,
                                   confirmation_value=token_id,
                                   confirmation_title="Publish ERC20 contract?",
                                   confirmation_message=message,
                                   confirmation_type="erc20_publish",
                                   choices=["Cancel"],
                                   default_choice="Publish")


@admin_blueprint.route('/tokens/create', methods=["POST"])
def create_tokens_form():
    session_token = request.form["session_token"]
    if session_token:
        db = database.Database(logger=current_app.logger)
        logger = current_app.logger
        user_id = db.validate_session(session_token)
        ctx = UserContext(user_id, db, logger)
        auth = ctx.check_acl("launch-ico")
        token_name = request.form['token_name']
        if not TOKEN_NAME_REGEX.match(token_name):
            create_token_error = "Invalid token name, must consist of 4-36 alphanumeric characters only."
            return render_template("admin/admin_confirmation.jinja2",
                                   session_token=session_token,
                                   confirmation_title="Invalid ERC20 parameter(s)",
                                   confirmation_message=create_token_error,
                                   confirmation_type="create_erc20_failed",
                                   default_choice="OK")
        token_symbol = request.form['token_symbol']
        if len(token_symbol) > 0 and not TOKEN_SYMBOL_REGEX.match(token_symbol):
            create_token_error = "Invalid token symbol, must consist of between 1-5 uppercase letters or numbers. This field is optional."
            return render_template("admin/admin_confirmation.jinja2",
                                   session_token=session_token,
                                   confirmation_title="Invalid ERC20 parameter(s)",
                                   confirmation_message=create_token_error,
                                   confirmation_type="create_erc20_failed",
                                   default_choice="OK")
        elif len(token_symbol) == 0:
            token_symbol = None
        token_count = request.form['token_count']
        if not TOKEN_COUNT_REGEX.match(token_count):
            return render_template("admin/admin_confirmation.jinja2",
                                   session_token=session_token,
                                   confirmation_title="Invalid ERC20 parameter(s)",
                                   confirmation_message="Invalid initial token count value, must be a positive integer.",
                                   confirmation_type="create_erc20_failed",
                                   default_choice="OK")
        token_count = int(token_count)
        if auth:
            sc = SmartContract(token_name=token_name,
                               token_symbol=token_symbol,
                               token_count=token_count,
                               logger=current_app.logger,
                               owner_id=user_id)
            if sc.smart_contract_id > 0:
                new_event = Event("ERC20 Token Created", db, current_app.logger)
                new_event.log_event(user_id, {"ip_address": request.access_route[-1],
                                              "token_name": token_name,
                                              "token_symbol": token_symbol,
                                              "token_count": token_count,
                                              "token_id": sc.smart_contract_id,
                                              })
                return redirect(url_for("admin.admin_tokens", session_token=session_token))
            else:
                create_token_error = "Token with this name already managed by ERC20Master, to make things less "
                create_token_error += "confusing, please use a unique token name."
                return render_template("admin/admin_confirmation.jinja2",
                                       session_token=session_token,
                                       title="Error",
                                       confirmation_title="Token Name Exists",
                                       confirmation_message=create_token_error,
                                       confirmation_type="create_erc20_failed",
                                       default_choice="OK")
    abort(403)


@admin_blueprint.route('/tokens/view_source/<token_id>/<session_token>')
def admin_view_source(token_id, session_token):
    token_id = int(token_id)
    db = database.Database(logger=current_app.logger)
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
    if EMAIL_REGEX.match(email_address) is None:
        return render_template("admin/admin_create_user.jinja2",
                               session_token=session_token,
                               create_user_error="Invalid e-mail address.")
    if len(password) < 8:
        return render_template("admin/admin_create_user.jinja2",
                               session_token=session_token,
                               create_user_error="Password must be at least 8 characters in length.")
    if password == password_repeat:
        data = email_address + password
        pw_hash = sha256(data.encode("utf-8")).hexdigest()
    else:
        return render_template("admin/admin_create_user.jinja2",
                               session_token=session_token,
                               create_user_error="Password must match both times.")
    db = database.Database(current_app.logger)
    user_id = db.validate_session(session_token)
    ctx = UserContext(user_id, db, current_app.logger)
    if user_id:
        authorized = db.validate_permission(user_id, "onboard-users")
        if authorized:
            ip_addr = request.access_route[-1]
            result = db.create_user(full_name,
                                    email_address,
                                    password,
                                    ip_addr)
            if result:
                if result[0] == -1:
                    return render_template("admin/admin_create_user.jinja2",
                                           session_token=session_token,
                                           create_user_error="E-mail address already exists in the database.")
                else:
                    user_ctx = UserContext(result[0], db, current_app.logger)
                    # default permissions
                    user_ctx.add_permission("own-any-token")
                    user_ctx.add_permission("transfer-owned-token")

                    db.update_user_permissions(result[0], user_ctx.acl())

                    create_user_event = Event("Users Create User",
                                              db,
                                              logger=current_app.logger)
                    metadata = {"ip_addr": ip_addr,
                                "created_by": ctx.user_info['email_address'],
                                "new_user_email_address": email_address,
                                "new_user_id": result[0]}
                    create_user_event.log_event(user_id, json.dumps(metadata))

                    return render_template("admin/admin_create_user.jinja2",
                                           session_token=session_token,
                                           create_user_error="User created successfully.")
    abort(403)


@admin_blueprint.route('/users/change-permissions/<user_id>/<session_token>')
def change_user_permissions(user_id, session_token):
    user_id = int(user_id)
    db = database.Database()
    auth_user_id = db.validate_session(session_token)
    if auth_user_id:
        auth_ctx = UserContext(auth_user_id, db, current_app.logger)
        # TODO: there is a lot more granularity we could get here
        if auth_ctx.check_acl("change-permissions"):
            user_ctx = UserContext(user_id, db, current_app.logger)
            existing_acl = user_ctx.acl()
            return render_template("admin/admin_create_user_acl.jinja2",
                                   session_token=session_token,
                                   user_id=user_id,
                                   email_address=user_ctx.user_info['email_address'],
                                   existing_acl=json.dumps(existing_acl),
                                   new_user=False)
    abort(403)


@admin_blueprint.route('/users/change-user-acl', methods=["POST"])
def change_user_acl():
    session_token = request.form['session_token']
    acl_data = request.form['acl']
    db = database.Database()
    auth_user_id = db.validate_session(session_token)
    if auth_user_id:
        auth_user_ctx = UserContext(auth_user_id, db, current_app.logger)
        if auth_user_ctx.check_acl("change-permissions"):
            user_id = int(request.form['user_id'])
            user_ctx = UserContext(user_id, db, current_app.logger)
            user_event = Event("Users Changed Permissions", db, current_app.logger)
            event_data = {"email_address": user_ctx.user_info["email_address"],
                          "user_id": user_id,
                          "new_acl_data": acl_data}
            user_event.log_event(auth_user_id, event_data)
            result = db.update_user_permissions(user_id, json.loads(acl_data))
            if result:
                message = "Access Control List updated for " + user_ctx.user_info['email_address']
                return render_template("admin/admin_confirmation.jinja2",
                                       session_token=session_token,
                                       title="ACL Updated",
                                       confirmation_title="ACL Updated",
                                       confirmation_message=message,
                                       confirmation_type="acl_updated",
                                       default_choice="OK")
            else:
                abort(500)
    abort(403)


@admin_blueprint.route('/users/<user_id>/<session_token>/<offset>/<limit>')
def view_onboarded_users(user_id, session_token, offset=0, limit=20):
    if session_token:
        offset = int(offset)
        limit = int(limit)
        if offset < 0 or limit < 0:
            raise ValueError

        db = database.Database()
        db.logger = current_app.logger
        session_user_id = db.validate_session(session_token)
        if session_user_id == user_id:
            cu_event = Event("Users Create User", db, current_app.logger)
            cu_event_count = cu_event.get_event_count(user_id)
            all_cu_events = cu_event.get_latest_events(cu_event_count, user_id)
        else:
            abort(403)


@admin_blueprint.route('/users/<session_token>/<offset>/<limit>')
def view_users(session_token, offset=0, limit=20):
    if session_token:
        offset = int(offset)
        limit = int(limit)
        if offset < 0 or limit < 0:
            raise ValueError
        db = database.Database()
        db.logger = current_app.logger
        user_id = db.validate_session(session_token)
        if user_id:
            user_ctx = UserContext(user_id, db, current_app.logger)
            user_data = db.list_users(offset, limit)
            user_count = db.get_user_count()
            can_reset_password = user_ctx.check_acl("reset-passwords")
            can_change_permissions = user_ctx.check_acl("change-permissions")
            can_issue_credits = user_ctx.check_acl("issue-credits")
            can_view_wallet = user_ctx.check_acl("assign-tokens") or user_ctx.check_acl("remove-tokens")

            augmented_user_data = []
            for each_user in user_data:
                new_obj = dict(each_user)
                ledger = TransactionLedger(each_user['user_id'], db, current_app.logger)
                user_credits = Credits(each_user['user_id'], db, current_app.logger)
                new_obj['transactions'] = ledger.get_transaction_count()
                new_obj['credits_balance'] = user_credits.get_credit_balance()
                new_obj['owned_tokens'] = ledger.get_owned_token_count()
                augmented_user_data.append(new_obj)
            return render_template("admin/admin_users.jinja2",
                                   session_token=session_token,
                                   users=augmented_user_data,
                                   reset_password=can_reset_password,
                                   change_permissions=can_change_permissions,
                                   issue_credits=can_issue_credits,
                                   view_wallet=can_view_wallet,
                                   user_count=user_count,
                                   limit=limit,
                                   offset=offset)
