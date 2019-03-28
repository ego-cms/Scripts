# Input
# %env.ProjectId% : Jira project id                                                                     || 1000
# %env.AppVersion% : new app version
# %env.JiraUrl% : url path for jira                                                                     || https://test.atlassian.net
# %env.JiraBotMailAddress% : email address for user which will interact with jira                       || test@ego-cms.com
# %env.JiraBotApiToken% : api token for user which will interact with jira                              || Abababagalamaga

import requests
import sys


def create_version_and_get_id():
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    data = '{ "name":"%env.AppVersion%", "projectId":"%env.ProjectId%" }'
    # send request for adding new version
    response = requests.post('%env.JiraUrl%/rest/api/3/version', headers=headers, data=data,
                             auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))

print(response.json())

# return new version id
    return response.json()["id"]


def do_release(current_version, new_version):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    
    data = '{"released":"true", "moveUnfixedIssuesTo":"'+new_version+'"}'
    # send request for changing version status to release
    response = requests.put('%env.JiraUrl%/rest/api/3/version/'+current_version, headers=headers, data=data,
                            auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))

print(response)


def get_current_version_id():
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    # send request for getting all project's versions
    response = requests.get('%env.JiraUrl%/rest/api/3/project/%env.ProjectKey%/versions', headers=headers,
                            auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))

# first version that's not archived and not released is returned
for version in response.json():
    if not version["released"] and not version["archived"]:
        print(version)
        return version["id"]
    
    print("Current version not found")
    sys.exit()


if "%env.SkipRelease%" == "true":
    sys.exit()

current_version_id = get_current_version_id()

print("current version - " + current_version_id)

sys.stdout.write("##teamcity[setParameter name='env.JiraPreviousVersionId' value='"+current_version_id+"']")
sys.stdout.flush()

new_version_id = create_version_and_get_id()

print("new version - " + new_version_id)

do_release(current_version_id, new_version_id)
