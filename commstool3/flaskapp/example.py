import os

from jinja2.environment import Template

import flaskapp.ct3 as ct3
from flaskapp.config import basedir


def main():
    my_ticket = ct3.JiraTicket.create("OPS-260857")
    print(type(my_ticket))
    print(my_ticket)

    my_email = ct3.JiraEmail(fromaddress="digital.247operations@bbc.co.uk")
    recipients = ["tim.oryan@bbc.co.uk", "digital.247operations@bbc.co.uk"]
    my_email.add_recipients(recipients)

    with open(os.path.join(basedir, "templates/email.html.j2"), "r") as f:
        template = Template(f.read())

    my_email.populate_email(my_ticket, template)
    my_email.output_email(os.path.join(basedir, "output/test_email.eml"))


if __name__ == "__main__":
    main()
