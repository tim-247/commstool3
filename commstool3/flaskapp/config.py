import os

import requests.__version__

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    """
    Contains configuration options for the program.

    JIRAOPTIONS: Details about the Jira API we are connecting to
    REQUESTSOPTIONS: Options for the requests module to use to connect to the API
    CUSTOMFIELDS: Friendly names for the various custom Jira fields we access
    TIMEOPTIONS: Options relating to date and time formatting
    SECRET_KEY: The Flask secret key
    """

    JIRAOPTIONS = {
        "scheme": "https",
        "server": "jira.dev.bbc.co.uk",
        "apipath": "/rest/api/2/",
    }
    REQUESTSOPTIONS = {
        "cert": os.environ.get("CT3CERTPATH")
        or os.path.join(basedir, "secrets/client_cert.pem"),
        "headers": {
            "User-Agent": f"python-requests/{requests.__version__} +(CommsTool3)"
        },
    }
    CUSTOMFIELDS = {
        "incident_priority": "customfield_10351",
        "incident_start_time": "customfield_10052",
        "incident_end_time": "customfield_10053",
    }
    TIMEOPTIONS = {"jira_datetime_format": "%Y-%m-%dT%H:%M:%S.%f%z"}
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
