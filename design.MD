# CommsTool 3 Design Document

12 Nov 2021

## Overview

* **Status**: In Progress
* **Stakeholders**
  * 247 Operations
  * Service Management
  * AppAdmin

This project aims to replace the existing **CommsTool 2** Windows application with a web application that can be used on other platforms and does not rely on a Reith-enabled BBC Windows laptop.

## Context

Email is currently the main form in which incident communications are distributed by 247 Ops to the BBC. However, email is often not the primary method of communication between teams in the BBC, and users have asked whether incident comms can be distributed by other means, such as Slack.

247 currently use **CommsTool 2**, a Windows application developed by a former member of 247. **CommsTool 2** works well, but it would require significant work to extend its features to support new channels of communication.

247 have attempted to move away from **CommsTool 2** in the past. A project to use a RunDeck script was abandoned because of the limitations of that platform.

## Goals

### Comms editing in the browser

The main application window should present a set of input fields that correspond to the standard fields in the email template. For an OPS incident, these fields are:

* Priority and type of ticket (eg. P2 Incident)
* Ticket reference
* Title (referred to as `Summary` in Jira) *
* What has happened? *
* Service Impact *
* Business/Audience Impact *
* What has been done to restore normal service? *
* Data about the ticket:
  * Jira link
  * Incident owner (always Technology Operations)
  * Incident start time
  * Incident end time
  * Next update

Fields marked with a * should be free text entry fields in the browser. Other fields may or may not be editable (although of course they can be edited in the email that is produced).

### Select distribution list(s) for email comms

Users will be able to select the distribution lists to which they want their email comms to be sent. These lists are held in Confluence.

### View and select active and recent tickets

The application window will show a list of tickets that might be of interest to the user. Initially, these will consist of open P1 and P2 incidents, and tickets that have recently been pulled into the application.

Clicking on one of these tickets will pull it into the main window.

### Remembering last comms sent

When a ticket is pulled into the main application window, the fields should be populated with the most recent comms sent (rather than data pulled from Jira).

There should be an option to refresh the fields with data from Jira.

The distribution lists last used will also be remembered.

### Email creation

The application will produce an Outlook email document with the correct **From**, **To**, and **BCC** fields populated, and the content of the comms as a standard template in the email body.

### Slack posting

The main application window will include the ability to post the comms to Slack. Currently it is envisaged that this will be to a single dedicated channel for incident comms, but requirements for this are not yet fixed.

### Posting comms updates to Jira ticket

The main application will be able to post a comment to Jira indicating that comms have been issued. The comment shall specify the time comms were sent, by what means, and to whom (in the case of email comms).

### Non-goals

The following are specifically not goals of the project:

* A generic, expandable email creation tool. The email templates are anticipated to be hard-coded and different templates will be used for different scenarios and ticket types
* A generic solution for posting to slack, including the ability to select which workspace/channel to post to

### Potential future goals

The following may be considered in future:

* Posting comms to SMS via SendWordNow

## Existing Solution

## Proposed Solution

## Alternative Solutions

## Cross-Team Impact

## Open Questions
