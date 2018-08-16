import logging
import os

from errbot import BotPlugin, botcmd
import requests


class RSVP(BotPlugin):
    """Plugin to enable RSVPing from Zulip."""

    @botcmd
    def rsvp(self, msg, args):
        """RSVP to the app"""
        sender_email = args.strip().split()[0] if args else msg.frm.id
        data = {
            'token': os.environ['RSVP_TOKEN'],
            'message': {
                'subject': msg.to.subject,
                'display_recipient': msg.to.id,
                'content': msg.body,
                'sender_email': sender_email,
            },
        }
        # FIXME: Worth making this a config?
        url = 'https://rsvp.thatteidlikaalsoup.team/zulip'
        try:
            response = requests.post(url, json=data)
        except Exception as e:
            status = 'Failure'
            message = str(e)
        else:
            status = 'Failure' if response.status_code > 201 else 'Success'
            message = response.json()['response_string']
        return '{}: {}'.format(status, message)
