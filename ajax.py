from flask import (
    Blueprint, Response, current_app
)
import json
from block_data import BlockDataManager
import database

ajax_api_blueprint = Blueprint('ajax', __name__, url_prefix="/ajax")


@ajax_api_blueprint.route("/update_block_data/<latest_block>")
def update_block_data(latest_block):
    manager = BlockDataManager(logger=current_app.logger)
    new_block_numbers = manager.get_block_numbers_since(latest_block)
    new_block_data = []
    for each_block_number in new_block_numbers:
        block = manager.get_block_from_db(each_block_number, True)
        # convert to JSON serializable/JavaScript format
        block_timestamp = block["block_timestamp"]
        block["block_timestamp"] = block_timestamp.isoformat()
        if block:
            new_block_data.append(block)
    return Response(json.dumps(new_block_data), content_type="application/json")


@ajax_api_blueprint.route("/block_data/<block_number>")
def block_data(block_number):
    db = database.Database()
    manager = BlockDataManager(db, logger=current_app.logger)
    data = manager.get_block_from_db(block_number)
    if data:
        # convert to JSON serializable/JavaScript format
        block_timestamp = data["block_timestamp"]
        data["block_timestamp"] = block_timestamp.isoformat()
        return Response(json.dumps(data), content_type="application/json")
    else:
        return Response(json.dumps({"result": False, "error": "Block data not found."}),
                        content_type="application/json")
