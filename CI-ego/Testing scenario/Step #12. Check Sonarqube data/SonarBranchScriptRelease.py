# Input:
# %env.SkipTesting% : skip build/jira actions when needed
# %env.IsBuildFailed% : skip step if build failed
# %env.TicketNumber% : Ticket number of build
# %env.JiraUrl% : url path for jira
# %env.JiraBotMailAddress% : email address for user which will interact with jira
# %env.JiraBotApiToken% : api token for user which will interact with jira
# %env.SonarQubeUrl% : url path for sonarqube
# %env.SonarQubeProjectName% : project name in SonarQube
# %env.SonarQubeToken% : sonarqube token for api calls

import requests
import json
import re
import threading
import sys
from datetime import datetime, timedelta


# Model for sonarqube issue
class IssueModel:
    def __init__(self, key, message):
        self.key = key
        self.message = message


# Model for sonarqube project analysis
class ProjectAnalysisModel:
    def __init__(self, date, version):
        self.date = date
        self.version = version


def main():
    analyses = get_project_analyses()

    release_analysis = find_last_release_analysis(analyses)

    print("\n" + release_analysis.date + " " + release_analysis.version)

    since_date = get_exclusive_analysis_date(release_analysis.date)
    data = get_data(since_date)
    models = parse_data(data)
    if len(models) > 0:
        print("Found " + str(len(models)) + " new issues.")
        sys.stdout.write("##teamcity[setParameter name='env.SkipTesting' value='true']")
        sys.stdout.flush()
        add_comment_to_issue("%env.TicketNumber%", models)
        add_remote_links("%env.TicketNumber%", models)
    else:
        print("New issues not found")


def add_comment_to_issue(issue_id, models):
    issue_ending = ""
    if len(models) > 1:
        issue_ending = "s"
    text = "Found {0} issue{1}. Check remote links section for details.".format(len(models), issue_ending)

    url = "%env.JiraUrl%/rest/api/3/issue/" + issue_id + "/comment"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": text,
                            "type": "text"
                        }
                    ]
                }
            ]
        }})
    response = requests.request("POST", url, data=payload, headers=headers,
                                auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))


def add_remote_links(issue_id, models):
    for model in models:
        add_remote_link(issue_id, model.key, model.message)


def add_remote_link(issue_id, key, message):
    title = datetime.now().strftime('%m/%d/%Y %H:%M:%S') + " - " + message

    link_url = "%env.SonarQubeUrl%/project/issues?id=%env.SonarQubeProjectName%&open=" + key

    url = "%env.JiraUrl%/rest/api/3/issue/" + str(issue_id) + "/remotelink"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "object": {
            "title": title,
            "url": link_url
        }})

    response = requests.request("POST", url, data=payload, headers=headers,
                                auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))


def parse_data(data):
    model_items = []
    for data_item in data["issues"]:
        model_item = IssueModel(data_item["key"], data_item["message"])
        model_items.append(model_item)
    return model_items


# def get_exclusive_analysis_date(date):
#     date_posted = date
#     result = datetime.strptime(date_posted, '%Y-'+'%m-'+'%dT'+'%H:'+'%M:'+'%S+0000')
#     new_date = result + timedelta(0, 1)
#     return new_date.strftime('%Y-'+'%m-'+'%dT'+'%H:'+'%M:'+'%S+0000')


def find_last_release_analysis(analyses):
    for item in analyses:
        if re.match("^\d+\.\d+$", item.version) is not None:
            return item


def get_project_analyses():
    params = (
        ('project', '%env.SonarQubeProjectName%'),
        ('category', 'VERSION'),
    )

    response = requests.get('%env.SonarQubeUrl%/api/project_analyses/search', params=params,
                            auth=('%env.SonarQubeToken%', ''))

    # print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(",", ": ")))

    model_items = []
    for data_item in response.json()["analyses"]:
        item_date = data_item["date"]
        item_version = ""
        for event_item in data_item["events"]:
            if event_item["category"] == "VERSION":
                item_version = event_item["name"]
        model_item = ProjectAnalysisModel(item_date, item_version)
        model_items.append(model_item)
    return model_items


def get_data(sinceDate):
    params = (
        ('componentKeys', '%env.SonarQubeProjectName%'),
        ('createdAfter', sinceDate),
        ('statuses', 'OPEN')
    )

    response = requests.get('%env.SonarQubeUrl%/api/issues/search', params=params,
                            auth=('%env.SonarQubeToken%', ''))

    # print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(",", ": ")))

    for item in response.json()["issues"]:
        print(item["message"])

    return response.json()


if "%env.SkipTesting%" == "true":
    sys.exit()

if "%env.IsBuildFailed%" == "true":
    sys.exit()

timer = threading.Timer(5.0, main)
timer.start()
