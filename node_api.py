from flask import (
    Blueprint, request, Response, current_app
)
from werkzeug.exceptions import abort
import database
import events
import json
from charting import Charting
from block_data import BlockDataManager, BlockData

node_api_blueprint = Blueprint('node_api', __name__, url_prefix="/node_api")


@node_api_blueprint.route('/command_output/<api_key>', methods=["POST"])
def command_output(api_key):
    db = database.Database(current_app.logger)
    ip_addr = request.access_route[-1]
    node_id = db.validate_api_key(api_key)
    if node_id:
        json_data = request.get_json(force=True)
        if json_data:
            event_data = {}
            if json_data["success"] is True:
                event_data["error"] = False
                event_data["command_id"] = json_data["command_id"]
                event_data["input"] = json_data["input"]
                event_data["ip_address"] = ip_addr
                command_output = json.loads(event_data["input"])
                if "block_number" in command_output:
                    block_data = BlockData(json_data=event_data["input"])
                    manager = BlockDataManager(db, current_app.logger)
                    manager.put_block(block_data)
                elif "erc20_function" in command_output:
                    if "erc20_function" == "publish":
                        event_data["contract"] = command_output["contract_address"]
                        publish_event = events.Event("ERC20 Token Published", db, current_app.logger)
                        publish_event.log_event(node_id, event_data)
                    elif "erc20_function" == "burn":
                        burn_function = events.Event("ERC20 Token Burned", db, current_app.logger)
                        burn_function.log_event(node_id, event_data)
                    elif "erc20_function" == "transfer":
                        transfer_function = events.Event("ERC20 Token External Transfer", db, current_app.logger)
                        transfer_function.log_event(node_id, event_data)
                    elif "erc20_function" == "total_supply":
                        event_data["total_supply"] = json_data["total_supply"]
                new_event = events.Event("Ethereum Node Command Output", db, current_app.logger)
                new_event.log_event(node_id, event_data)
            else:
                event_data["error"] = True
                event_data["command_id"] = json_data["command_id"]
                event_data["error_message"] = json_data["error_message"]
                event_data["ip_address"] = ip_addr
                # mark command undispatched
                # db.clear_dispatch_event_id(event_data["command_id"])
                # log error event
                new_event = events.Event("Ethereum Node Command Failed", db, current_app.logger)
                new_event.log_event(node_id, event_data)
            return Response(json.dumps({"success": event_data["error"]}))
        abort(500)
    abort(403)


@node_api_blueprint.route("/dispatch_directed_command/<api_key>")
def dispatch_directed_command(api_key):
    db = database.Database(current_app.logger)
    ip_addr = request.access_route[-1]
    node_id = db.validate_api_key(api_key)
    if node_id:
        next_command = db.get_next_directed_command(node_id)
        if next_command:
            command_id = next_command[0]
            command_data = json.loads(next_command[1])

            new_event = events.Event("Ethereum Node Command Dispatch", db, current_app.logger)
            event_data = {"ip_address": ip_addr,
                          "node_id": node_id,
                          "command": json.dumps(command_data),
                          "command_id": command_id}
            new_event_id = new_event.log_event(node_id,
                                               json.dumps(event_data))
            command_data["command_id"] = command_id
            command_data["event_id"] = new_event_id
            command_data["directed"] = True
            if db.dispatch_command(command_id,
                                   node_id,
                                   new_event_id):
                return Response(json.dumps({"result": "OK",
                                            "command_data": command_data}))
            else:
                return Response(json.dumps({"result": "Error",
                                            "error_msg": "Could not dispatch command {0}".format(command_id)}))
        else:
            return Response(json.dumps({"result": "Error",
                                        "error_msg": "Could not fetch next directed command"}))
    else:
        return Response(json.dumps({"result": "Error",
                                    "error_msg": "Invalid API key"}))


@node_api_blueprint.route("/dispatch_undirected_command/<api_key>")
def dispatch_undirected_command(api_key):
    db = database.Database(current_app.logger)
    ip_addr = request.access_route[-1]
    node_id = db.validate_api_key(api_key)
    if node_id:
        next_command = db.get_next_undirected_command()
        if next_command:
            command_id = next_command[0]
            command_data = json.loads(next_command[1])

            new_event = events.Event("Ethereum Node Command Dispatch", db, current_app.logger)
            event_data = {"ip_address": ip_addr,
                          "node_id": node_id,
                          "command": json.dumps(command_data),
                          "command_id": command_id}
            new_event_id = new_event.log_event(node_id,
                                               json.dumps(event_data))
            command_data["command_id"] = command_id
            command_data["event_id"] = new_event_id
            command_data["directed"] = False
            if db.dispatch_command(command_id,
                                   node_id,
                                   new_event_id):
                return Response(json.dumps({"result": "OK",
                                            "command_data": command_data}))
            else:
                return Response(json.dumps({"result": "Error",
                                            "error_msg": "Could not dispatch command {0}".format(command_id)}))
        else:
            return Response(json.dumps({"result": "Error",
                                        "error_msg": "Could not fetch next undirected command"}))
    else:
        return Response(json.dumps({"result": "Error",
                                    "error_msg": "Invalid API key"}))


@node_api_blueprint.route('/update/<api_key>', methods=["GET", "POST"])
def node_api_update(api_key):
    db = database.Database()
    db.logger = current_app.logger
    ip_addr = request.access_route[-1]
    node_id = db.validate_api_key(api_key)
    if node_id:
        new_event = events.Event("Ethereum Node Update", db, current_app.logger)
        json_data = request.get_json(force=True)
        if type(json_data) is dict:
            event_data = dict(json_data)
            event_data["ip_address"] = ip_addr
            if "synchronized" in json_data:
                if not event_data["synchronized"]:
                    new_event_log_id = new_event.log_event(node_id, json.dumps(event_data))
                    db.update_ethereum_node_status(node_id,
                                                   ip_addr,
                                                   new_event_log_id,
                                                   db.ETH_NODE_STATUS_SYNCING)
                    db.close()
                    return Response("{\"result\":\"OK\"}")
                else:
                    if "error" in json_data:
                        if json_data["error"] == "output_blocked":
                            event_data["error"] = "output_blocked"
                            # No more commands if the output to a prior command is blocked
                            new_event_log_id = new_event.log_event(node_id, json.dumps(event_data))
                            db.update_ethereum_node_status(node_id, ip_addr, new_event_log_id,
                                                           db.ETH_NODE_STATUS_ERROR)
                            db.close()
                            return Response(json.dumps({"result": "OK"}))

                    # update block data
                    manager = BlockDataManager(db, current_app.logger)
                    manager.get_block(event_data["latest_block_number"])

                    new_event_log_id = new_event.log_event(node_id, json.dumps(event_data))
                    # update charting database
                    node_update_event = events.NodeUpdateEvent(db,
                                                               from_event_id=new_event_log_id)
                    charting = Charting(db, current_app.logger)
                    charting.add_chart_data(node_update_event)

                    db.update_ethereum_node_status(node_id,
                                                   ip_addr,
                                                   new_event_log_id,
                                                   db.ETH_NODE_STATUS_SYNCED)
                    # since the node is synchronized and not output blocked, we check for outstanding commands
                    pending_commands = db.get_pending_commands(node_id)
                    db.close()
                    response_obj = dict(result="OK",
                                        directed_commands=pending_commands[1],
                                        undirected_commands=pending_commands[0])
                    return Response(json.dumps(response_obj))
    db.close()
    abort(403)
