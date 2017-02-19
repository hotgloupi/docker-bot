
## This file comes from https://github.com/mindmatters/buildbot-status-slack

from buildbot.reporters.http import HttpStatusPushBase
from buildbot.util import httpclientservice
from buildbot.util.logger import Logger
from buildbot.reporters import utils
from buildbot.process.results import CANCELLED
from buildbot.process.results import EXCEPTION
from buildbot.process.results import FAILURE
from buildbot.process.results import SUCCESS
from buildbot.process.results import WARNINGS
from buildbot.process.results import Results

from twisted.internet import defer
import json

log = Logger()

class SlackStatusPush(HttpStatusPushBase):
    """
    Sends messages to a Slack.io channel when each build finishes with a handy
    link to the build results.
    """

    name = "SlackStatusPush"

    @defer.inlineCallbacks
    def reconfigService(self,
                        weburl,
                        username = None,
                        icon = None,
                        templates = None,
                        **kwargs):
        """
        Creates a SlackStatusPush status service.

        :param weburl: Your Slack weburl
        :param username: The user name of the "user" positing the messages on
            Slack.
        :param icon: The icon of the "user" posting the messages on Slack.
        """

        yield HttpStatusPushBase.reconfigService(self, **kwargs)
        self._http = yield httpclientservice.HTTPClientService.getService(self.master, weburl)

        self.weburl = weburl
        self.username = username
        self.icon = icon

        self.templates = {}
        for t in ['repository', 'branch', 'revision']:
            self.templates[t] = templates.get(t, '{%s}' % t)

    @defer.inlineCallbacks
    def buildFinished(self, key, build):
        yield utils.getDetailsForBuild(
            self.master,
            build,
            wantProperties = True,
            wantSteps = True,
            wantPreviousBuild = False,
            wantLogs = False
        )
        from pprint import pprint
        pprint(build)
        prop = lambda name: build['properties'].get(name, [None])[0]

        build_url = build['url']
        source_stamps = build['buildset']['sourcestamps']
        branch = prop('branch')
        build_name = prop('build_name')
        variant_name = prop('variant_name')
        buildername = prop('buildername')
        if not buildername.startswith('build-'):
            return
        buildername = buildername[len('build-'):]
        buildnumber = prop('buildnumber')
        worker = prop('workername')
        rev = prop('got_revision')
        repository_name = prop('repository_name')
        repository_url = prop('repository_url')
        blamelist = yield utils.getResponsibleUsersForBuild(
            self.master,
            build['buildid']
        )
        responsible_users = '\n'.join(blamelist)
        status = Results[build['results']]

        if build['results'] == SUCCESS:
            color = "good"
        elif build['results'] == FAILURE:
            color = "#EE3435"
        else:
            color = '#AB12EF'

        message = "Build <{url}|#{buildnumber} {build_name} {variant_name} on {worker}> finished".format(
            url = build_url,
            buildnumber = buildnumber,
            build_name = build_name,
            variant_name = variant_name,
            worker = worker,
        )

        fields = [
            {
                'title': 'Status',
                'value': status,
                'short': True,
            },
            {
                "title": "Repository",
                "value": self.templates['repository'].format(repository = repository_name),
                "short": True
            }
        ]
        if responsible_users:
            fields.append({
                "title": "Responsible users",
                "value": responsible_users,
                'rev_short': True,
            })

        if branch:
            fields.append({
                "title": "Branch",
                "value": self.templates['branch'].format(
                    repository = repository_name,
                    branch = branch,
                ),
                "short": True
            })

        if rev:
            fields.append({
                "title": "Revision",
                "value": self.templates['revision'].format(
                    repository = repository_name,
                    revision = rev,
                    revision_short = rev[:8]
                ),
                "short": True
            })

        payload = {
            "attachments": [
              {
                  "text": message,
                  "color": color,
                  "mrkdwn_in": ["text", "title", "fallback", "fields"],
                  "fields": fields
              }
            ],
            'mrkdwn': True,
        }

        if self.username:
            payload['username'] = self.username

        if self.icon:
            if self.icon.startswith(':'):
                payload['icon_emoji'] = self.icon
            else:
                payload['icon_url'] = self.icon

        response = yield self._http.post("", json=payload)
        if response.code != 200:
            content = yield response.content()
            log.error("{code}: unable to upload status: {content}",
                      code=response.code, content=content)
