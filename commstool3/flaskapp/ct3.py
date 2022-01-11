# Imports

import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
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

EMAIL_REGEX = re.compile(
    r"""^[a-zA-Z0-9.!@#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"""  # noqa: E501
)
# Source: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/email

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
    status: str

    def __init__(self, ticket_data: dict) -> None:
        self._ticket_data = ticket_data
        self.api_url = self._ticket_data["self"]
        self.jira_url = self._get_jira_url()
        self.ref = self._ticket_data["key"]
        self.project = self._ticket_data["key"].split("-")[0]
        self.status = self._ticket_data["fields"]["status"]["name"]
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
            An `OpsIncidentTicket` object if project is OPS and issuetype is Incident,
            otherwise a `JiraTicket` object.
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
        fromaddress:
            String containing the from email address
        is_draft:
            Bool. Whether Outlook should regard the email as unsent. Sets header
            "X-Unsent": "1" if True.
        recipients:
            List containing recipient email addresses
        subject:
            String containing the email subject
        bad_recipients:
            List containing email addresses that `JiraEmail.create` found to be
            invalid
    """

    def __init__(
        self,
        ticket: JiraTicket | OpsIncidentTicket,
        fromaddress: str = "",
        recipients: List[str] = None,
        bad_recipients: List[str] = None,
        subject: str = None,
        is_draft: bool = True,
    ) -> None:

        self.ticket = ticket
        self.fromaddress = fromaddress
        self.is_draft = is_draft
        if recipients is None:
            self.recipients = []  # Don't use a mutable type (list) as default value
        else:
            self.recipients = recipients
        if bad_recipients is None:
            self._bad_recipients = []
        else:
            self._bad_recipients = bad_recipients

        self.incident_values = {}

        if subject is None:
            self.subject = self._get_subject()
        else:
            self.subject = subject
        self._message = MIMEMultipart(
            "alternative"
        )  # Create the email object for later use

    @classmethod
    def create(
        cls,
        ticket: JiraTicket | OpsIncidentTicket,
        fromaddress: str = "digital.247operations@bbc.co.uk",
        recipients: List[str] = None,
        is_draft: bool = True,
    ):
        """
        Creates an instance of JiraEmail

        Handles validation of recipient email addresses. Passes invalid email addresses
        to `JiraEmail.bad_recipients` in the returned object

        Args:
            ticket:
                A ticket object of type `JiraTicket` or a subtype thereof
            fromaddress:
                String containing the from address for the email
            recipients:
                List of recipient emails addresses as strings
            is_draft:
                Bool indicating whether email should be treated as a draft

        Returns:
            A `JiraEmail` object
        """
        if recipients is None:
            recipients = []
        valid_recipients = [
            address for address in recipients if verify_address(address)
        ]
        bad_recipients = [
            address for address in recipients if not verify_address(address)
        ]

        return JiraEmail(
            ticket,
            fromaddress,
            recipients=valid_recipients,
            bad_recipients=bad_recipients,
            is_draft=is_draft,
        )

    def _get_subject(self) -> str:
        """
        Returns the default subject based on ticket state

        Subject is in the form:
        [<Status>] <Incident status> <Ticket reference> <Summary>
        Status contains "Advisory" for non-incidents, incident status for
        incidents that are Resolved, Closed, or Reopened, and blank otherwise

        Returns:
            subject: The default subject based on the ticket
        """
        # set prefix
        if isinstance(self.ticket, OpsIncidentTicket):
            if self.ticket.status in ("Resolved", "Closed", "Reopened"):
                status_part = f"[{self.ticket.status}]"
            else:
                status_part = None
            incident_part = f"{self.ticket.incident_fields['Priority']} Incident"
        else:
            status_part = "[Advisory]"
            incident_part = None
        prefix = f"""{str(status_part) + ' ' + str(incident_part)}"""
        subject = f"""{prefix + ' ' + self.ticket._ticket_data["fields"]["summary"]}"""
        return subject

    def populate_email(self, ticket: JiraTicket, template: Template) -> None:
        html = template.render(
            ref=ticket.ref,
            summary=ticket._ticket_data["fields"]["summary"],
            desc=ticket._ticket_data["fields"]["description"],
        )
        part = MIMEText(html, "html")
        self._message.attach(part)
        self._message.add_header("From", self.fromaddress)
        self._message.add_header("To", self.fromaddress)
        self._message.add_header("BCC", ",".join(self.recipients))
        self._message.add_header("Subject", self.subject)

    def add_recipient(self, recipient: str) -> None:
        """
        Adds a single recipient email address to `self.recipients`

        If the email address is invalid, adds the address to `self._bad_recipients`

        Args:
            recipient: String containing the email address to be added
        """
        if verify_address(recipient):
            self.recipients.append(recipient)
        else:
            self._bad_recipients.append(recipient)

    def add_multiple_recipients(
        self, recipients: List[str]  # expect a list of strings
    ) -> None:
        """
        Adds a list of recipients to `recipients`

        Args:
            recipients: A list of email addresses to be added to `self.recipients`
        """
        for recipient in recipients:
            self.add_recipient(recipient)

    def output_email(self, path: str) -> None:
        """
        Writes the `JiraEmail` object out to a file

        Adds the "X-Unsent" header if the email is a draft

        Args:
            path: String containing path to output file
        """
        if self.is_draft:
            self._message.add_header(
                "X-Unsent", "1"
            )  # Make the email appear unsent to Outlook
        with open(path, "w") as outfile:
            gen = generator.Generator(outfile)
            gen.flatten(self._message)


# Functions


def verify_address(address: str) -> bool:
    """
    Checks that the provided email address is valid

    Uses the same regex as the HTML5 'email' input type described at
    https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/email

    Args:
        address: String containing email address to be checked

    Returns:
        True if email address appears valid

    Raises:
        ValueError if email address appears invalid
    """
    if not EMAIL_REGEX.fullmatch(address):
        return False
    return True
