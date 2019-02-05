from flask import (
    Blueprint, request, Response, current_app
)
from werkzeug.exceptions import abort
import json
from events import Event
from block_data import BlockDataManager, BlockData

ajax_api_blueprint = Blueprint('ajax', __name__, url_prefix="/ajax")


@ajax_api_blueprint.route("/update_block_data/<latest_block>")
def update_block_data(latest_block):
    manager = BlockDataManager(logger=current_app.logger)
    new_block_numbers = manager.get_block_numbers_since(latest_block)
    block_data = []
    for each_block_number in new_block_numbers:
        block = manager.get_block_from_db(each_block_number, True)
        if block:
            block_data.append(block)
    return Response(json.dumps(block_data), content_type="application/json")


@ajax_api_blueprint.route("/block_data/<block_number>")
def block_data(block_number):
    manager = BlockDataManager(logger=current_app.logger)
    data = manager.get_block_from_db(block_number)
    if data:
        return Response(json.dumps(data), content_type="application/json")
    else:
        return Response(json.dumps({"result": False, "error": "Block data not found."}),
                        content_type="application/json")
