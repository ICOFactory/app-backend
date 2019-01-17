from flask import (
    Blueprint, render_template, request, url_for, redirect, current_app
)
from werkzeug.exceptions import abort

whitepapers_blueprint = Blueprint('whitepapers', __name__, url_prefix="/whitepapers")

whitepaper_urls = {"What is ERC20?": "what-is-erc20"}


@whitepapers_blueprint.route("/<identifier>")
def display_whitepaper(identifier):
    if identifier not in whitepaper_urls.values():
        abort(404)
    template_name = "whitepaper_" + identifier.replace("-", "_") + ".jinja2"
    return render_template("whitepapers/" + template_name)
