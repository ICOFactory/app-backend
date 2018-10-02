from flask import Flask, request, render_template, Response, abort
from json_parser import JSONProcessor
from database import Database
import json
import uuid

app = Flask(__name__)


def verify_admin(user_info):
    if user_info['email_address'] == "admin":
        return True
    return False


@app.route('/admin/glosspoints/<session_token>')
def glosspoints_admin(session_token):
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            if verify_admin(db.get_user_info(session_id)):
                config_data = json.load(open("config.json","r"))
                contract_address = config_data['contract_address']
                return render_template("glosspoints.html",
                                       session_token=session_token,
                                       contract_address=contract_address)


@app.route('/admin/', methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        db = Database()
        db.logger = app.logger
        login_info = db.login(request.form["username"], request.form["password"],request.remote_addr)
        if login_info:
            return render_template("admin.html", session_token=login_info[1])
    return render_template("login.html")


@app.route('/admin/users/<session_token>')
def users_admin_page(session_token):
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            all_users = db.list_users()
            return render_template("users.html", users=all_users, session_token=session_token)
    return render_template("login.html", error="Invalid session.")


@app.route('/admin/<session_token>')
def admin_page(session_token):
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            return render_template("admin.html", session_token=session_token)
    return render_template("login.html", error="Invalid session.")


@app.route('/admin/reset-password/<user_id>/<session_token>')
def admin_reset_password(user_id, session_token):
    # TODO: handle POST request from form
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            user_info = db.get_user_info(user_id)
            if user_info:
                return render_template("reset_password.html",
                                       session_token=session_token,
                                       email=user_info['email_address'],
                                       last_logged_in=user_info['last_logged_in'])
            else:
                abort(Response("Couldn't get user info for user_id: {0}".format(user_id)))


@app.route('/json', methods=['POST'])
def json_endpoint():
    json_data = request.get_json(force=True)
    request_data = {"ip_address": request.remote_addr}
    jp = JSONProcessor(json_data, request_data)
    jp.logger = app.logger
    if jp.response:
        return json.dumps(jp.response)
    elif jp.error:
        if "errorCode" in jp.error:
            app.logger.error("Error Code: {0} ({1})".format(jp.error["errorCode"],jp.error["error"]))
        else:
            app.logger.error(jp.error.error)
        return json.dumps(jp.error)
    else:
        error_obj = {"success": False,
                     "errorCode": 0,
                     "error": "Unknown error."}
        json.dumps(error_obj)


@app.route('/upload', methods=['POST', 'GET'])
def upload_form():
    if request.method == 'POST':
        db = Database()
        db.logger = app.logger
        result = db.device_info(request.form['uuid'])
        if Device.UUID_REGEX.match(result):
            device_id = result
            new_filename = str(uuid.uuid4()) + ".jpg"
            if 'frame_image' in request.files:
                frame_file = request.files['frame_image']
                import boto3
                s3 = boto3.resource('s3')
                s3.Object('xscoating', new_filename).put(Body=frame_file, ACL='public-read')
                json_data = json.loads(request.form['frame_data'])
                json_data['filename'] = new_filename
                json_data['remote_addr'] = request.remote_addr
                json_text = json.dumps(json_data)
                db = Database()
                result = db.add_frame(device_id, json_text)
                if result > 0:
                    commands = db.fetch_commands(device_id)
                    return json.dumps({"success": True,
                                       "commands": commands,
                                       "frame_id": result})
                else:
                    return json.dumps({"success": False,
                                       "errorCode": 333,
                                       "error": "frame not added"})
        else:
            return json.dumps({"success": False, "error": "Unknown error.", "errorCode": 312})
    return '''
<html>
<title>Upload new frame</title>
<form method="post" enctype="multipart/form-data">
    <input name="uuid" placeholder="Device UUID" /><br />
    <input name="frame_data" placeholder="JSON metadata" /><br />
    <input type="file" name="frame_image" /><br />
    <input type="submit" />
</form>
'''
