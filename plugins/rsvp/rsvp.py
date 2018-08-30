from datetime import datetime, timedelta
import os
import re

import dateparser
from errbot import BotPlugin, botcmd
import requests

# FIXME: Worth making this a config?
BASE_URL = 'https://rsvp.thatteidlikaalsoup.team/'


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
        name, date = match.groups()
        start_date = datetime.strptime(date, '%Y-%m-%d %H:%M')
        end_date = start_date + timedelta(days=1)
        url = '{}/api/events/?start={:%Y-%m-%d}&end={:%Y-%m-%d}'.format(
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
        url = '{}/api/rsvps/{}'.format(BASE_URL, event_id)
        response = requests.post(
            url, json={'user': email}, headers=headers
        ).json()
        return response

    @staticmethod
    def get_event(event_id):
        headers = {
            'Authorization': 'token {}'.format(os.environ['RSVP_TOKEN'])
        }
        url = '{}/api/rsvps/{}'.format(BASE_URL, event_id)
        response = requests.get(url, headers=headers).json()
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
        return self.rsvp_list(msg, args) if rsvp_id else response.get(
            'error', 'Failed to RSVP'
        )

    @botcmd
    def rsvp_list(self, msg, args):
        """List of RSVPs for an event"""
        try:
            event_id = self.get_event_id(msg)
        except Exception:
            event_id = None
        if not event_id:
            return 'Could not find event'

        event = self.get_event(event_id)
        names = [
            rsvp['user'].get('nick', '').strip() or rsvp['user']['name']
            for rsvp in event['rsvps']
            if not rsvp['cancelled']
        ]
        rsvp_list = '\n'.join(
            [
                '{}. {}'.format(i, name)
                for (i, name) in enumerate(names, start=1)
            ]
        )
        content = 'All RSVPs:\n\n{}'.format(rsvp_list)
        return content if names else 'No RSVPs'

    @botcmd(split_args_with='\n')
    def create_rsvp(self, msg, args):
        """Create a new RSVP event"""
        title, date, description = args.strip().split('\n', 2)
        parsed_date = dateparser.parse(
            date, settings={'PREFER_DATES_FROM': 'future'}
        )
        try:
            date, time = parsed_date.date(), parsed_date.time()
        except AttributeError:
            return 'Could not parse date'

        url = '{}/event'.format(BASE_URL)
        headers = {
            'Authorization': 'token {}'.format(os.environ['RSVP_TOKEN'])
        }
        response = requests.post(
            url,
            data={
                'date': date,
                'time': time,
                'event-name': title,
                'event-description': description,
            },
            headers=headers,
        )
        return 'Success!'
