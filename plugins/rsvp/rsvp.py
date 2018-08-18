from datetime import datetime, timedelta
import os
import re

from errbot import BotPlugin, botcmd
import requests

# FIXME: Worth making this a config?
BASE_URL = 'https://rsvp.thatteidlikaalsoup.team/api'


class RSVP(BotPlugin):
    """Plugin to enable RSVPing from Zulip."""

    @staticmethod
    def get_event_id(msg):
        headers = {
            'Authorization': 'token {}'.format(os.environ['RSVP_TOKEN'])
        }
        match = re.match(
            '(?P<name>.*) - (?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2})',
            msg.to.subject,
        )
        if not match:
            return 'No date found from topic'

        name, date = match.groups()
        start_date = datetime.strptime(date, '%Y-%m-%d %H:%M')
        end_date = start_date + timedelta(days=1)
        url = '{}/events/?start={:%Y-%m-%d}&end={:%Y-%m-%d}'.format(
            BASE_URL, start_date, end_date
        )
        events = requests.get(url, headers=headers).json()
        events = [event for event in events if event['name'] == name]
        if len(events) == 1:
            return events[0]['_id']['$oid']

    @staticmethod
    def do_rsvp(event_id, email):
        headers = {
            'Authorization': 'token {}'.format(os.environ['RSVP_TOKEN'])
        }
        url = '{}/rsvps/{}'.format(BASE_URL, event_id)
        response = requests.post(
            url, json={'user': email}, headers=headers
        ).json()
        return response

    @botcmd
    def rsvp(self, msg, args):
        """RSVP to the app"""
        sender_email = args.strip().split()[0] if args else msg.frm.id
        try:
            event_id = self.get_event_id(msg)
        except Exception:
            event_id = None
        if not event_id:
            return 'Could not find event'

        try:
            response = self.do_rsvp(event_id, sender_email)
        except Exception:
            return 'Failed to RSVP'

        rsvp_id = response.get('_id', {}).get('$oid', '')
        return "Successfully RSVP'd" if rsvp_id else response.get(
            'error', 'Failed to RSVP'
        )
