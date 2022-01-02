# CommsTool3

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Rebuild of the 247 Ops CommsTool as a web application. Written in Python.

[CSI-942](https://jira.dev.bbc.co.uk/browse/CSI-942)

## Proof of concept: basic instructions

For both methods, set the environment variable `CT3CERTPATH` to the location of your dev certificate, eg:

```bash
export CT3CERTPATH=/path/to/certificate.pem
```

And install the packages in `requirements.txt`.

### Command line method

Clone the repo. Run `commstool3/flaskapp/example.py`. An email will be saved to `commstool3/app/output/test_email.eml`. Change the file extension to `.emltpl` for Outlook on Mac. Feel free to change the ticket reference in `example.py`.

### Flask method

Set the following environment variable:

```bash
export FLASK_APP=flaskapp
```

From within `commstool3` run:

```bash
flask run
```

Then browse to http://localhost:5000/.

Feel free to change the ticket reference in the link.
