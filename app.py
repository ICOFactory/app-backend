from flask import Flask, request, render_template
from json_parser import JSONProcessor
from database import Database
from charting import Charting
import json
import node_api
import admin

app = Flask(__name__)
app.register_blueprint(admin.admin_blueprint)
app.register_blueprint(node_api.node_api_blueprint)


@app.route('/')
def homepage():
    db = Database()
    charting = Charting(db, app.logger)
    moving_average = charting.get_gas_price_moving_average()
    chart_data = []
    for each in moving_average:
        chart_data.append(each[1])
    return render_template("main.jinja2",
                           metrics={"chart_data": {"gas_price": chart_data}},
                           first_block=moving_average[0][0])


@app.route('/block_size')
def homepage_block_size():
    db = Database()
    charting = Charting(db, app.logger)
    block_size_per_block = charting.get_block_size_per_block()
    chart_data = []
    for each in block_size_per_block:
        chart_data.append(each[1])
    return render_template("main.jinja2",
                           metrics={"chart_data": {"block_size": chart_data}},
                           first_block=block_size_per_block[0][0])


@app.route('/utilization')
def homepage_utilization():
    db = Database()
    charting = Charting(db, app.logger)
    utilization = charting.get_utilization_per_block()
    chart_data = []
    for each in utilization:
        chart_data.append(each[2] - each[1])
    return render_template("main.jinja2",
                           metrics={"chart_data": {"utilization": chart_data}},
                           first_block=utilization[0][0])


@app.route('/transaction_count')
def home_page_transaction_count():
    db = Database()
    charting = Charting(db, app.logger)
    transaction_count = charting.get_transactions_per_block()
    chart_data = []
    for each in transaction_count:
        chart_data.append(each[1])
    return render_template("main.jinja2",
                           metrics={"chart_data": {"transaction_count": chart_data}},
                           first_block=transaction_count[0][0])


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
