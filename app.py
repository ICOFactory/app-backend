from flask import Flask, request
from json_parser import JSONProcessor
from database import Database
import json
import uuid
import node_api
import admin

app = Flask(__name__)
app.register_blueprint(admin.admin_blueprint)
app.register_blueprint(node_api.node_api_blueprint)


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
