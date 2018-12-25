from flask import Flask, request, render_template, current_app, url_for, redirect
from json_parser import JSONProcessor
from database import Database
from charting import Charting
import datetime
import json
import node_api
import admin
import users
import events

app = Flask(__name__)
app.register_blueprint(admin.admin_blueprint)
app.register_blueprint(node_api.node_api_blueprint)


@app.route('/')
def homepage():
    db = Database()
    charting = Charting(db, current_app.logger)
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    moving_average = charting.get_gas_price_moving_average(start=epoch)
    chart_data = []
    for each in moving_average:
        chart_data.append(each[1])

    error_msg = "No charting data for period {0}-{1}".format(epoch.isoformat(),
                                                             datetime.datetime.now().isoformat())
    if len(moving_average) == 0:
        return render_template("main.jinja2",
                               error=error_msg)
    return render_template("main.jinja2",
                           metrics={"chart_data": {"gas_price": chart_data}},
                           first_block=moving_average[0][0])


@app.route('/<session_token>')
def logged_in_homepage(session_token):
    db = Database(logger=current_app.logger)
    user_id = db.validate_session(session_token)
    charting = Charting(db, current_app.logger)
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    moving_average = charting.get_gas_price_moving_average(start=epoch)
    chart_data = []
    for each in moving_average:
        chart_data.append(each[1])

    first_block = 0
    if len(moving_average) > 0:
        first_block = moving_average[0][0]
    # if user is logged in
    if user_id:
        user_ctx = users.UserContext(user_id,
                                     db=db,
                                     logger=current_app.logger)
        user_can_create_erc20_token = user_ctx.check_acl("launch-ico")
        user_owned_tokens = user_ctx.get_member_tokens()
        user_managed_tokens = user_ctx.get_manager_tokens()

        return render_template("main.jinja2",
                               user_info=user_ctx.user_info,
                               metrics={"chart_data": {"gas_price": chart_data}},
                               launch_ico=user_can_create_erc20_token,
                               owned_tokens=user_owned_tokens,
                               managed_tokens=user_managed_tokens,
                               first_block=first_block,
                               session_token=session_token)
    else:
        return render_template("main.jinja2",
                               metrics={"chart_data": {"gas_price": chart_data}},
                               first_block=moving_average[0][0],
                               login_error="Invalid session.")


@app.route('/logout/<session_token>')
def logout_user(session_token):
    db = Database(logger=current_app.logger)
    user_id = db.validate_session(session_token)
    if user_id:
        db.logout(user_id)
    return redirect(url_for("homepage"))


@app.route('/create_user', methods=["GET", "POST"])
def homepage_create_user():
    if request.method == "POST":
        if request.form["passwd"] == request.form["passwd_repeat"]:
            user_passwd = request.form["passwd"]
            db = Database()
            result = db.create_user("",
                                    request.form['email_address'],
                                    user_passwd,
                                    request.access_route[-1])
            if result:
                if result[0] == -1:
                    error = "User with this e-mail address already exists."
                    return render_template("create_user.jinja2", error_msg=error)
                session_id = result[1]
                # log event
                create_user_event = events.Event("Users Create User",
                                                 db,
                                                 logger=current_app.logger)
                metadata = {"ip_addr":request.access_route[-1]}
                create_user_event.log_event(result[0], json.dumps(metadata))

                user_ctx = users.UserContext(result[0], db=db, logger=current_app.logger)
                # TODO: add all the default permissions
                return redirect(url_for("logged_in_homepage", session_token=session_id))
        else:
            error = "Passwords did not match."
            return render_template("create_user.jinja2", error_msg=error)

    return render_template("create_user.jinja2")


@app.route('/login', methods=["POST"])
def login():
    if request.form['submit_button'] == "Create Account":
        return redirect(url_for("homepage_create_user"))
    db = Database()
    logged_in_user = db.login(request.form["email_address"],request.form["password"],request.access_route[-1])
    if logged_in_user:
        return redirect(url_for("admin.admin_main", session_token=logged_in_user[1]))
    else:
        charting = Charting(db, current_app.logger)
        epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
        moving_average = charting.get_gas_price_moving_average(start=epoch)
        chart_data = []
        first_block = 0
        if len(moving_average) > 0:
            first_block = moving_average[0][0]
        for each in moving_average:
            chart_data.append(each[1])
        return render_template("main.jinja2",
                               metrics={"chart_data": {"gas_price": chart_data}},
                               first_block=first_block,
                               login_error="Invalid e-mail address/password combination.")


@app.route('/utilization')
def homepage_utilization():
    db = Database()
    charting = Charting(db, current_app.logger)
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    utilization = charting.get_utilization_per_block(start=epoch)
    chart_data = []
    for each in utilization:
        chart_data.append(each[1])
    first_block = 0
    if len(utilization) > 0:
        first_block = utilization[0][0]
    return render_template("main.jinja2",
                           metrics={"chart_data": {"utilization": chart_data}},
                           first_block=first_block)


@app.route('/block_size')
def homepage_block_size():
    db = Database()
    charting = Charting(db, current_app.logger)
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    block_size_per_block = charting.get_block_size_per_block(start=epoch)
    chart_data = []
    for each in block_size_per_block:
        chart_data.append(each[1])
    first_block = 0
    if len(block_size_per_block) > 0:
        first_block = block_size_per_block[0][0]
    return render_template("main.jinja2",
                           metrics={"chart_data": {"block_size": chart_data}},
                           first_block=first_block)


@app.route('/transaction_count')
def home_page_transaction_count():
    db = Database()
    charting = Charting(db, current_app.logger)
    epoch = datetime.datetime.now() - datetime.timedelta(hours=24)
    transaction_count = charting.get_transactions_per_block(start=epoch)
    chart_data = []
    for each in transaction_count:
        chart_data.append(each[1])
    first_block = 0
    if len(transaction_count) > 0:
        first_block = transaction_count[0][0]
    return render_template("main.jinja2",
                           metrics={"chart_data": {"transaction_count": chart_data}},
                           first_block=first_block)


@app.route('/json', methods=['POST'])
def json_endpoint():
    json_data = request.get_json(force=True)
    request_data = {"ip_address": request.access_route[-1]}
    jp = JSONProcessor(json_data, request_data)
    jp.logger = app.logger
    if jp.response:
        return json.dumps(jp.response)
    elif jp.error:
        if "errorCode" in jp.error:
            app.logger.error("Error Code: {0} ({1})".format(jp.error["errorCode"], jp.error["error"]))
        else:
            app.logger.error(jp.error.error)
        return json.dumps(jp.error)
    else:
        error_obj = {"success": False,
                     "errorCode": 0,
                     "error": "Unknown error."}
        json.dumps(error_obj)
