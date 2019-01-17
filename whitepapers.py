from flask import (
    Blueprint, render_template, request, current_app
)
from werkzeug.exceptions import abort
import events
import database

whitepapers_blueprint = Blueprint('whitepapers', __name__, url_prefix="/whitepapers")

whitepaper_urls = [{"title": "What is ERC20?", "identifier": "what-is-erc20", "url": "/whitepapers/what-is-erc20"}]


@whitepapers_blueprint.route("/<identifier>")
def display_whitepaper(identifier):
    found = None
    for each in whitepaper_urls:
        if each["identifier"] == identifier:
            found = each
            break
    if found:
        db = database.Database(logger=current_app.logger)
        view_whitepaper_event = events.Event("Whitepaper Viewed", db, logger=current_app.logger)
        view_whitepaper_event.log_event(1, {"identifier": identifier, "ip_address": request.access_route[-1]})
        template_name = "whitepapers/whitepaper_{0}.jinja2".format(identifier.replace("-", "_"))
        return render_template(template_name, whitepapers=whitepaper_urls)
    abort(404)
