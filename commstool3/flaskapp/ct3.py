# Imports

import json
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import ParseResult

import requests
from jinja2 import Template
from requests.sessions import Session

from flaskapp.config import Config

# Constants


_SESSION: Session = (
    requests.Session()
)  # We will use the same session throughtout this module
_SESSION.cert = Config.REQUESTSOPTIONS["cert"]
_SESSION.headers = Config.REQUESTSOPTIONS["headers"]

_APIBASEURL: ParseResult = urllib.parse.urlparse(
    urllib.parse.urlunsplit(
        (
            Config.JIRAOPTIONS["scheme"],
            Config.JIRAOPTIONS["server"],
            Config.JIRAOPTIONS["apipath"],
            "",
            "",  # query and fragment left empty
        )
    )
)


# Classes


@dataclass(init=False)
class JiraTicket:
    """
    Class containing the basic elements of a Jira ticket
    """

    ticket_data: dict
    api_url: str
    jira_url: ParseResult
    ref: str
    project: str

    def __init__(self, ticket_data: dict) -> None:
        self.ticket_data = ticket_data
        self.api_url = self.ticket_data["self"]
        self.jira_url = self.get_jira_url()
        self.ref = self.ticket_data["key"]
        self.project = self.ticket_data["key"].split("-")[0]
        print(
            f"""\
            Project: {self.project}
            API URL: {self.api_url}
            Jira URL: {self.jira_url.geturl()}
            """
        )

    @classmethod
    def create(cls, ref: str, api: ParseResult = _APIBASEURL):
        """
        Static method used to create an instance of a JiraTicket or subclass.
        Returns an OpsIncidentTicket object if project is OPS and issuetype is Incident,
        returns JiraTicket otherwise.
        """
        fetch_url = api.geturl() + f"issue/{ref}"
        response = _SESSION.get(fetch_url, verify=True)
        response.raise_for_status()  # Stop on HTTP error
        data = json.loads(response.text)
        if (
            data["key"].split("-")[0] == "OPS"
            and data["fields"]["issuetype"]["name"] == "Incident"
        ):
            return OpsIncidentTicket(data)
        else:
            return JiraTicket(data)

    def get_jira_url(self) -> ParseResult:
        url = urllib.parse.urlparse(self.api_url)
        return url._replace(path=f"browse/{self.ticket_data['key']}")

    def update_from_jira(self):
        response = _SESSION.get(self.api_url)
        response.raise_for_status()  # Stop on HTTP error
        # Check that the ticket has not moved projects (project in response does not
        # match current project). If it has, stop.
        if json.loads(response.text)["key"].split("-")[0] != self.project:
            raise ValueError(
                f"Jira project does not match key {self.ref}. Has the ticket moved?"
            )
        self.ticket_json = response.text
        self.ticket_data = json.loads(self.ticket_json)
        self.jira_url = self.get_jira_url()


@dataclass(init=False)
class OpsIncidentTicket(JiraTicket):
    """
    Subclass of JiraTicket with data relating to OPS incidents
    """

    incident_fields: dict

    def __init__(self, ticket_data):
        super().__init__(ticket_data)
        self.incident_fields = {}
        self.incident_fields["Priority"] = self.ticket_data["fields"][
            Config.CUSTOMFIELDS["incident_priority"]
        ]["value"]
        self.incident_fields["Start Time"] = datetime.strptime(
            self.ticket_data["fields"][Config.CUSTOMFIELDS["incident_start_time"]],
            Config.TIMEOPTIONS["jira_datetime_format"],
        )
        try:
            self.incident_fields["End Time"] = datetime.strptime(
                self.ticket_data["fields"][Config.CUSTOMFIELDS["incident_end_time"]],
                Config.TIMEOPTIONS["jira_datetime_format"],
            )
        except TypeError:
            self.incident_fields["End Time"] = ""


class JiraEmail:
    """
    Class representing an email to be sent
    """

    def __init__(self, fromaddress: str) -> None:
        self.fromaddress = fromaddress
        self.message = MIMEMultipart(
            "alternative"
        )  # Create the email object for later use

    def populate_email(self, ticket: JiraTicket, template: Template) -> None:
        html = template.render(
            ref=ticket.ref,
            summary=ticket.ticket_data["fields"]["summary"],
            desc=ticket.ticket_data["fields"]["description"],
        )
        part = MIMEText(html, "html")
        self.message.attach(part)

    def add_recipients(self, recipients: list) -> None:
        self.message["to"] = ",".join(recipients)

    def output_email(self, path: str, draft: bool = True) -> None:
        if draft:
            self.message.add_header(
                "X-Unsent", "1"
            )  # Make the email appear unsent to Outlook
        with open(path, "w") as outfile:
            gen = generator.Generator(outfile)
            gen.flatten(self.message)
