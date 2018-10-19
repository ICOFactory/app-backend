from flask import Flask, request, render_template, Response, abort
from json_parser import JSONProcessor
from database import Database
import events
import smart_contract
import datetime
import json
import uuid
import MySQLdb

app = Flask(__name__)


def verify_admin(user_info):
    if user_info['email_address'] == "admin":
        return True
    return False


@app.route('/ethereum-node/command-output/<api_key>',methods=["GET","POST"])
def eth_node_command_output(api_key):
    db = Database()
    db.logger = app.logger
    eth_node_id = db.validate_api_key(api_key)
    if eth_node_id:
        json_data = request.get_json(force=True)
        new_event = events.Event("Ethereum Node Command Output",db)
        if new_event.log_event(eth_node_id,json.dumps(json_data)):
            return Response(json.dumps(result="OK"))
        else:
            # node will not request another command until it receives a result from
            # posting output
            return Response(json.dumps(result="Error"))
    abort(403)


@app.route('/ethereum-node/update/<api_key>',methods=["GET","POST"])
def eth_node_update(api_key):
    db = Database()
    db.logger = app.logger
    eth_node_id = db.validate_api_key(api_key)
    if eth_node_id:
        new_event = events.Event("Ethereum Node Update")
        event_data = dict(ipAddress=request.remote_addr)
        json_data = request.get_json(force=True)
        if type(json_data) is dict:
            if "peerCount" in json_data:
                event_data["peerCount"] = json_data["peerCount"]
            if "synchronized" in json_data:
                event_data["synchronized"] = json_data["synchronized"]
                if not event_data["synchronized"]:
                    sync_info = ["currentBlock",
                                 "highestBlock",
                                 "knownStates",
                                 "startingBlock"]
                    if "syncProgress" in json_data:
                        event_data["syncProgress"] = dict()
                        for each in sync_info:
                            event_data["syncProgress"][each] = json_data["syncProgress"][each]
                    new_event_log_id = new_event.log_event(eth_node_id,json.dumps(event_data))
                    db.update_ethereum_node_status(eth_node_id,request.remote_addr,new_event_log_id,db.ETH_NODE_STATUS_SYNCING)
                    return Response("{\"result\":\"OK\"}")
                else:
                    block_data = ["blockNumber", "mainAccountBalance", "gasPrice"]
                    for each in block_data:
                        event_data[each] = json[each]
                    if "error" in json_data:
                        if json_data["error"] == "output_blocked":
                            event_data["error"] = "output_blocked"
                            # No more commands if the output to a prior command is blocked
                            new_event_log_id = new_event.log_event(eth_node_id, json.dumps(event_data))
                            db.update_ethereum_node_status(eth_node_id, request.remote_addr, new_event_log_id,
                                                           db.ETH_NODE_STATUS_ERROR)
                            return Response(json.dumps({"result":"OK"}))

                    new_event_log_id = new_event.log_event(eth_node_id, json.dumps(event_data))
                    db.update_ethereum_node_status(eth_node_id, request.remote_addr, new_event_log_id,
                                                           db.ETH_NODE_STATUS_SYNCED)
                    # since the node is synchornized and not output blocked, we check for outstanding commands
                    pending_commands = db.get_pending_commands(eth_node_id)
                    response_obj = dict(result="OK",
                                        directed_commands=pending_commands[1],
                                        undirected_commands=pending_commands[0])
                    return Response(json.dumps(response_obj))
    abort(403)


@app.route('/ethereum-node/dispatch-next-command/undirected/<api_key>')
def dispatch_next_undirected_command(api_key):
    db = Database()
    db.logger = app.logger
    eth_node_id = db.validate_api_key(api_key)
    if eth_node_id:
        sql = "SELECT command_id, command FROM commands WHERE dispatch_event_id IS NULL AND node_id IS NULL "
        sql += "ORDER BY created DESC LIMIT 1;"
        # We call the DB here directly because we are locking a table,
        # want to keep everything clear so we don't deadlock it
        try:
            c = self.db.cursor()
            c.execute("LOCK TABLES commands WRITE")
            c.execute(sql)
            row = c.fetchone()
            if row:
                command_id = row[0]
                command = row[1]
                new_event = events.Event("Ethereum Node Command Dispatch")
                new_log_item_id = new_event.log_event(eth_node_id,command)
                if new_log_item_id:
                    sql = "UPDATE commands SET dispatch_event_id=%s WHERE command_id=%s;"
                    c.execute(sql,(new_log_item_id,command_id))
                    self.db.commit()
                    c.execute("UNLOCK TABLES")
                    c.close()
                    return_obj = dict(result="OK",command=command,command_id=command_id)
                    return Response(json.dumps(return_obj))
                else:
                    return Response(json.dumps({"result":"Error"}))
            c.execute("UNLOCK TABLES")
            return Response(json.dumps({"result":"OK","command":None}))
        except MySQLdb.Error as e:
            try:
                self.logger.error("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
            except IndexError:
                self.logger.error("MySQL Error: %s" % (str(e),))
    abort(403)


@app.route('/ethereum-node/dispatch-next-command/directed/<api_key>')
def dispatch_next_directed_command(api_key):
    db = Database()
    db.logger = app.logger
    eth_node_id = db.validate_api_key(api_key)
    if eth_node_id:
        new_event = events.Event("Ethereum Node Command Dispatch",db)
        next_command = db.get_next_directed_command(eth_node_id)
        if next_command:
            command_id = next_command[0]
            new_log_id = new_event.log_event(eth_node_id,command)
            if new_log_id:
                if db.dispatch_directed_command(command_id,new_log_id):
                    return Response(json.dumps({"result":"OK","command":command}))
                else:
                    return Response(json.dumps({"result":"OK","command":None}))
        return Response(json.dumps({"result":"OK","command":None}))
    abort(403)


@app.route('/admin/ethereum-network/<session_token>')
def admin_eth_network(session_token):
    db = Database()
    db.logger = app.logger
    session_id = db.validate_session(session_token)
    if session_id:
        if verify_admin(db.get_user_info(session_id)):
            ethereum_nodes = db.list_ethereum_nodes()
            return render_template("ethereum_network.html",
                            session_token=session_token,
                            ethereum_nodes=ethereum_nodes)

    return render_template("login.html", error="Invalid session.")


@app.route('/admin/user/remove-tokens', methods=["GET","POST"])
def remove_tokens():
    db = Database()
    db.logger = app.logger
    session_token = request.form['session_token']
    tokens_to_remove = int(request.form['tokens'])
    token_id = int(request.form['smart_contract_id'])
    user_id = int(request.form['user_id'])
    user_info = db.get_user_info(user_id)
    full_name = user_info["full_name"]
    session_id = db.validate_session(session_token)
    if session_id:
        if verify_admin(db.get_user_info(session_id)):
            smart_contracts = db.get_smart_contracts(session_id)
            for every_contract in smart_contracts:
                if every_contract['token_id'] == token_id:
                    sc = smart_contract.SmartContract(eth_address=every_contract['eth_address'])
                    removed_tokens = sc.unassign_tokens_from_user_id(user_id,tokens_to_remove)
                    return render_template("tokens_removed.html",
                                           removed_tokens=removed_tokens,
                                           user_id=user_id,
                                           username=full_name,
                                           session_token=session_token)
    abort(500)


@app.route('/admin/ethereum-network/add-node', methods=["GET","POST"])
def add_eth_node():
    session_token = request.form['session_token']
    new_node_identifier = request.form['node_identifier']
    db = Database()
    db.logger = app.logger
    session_id = db.validate_session(session_token)
    if session_id:
        if verify_admin(db.get_user_info(session_id)):
            new_api_key = db.add_ethereum_node(new_node_identifier)
            if new_api_key:
                node_action_message = "Generated the new new API key  " + new_api_key
                return render_template("node_action.html",node_action="New Node Created",
                                       node_action_message=node_action_message,
                                       session_token=session_token)
            else:
                node_action_message = "Couldn't create new API key"
                return render_template("node_action.html", node_action="Error",
                                       node_action_message=node_action_message,
                                       session_token=session_token)
    return render_template("login.html", error="Invalid session.")


@app.route('/admin/user/assign-tokens', methods=["GET","POST"])
def assign_tokens():
    db = Database()
    db.logger = app.logger
    session_token = request.form['session_token']
    new_tokens = int(request.form['new_tokens'])
    token_id = int(request.form['smart_contract_id'])
    user_id = int(request.form['user_id'])
    user_info = db.get_user_info(user_id)
    full_name = user_info["full_name"]
    session_id = db.validate_session(session_token)
    if session_id:
        if verify_admin(db.get_user_info(session_id)):
            smart_contracts = db.get_smart_contracts(session_id)
            for every_contract in smart_contracts:
                if every_contract['token_id'] == token_id:
                    sc = smart_contract.SmartContract(eth_address=every_contract['eth_address'])
                    tokens_assigned = sc.assign_tokens_to_user_id(user_id, new_tokens)
                    return render_template("assigned_to_user.html",
                                           new_tokens=tokens_assigned,
                                           user_id=user_id,
                                           username=full_name,
                                           session_token=session_token)
    abort(500)


@app.route('/admin/issue-tokens', methods=["GET", "POST"])
def issue_tokens():
    db = Database()
    db.logger = app.logger
    session_token = request.form['session_token']
    new_tokens = int(request.form['new_tokens'])
    token_id = int(request.form['token_id'])
    session_id = db.validate_session(session_token)
    if session_id:
        if verify_admin(db.get_user_info(session_id)):
            smart_contracts = db.get_smart_contracts(session_id)
            for every_contract in smart_contracts:
                if every_contract['token_id'] == token_id:
                    sc = smart_contract.SmartContract(eth_address=every_contract['eth_address'])
                    new_tokens = sc.issue_tokens(new_tokens)
                    return render_template("new_tokens.html",
                                           session_token=session_token,
                                           token_name=every_contract["token_name"],
                                           new_tokens=new_tokens)
            abort("Couldn't find smart contract")
        abort("Must be admin")
    abort("Could not issue tokens")


@app.route('/admin/ico/view_smart_contract/<smart_contract_id>/<session_token>')
def view_smart_contract(smart_contract_id,session_token):
    if session_token and smart_contract_id:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            if verify_admin(db.get_user_info(session_id)):
                smart_contracts = db.get_smart_contracts(session_id)
                for every_contract in smart_contracts:
                    if every_contract['token_id'] == int(smart_contract_id):
                        sc = smart_contract.SmartContract(eth_address=every_contract['eth_address'])
                        return render_template("view_smart_contract.html",
                                               new_solidity_contract=sc.solidity_code,
                                               session_token=session_token)
            abort(403)
        abort(403)
    abort(500)


@app.route('/admin/ico', methods=["POST", "GET"])
def ico_admin():
    session_token = request.form['session_token']
    token_name = request.form['token_name']
    token_symbol = request.form['token_symbol']
    tokens = int(request.form['ico_tokens'])
    if tokens < 1:
        abort(Response("Invalid initial tokens value"))
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            if verify_admin(db.get_user_info(session_id)):
                smart_contracts = db.get_smart_contracts(session_id)
                for every_contract in smart_contracts:
                    if token_name == every_contract['token_name']:
                        abort(Response("This token name already exists"))
                    #if token_symbol == every_contract['token_symbol']:
                    #    abort(Response("This token symbol already exists"))
                new_smart_contract = smart_contract.SmartContract(token_name=token_name,
                                                                  token_symbol=token_symbol,
                                                                  token_count=tokens)
                return render_template("view_smart_contract.html",
                                       token_name=token_name,
                                       token_symbol=token_symbol,
                                       tokens=tokens,
                                       session_token=session_token,
                                       new_solidity_contract=new_smart_contract.solidity_code)
    abort(404)


@app.route('/admin/profile/<user_id>/<session_token>')
def user_profile_admin(user_id, session_token):
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            if verify_admin(db.get_user_info(session_id)):
                user_data = db.get_user_info(user_id)
                smart_contracts = db.get_smart_contracts(user_id)
                sc_data = []
                for each in smart_contracts:
                    sc = smart_contract.SmartContract(eth_address=each['eth_address'])
                    if sc.smart_contract_id > 0:
                        token_count = sc.get_token_count_for_user_id(user_id)
                        new_obj = dict(each)
                        new_obj["user_owned_tokens_count"] = token_count
                        new_obj["user_owned_tokens"] = sc.list_owned_tokens_for_user_id(user_id)
                        new_obj["available_tokens"] = sc.get_unassigned_token_count()
                        sc_data.append(new_obj)
                return render_template("profile.html",
                                       session_token=session_token,
                                       user_info=user_data,
                                       ico_data=sc_data)
    return render_template("login.html")


@app.route('/admin/tokens/<session_token>')
def tokens_admin(session_token):
    if session_token:
        db = Database()
        db.logger = app.logger
        session_id = db.validate_session(session_token)
        if session_id:
            if verify_admin(db.get_user_info(session_id)):
                config_data = json.load(open("config.json","r"))
                wallet_address = config_data['wallet_address']
                eth_node = {"hostname":"ethereum_node_1.dyndns.org",
                            "ip_addr":"69.53.42.122"}
                latest_block = {"hash": "0xb83f73fbe6220c111136aefd27b160bf4a34085c65ba89f24246b3162257c36a",
                                "transaction_count": 5,
                                "lowest_gas_price": 8,
                                "timestamp": datetime.datetime.now().isoformat()}
                smart_contracts = db.get_smart_contracts(0)
                total_tokens = 0
                issued_tokens = 0
                contract_data = []
                for every_contract in smart_contracts:
                    new_obj = dict(every_contract)
                    sc = smart_contract.SmartContract(eth_address=every_contract["eth_address"])
                    total_tokens += every_contract['tokens']
                    new_obj["issued_tokens"] = sc.get_issued_token_count()
                    new_obj["unissued_tokens"] = every_contract["tokens"] - new_obj["issued_tokens"]
                    new_obj["unassigned_tokens"] = sc.get_unassigned_token_count()
                    issued_tokens += new_obj["issued_tokens"]
                    contract_data.append(new_obj)
                return render_template("tokens.html",
                                       latest_block=latest_block,
                                       session_token=session_token,
                                       wallet_address=wallet_address,
                                       eth_node=eth_node,
                                       smart_contracts=contract_data,
                                       smart_contract_count=len(smart_contracts),
                                       total_ico_tokens=total_tokens,
                                       total_issued_tokens=issued_tokens,
                                       tokens_not_yet_issued=0,
                                       eth_balance=0.15)
    return render_template("login.html")


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
