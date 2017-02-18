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
    def reconfigService(self, weburl,
                 localhost_replace=False, username=None,
                 icon=None, notify_on_success=True, notify_on_failure=True,
                 **kwargs):
        """
        Creates a SlackStatusPush status service.

        :param weburl: Your Slack weburl
        :param localhost_replace: If your Buildbot web fronted doesn't know
            its public address it will use "localhost" in its links. You can
            change this by setting this variable to true.
        :param username: The user name of the "user" positing the messages on
            Slack.
        :param icon: The icon of the "user" posting the messages on Slack.
        :param notify_on_success: Set this to False if you don't want
            messages when a build was successful.
        :param notify_on_failure: Set this to False if you don't want
            messages when a build failed.
        """

        yield HttpStatusPushBase.reconfigService(self, **kwargs)
        self._http = yield httpclientservice.HTTPClientService.getService(self.master, weburl)

        self.weburl = weburl
        self.localhost_replace = localhost_replace
        self.username = username
        self.icon = icon
        self.notify_on_success = notify_on_success
        self.notify_on_failure = notify_on_failure

    @defer.inlineCallbacks
    def buildFinished(self, key, build):
        yield utils.getDetailsForBuild(
            self.master,
            build,
            wantProperties = True,
            wantSteps = False,
            wantPreviousBuild = False,
            wantLogs = False
        )
        from pprint import pprint
        pprint(build)

        prop = lambda name: build['properties'].get(name, [None])[0]

        build_url = build['url']
        source_stamps = build['buildset']['sourcestamps']
        branch = prop('branch')
        project = prop('project')
        buildername = prop('buildername')
        if not buildername.startswith('build-'):
            return
        buildername = buildername[len('build-'):]
        buildnumber = prop('buildnumber')
        worker = prop('workername')
        rev = prop('revision')
        repository = prop('repository')
        blamelist = yield utils.getResponsibleUsersForBuild(self.master, build['buildid'])
        responsible_users = '\n'.join(blamelist)
        status = Results[build['results']]

        if build['results'] == SUCCESS:
            color = "good"
        elif build['results'] == FAILURE:
            color = "#EE3435"
        else:
            color = '#AB12EF'

        message = "Build <{url}|#{buildnumber} {buildername}> finished".format(
            project=project,
            revision=rev,
            status=status,
            url=build_url,
            buildnumber = buildnumber,
            buildername = buildername,
        )

        fields = [
            {
                'title': 'Status',
                'value': status,
                'short': True,
            },
            {
                "title": "Repository",
                "value": "<http://git.eng.celoxica.com/?p={project}.git|{project}>".format(project = project),
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
                "value": '<http://git.eng.celoxica.com/?p={project}.git;a=shortlog;h=refs/heads/{branch}|{branch}>'.format(
                    project = project,
                    branch = branch,
                ),
                "short": True
            })

        if rev:
            fields.append({
                "title": "Revision",
                "value": '<http://git.eng.celoxica.com/?p={project}.git;h={rev}|{rev_short}>'.format(
                    project = project,
                    rev = rev,
                    rev_short = rev[:8]
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

        pprint(json.dumps(payload))

        response = yield self._http.post("", json=payload)
        if response.code != 200:
            content = yield response.content()
            log.error("{code}: unable to upload status: {content}",
                      code=response.code, content=content)
