from flask import (
    Blueprint, request, Response, current_app
)
from werkzeug.exceptions import abort
import database
import events
import json

node_api_blueprint = Blueprint('node_api', __name__, url_prefix="/node_api")


@node_api_blueprint.route('/update/<api_key>', methods=["GET", "POST"])
def node_api_update(api_key):
    db = database.Database()
    db.logger = current_app.logger
    node_id = db.validate_api_key(api_key)
    if node_id:
        new_event = events.Event("Ethereum Node Update", db, current_app.logger)
        json_data = request.get_json(force=True)
        if type(json_data) is dict:
            event_data = dict(json_data)
            event_data["ip_address"] = request.remote_addr
            if "synchronized" in json_data:
                if not event_data["synchronized"]:
                    new_event_log_id = new_event.log_event(node_id, json.dumps(event_data))
                    db.update_ethereum_node_status(node_id,
                                                   request.remote_addr,
                                                   new_event_log_id,
                                                   db.ETH_NODE_STATUS_SYNCING)
                    return Response("{\"result\":\"OK\"}")
                else:
                    if "error" in json_data:
                        if json_data["error"] == "output_blocked":
                            event_data["error"] = "output_blocked"
                            # No more commands if the output to a prior command is blocked
                            new_event_log_id = new_event.log_event(node_id, json.dumps(event_data))
                            db.update_ethereum_node_status(node_id, request.remote_addr, new_event_log_id,
                                                           db.ETH_NODE_STATUS_ERROR)
                            return Response(json.dumps({"result": "OK"}))

                    new_event_log_id = new_event.log_event(node_id, json.dumps(event_data))
                    db.update_ethereum_node_status(node_id, request.remote_addr, new_event_log_id,
                                                   db.ETH_NODE_STATUS_SYNCED)
                    # since the node is synchornized and not output blocked, we check for outstanding commands
                    pending_commands = db.get_pending_commands(eth_node_id)
                    response_obj = dict(result="OK",
                                        directed_commands=pending_commands[1],
                                        undirected_commands=pending_commands[0])
                    return Response(json.dumps(response_obj))
    abort(403)
