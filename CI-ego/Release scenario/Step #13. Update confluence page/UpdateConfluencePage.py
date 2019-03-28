# Input:
# %env.JiraUrl% : url path for jira                                                                 || https://test.atlassian.net
# %env.JiraBotMailAddress% : email address for user which will interact with jira                   || test@ego-cms.com
# %env.JiraBotApiToken% : api token for user which will interact with jira                          || Abababagalamaga
# %env.ConfluencePageNumber% : confluence page with list of builds							        ||

import json
import requests
import sys
from bs4 import BeautifulSoup


def get_page_json():
    # get content of confluence
    response = requests.get('%env.JiraUrl%/wiki/rest/api/content/%env.ConfluencePageNumber%?expand=body.storage,version',
                            auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))

    return response.json()


def get_page_html(json):
    # create BeautifulSoup from page content
    return BeautifulSoup(json["body"]["storage"]["value"], 'html.parser')


def get_new_page_version(json):
    return json["version"]["number"] + 1;


def insert_new_tr_tag(in_soup):
    # create new BeautifulSoup object with tr content
    newTr = BeautifulSoup(
        '<tr><td><a href=\"%env.JiraUrl%/browse/%env.ProjectKey%/fixforversion/%env.JiraPreviousVersionId%\">%env.AppPreviousVersion%</a></td><td><a href=\"%env.BuildServerUrl%/repository/download/%system.teamcity.buildType.id%/%teamcity.build.id%:id/%env.ReleaseApkFinalName%\">Build</a></td></tr>')

    # get current number of tr
    line_numbers = len(in_soup.table.find_all('tr'))

    # get last tr tag, and new tr tag after
    in_soup.table.find_all('tr')[line_numbers - 1].insert_after(newTr.tr)


def send_update_page(in_soup, new_version, page_title):
    # request headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # request body
    data = json.dumps({"id": %env.ConfluencePageNumber%, "type": "page", "title": page_title,
                       "body": {"storage": {"value": str(in_soup), "representation": "storage"}},
                       "version": {"number": new_version}})

    # send request to modify page
    response = requests.put('%env.JiraUrl%/wiki/rest/api/content/%env.ConfluencePageNumber%', headers=headers, data=data,
                            auth=('%env.JiraBotMailAddress%', '%env.JiraBotApiToken%'))


if "%env.SkipRelease%" == "true":
    sys.exit()

page_json = get_page_json()

html = get_page_html(page_json)

version = get_new_page_version(page_json)

insert_new_tr_tag(html)

send_update_page(html, version, page_json["title"])