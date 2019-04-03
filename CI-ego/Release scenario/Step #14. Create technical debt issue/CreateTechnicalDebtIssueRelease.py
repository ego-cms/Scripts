# Input:
# %env.SonarQubeProjectName% : project name in SonarQube
# %env.SonarQubeToken% : sonarqube token for api calls
# %env.SonarQubeUrl% : url path for sonarqube
# %env.JiraUrl% : url path for jira
# %env.JiraBotMailAddress% : email address for user which will interact with jira
# %env.JiraBotApiToken% : api token for user which will interact with jira
# %env.ProjectId% : jira's project id
# %env.JiraTechnicalDebtIssueType% : jira's project id
# %env.JiraTechnicalDebtPriority% : priority for new task

import requests
import json
import threading
import re
import sys
from datetime import datetime, timedelta


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

    # since_date = get_exclusive_analysis_date(release_analysis.date)
    since_date = release_analysis.date

    data = get_data(since_date)
    models = parse_data(data)
    if len(models) > 0:
        issue_type_id = get_issue_type_id()
        issue_id = create_issue(models, issue_type_id)
        add_remote_links(issue_id, models)
    else:
        print("New issues not found")


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
    # -2 min from now
    to_date = datetime.utcnow() + timedelta(0, 60 * -2)
    to_date_str = to_date.strftime('%Y-'+'%m-'+'%dT'+'%H:'+'%M:'+'%S+0000')

    params = (
        ('project', '%env.SonarQubeProjectName%'),
        ('category', 'VERSION'),
        ('to', to_date_str),
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

    response = requests.get('%env.SonarQubeUrl%/api/issues/search', params=params, auth=('%env.SonarQubeToken%', ''))

    return response.json()


def parse_data(data):
    model_items = []
    for data_item in data["issues"]:
        model_item = IssueModel(data_item["key"], data_item["message"])
        model_items.append(model_item)
    return model_items


def get_issue_type_id():
    url = "%env.JiraUrl%/rest/api/3/issue/createmeta"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    params = (
        ('projectIds', '%env.ProjectId%'),
    )

    response = requests.request("GET", url, headers=headers, params = params, auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))

    for item in response.json()["projects"][0]["issuetypes"]:
        if item["name"] == "%env.JiraTechnicalDebtIssueType%":
            return item["id"]


def create_issue(models, issue_type_id):
    project_id = %env.ProjectId%
    summary = "Technical Debt. Version - %env.AppPreviousVersion%"
    version = get_current_version_id()
    priority = "%env.JiraTechnicalDebtPriority%"
    issue_ending=""
    if len(models) > 1:
        issue_ending = "s"
    description = "Found {0} issue{1}. Check remote links section for details.".format(len(models), issue_ending)

    url = "%env.JiraUrl%/rest/api/3/issue"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {"update": {},
                          "fields": {
                              "summary": summary,
                              "issuetype": {
                                  "id": issue_type_id
                               },
                               "project": {"id": project_id},
                               "description": {"type": "doc", "version": 1, "content": [
                                   {"type": "paragraph",
                                    "content": [{"text": description, "type": "text"}]
                                    }]
                                },
                               "priority": {"name": priority}
                          }}

    if version is not None:
        payload["fields"]["fixVersions"] = [{"id": version}]

    response = requests.request("POST", url, data=json.dumps(payload), headers=headers, auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))
    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
    return response.json()["id"]


def add_remote_links(issue_id, models):
    for model in models:
        add_remote_link(issue_id, model.key, model.message)


def add_remote_link(issue_id, key, message):
    link_url = "%env.SonarQubeUrl%/project/issues?id=%env.SonarQubeProjectName%&open=" + key

    url = "%env.JiraUrl%/rest/api/3/issue/"+str(issue_id)+"/remotelink"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = json.dumps({
                          "object": {
                                     "title": message,
                                     "url": link_url
                          }})

    response = requests.request("POST", url, data=payload, headers=headers, auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))
    print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))


def get_current_version_id():
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    # send request for getting all project's versions
    response = requests.get('%env.JiraUrl%/rest/api/3/project/%env.ProjectId%/versions', headers=headers,
                            auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))

    # first version that's not archived and not released is returned
    for version in response.json():
        if not version["released"] and not version["archived"]:
            print(version)
            return version["id"]

    print("Current version not found")
    return None


if "%env.SkipRelease%" == "true":
    sys.exit()

if "%env.IsBuildFailed%" == "true":
    sys.exit()

timer = threading.Timer(5.0, main)
timer.start()