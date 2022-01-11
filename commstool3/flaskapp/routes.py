import os

from flask import render_template, send_file
from jinja2.environment import Template

from flaskapp import app
from flaskapp.config import basedir
from flaskapp.ct3 import JiraEmail, JiraTicket


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html.j2", title="Welcome to CommsTool3")


@app.route("/email/<ticketref>")
def email(ticketref=None):
    my_ticket = JiraTicket.create(ticketref)
    my_email = JiraEmail.create(
        my_ticket, recipients=["tim.oryan@bbc.co.uk", "digital.247operations@bbc.co.uk"]
    )

    with open(os.path.join(basedir, "templates/email.html.j2"), "r") as f:
        template = Template(f.read())

    my_email.populate_email(my_ticket, template)

    try:
        os.makedirs(
            os.path.join(basedir, "output")
        )  # Create output folder if it doesn't exist
    except OSError as e:
        if (
            e.errno != 17
        ):  # re-raise exception if anything other than "[Errno 17] File exists"
            raise

    my_email.output_email(os.path.join(basedir, "output/generated_email.eml"))

    return send_file(
        os.path.join(basedir, "output/generated_email.eml"),
        attachment_filename=f"{ticketref}_comms.emltpl",
    )
