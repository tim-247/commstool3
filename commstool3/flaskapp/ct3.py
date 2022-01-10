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
    Class containing the basic elements of a Jira ticket.

    Attributes:
        api_url: The URL for the ticket in the Jira API, as a string
        jira_url: The URL for the ticket in the Jira UI, as a ParseResult
        ref: The Jira reference for the ticket, as a string
        project: The Jira project to which the ticket belongs, as a string
    """

    _ticket_data: dict
    api_url: str
    jira_url: ParseResult
    ref: str
    project: str

    def __init__(self, ticket_data: dict) -> None:
        self._ticket_data = ticket_data
        self.api_url = self._ticket_data["self"]
        self.jira_url = self._get_jira_url()
        self.ref = self._ticket_data["key"]
        self.project = self._ticket_data["key"].split("-")[0]
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
        Creates an instance of a JiraTicket or subclass of JiraTicket.

        Use this method rather than creating an instance directly to ensure the correct
        subclass is returned (ie. OpsIncidentTicket for an OPS incident).

        Args:
            ref: A string containing the Jira reference of the ticket to be created
            api: The base URL of the Jira API, as urllib.parse.ParseResult

        Returns:
            An OpsIncidentTicket object if project is OPS and issuetype is Incident,
            otherwise a JiraTicket object.
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

    def _get_jira_url(self) -> ParseResult:
        """
        Gets the URL for a ticket in the Jira UI.

        The Jira API does not provide this itself, so we have to infer it.

        Returns:
            The URL for the ticket in the Jira UI, as a ParseResult
        """
        url = urllib.parse.urlparse(self.api_url)
        return url._replace(path=f"browse/{self._ticket_data['key']}")

    def update_from_jira(self) -> None:
        """
        Refreshes the ticket object with data from Jira.

        Returns:
            None. Updates the object variables _ticket_data and jira_url

        Raises:
            ValueError if the project part of the key does not match the current
            project, as this indicates the ticket has moved between projects.
        """
        response = _SESSION.get(self.api_url)
        response.raise_for_status()  # Stop on HTTP error
        # Check that the ticket has not moved projects (project in response does not
        # match current project). If it has, stop.
        if json.loads(response.text)["key"].split("-")[0] != self.project:
            raise ValueError(
                f"Jira project does not match key {self.ref}. Has the ticket moved?"
            )
        ticket_json = response.text
        self._ticket_data = json.loads(ticket_json)
        self.jira_url = self._get_jira_url()


@dataclass(init=False)
class OpsIncidentTicket(JiraTicket):
    """
    Subclass of JiraTicket with additional data relating to OPS incidents

    Attributes:
        api_url:
            The URL for the ticket in the Jira API, as a string
        jira_url:
            The URL for the ticket in the Jira UI, as a ParseResult
        ref:
            The Jira reference for the ticket, as a string
        project:
            The Jira project to which the ticket belongs, as a string
        incident_fields:
            Dictionary containing incident-specific fields, as defined in Config
    """

    incident_fields: dict

    def __init__(self, ticket_data):
        super().__init__(ticket_data)
        self.incident_fields = {}
        self.incident_fields["Priority"] = self._ticket_data["fields"][
            Config.CUSTOMFIELDS["incident_priority"]
        ]["value"]
        self.incident_fields["Start Time"] = datetime.strptime(
            self._ticket_data["fields"][Config.CUSTOMFIELDS["incident_start_time"]],
            Config.TIMEOPTIONS["jira_datetime_format"],
        )
        try:
            self.incident_fields["End Time"] = datetime.strptime(
                self._ticket_data["fields"][Config.CUSTOMFIELDS["incident_end_time"]],
                Config.TIMEOPTIONS["jira_datetime_format"],
            )
        except TypeError:
            self.incident_fields["End Time"] = ""


class JiraEmail:
    """
    Class representing an email to be sent

    Attributes:
        fromaddress: String containing the from email address
    """

    def __init__(self, fromaddress: str) -> None:
        self.fromaddress = fromaddress
        self._message = MIMEMultipart(
            "alternative"
        )  # Create the email object for later use

    def populate_email(self, ticket: JiraTicket, template: Template) -> None:
        html = template.render(
            ref=ticket.ref,
            summary=ticket._ticket_data["fields"]["summary"],
            desc=ticket._ticket_data["fields"]["description"],
        )
        part = MIMEText(html, "html")
        self._message.attach(part)

    def add_recipients(self, recipients: list) -> None:
        self._message["to"] = ",".join(recipients)

    def output_email(self, path: str, draft: bool = True) -> None:
        if draft:
            self._message.add_header(
                "X-Unsent", "1"
            )  # Make the email appear unsent to Outlook
        with open(path, "w") as outfile:
            gen = generator.Generator(outfile)
            gen.flatten(self._message)
