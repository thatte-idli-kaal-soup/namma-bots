from datetime import datetime, timedelta
import os
import re

import dateparser
from errbot import BotPlugin, botcmd, re_botcmd
import requests

# NOTE: Shouldn't end with a /
BASE_URL = "https://rsvp.thatteidlikaalsoup.team"


def date_replace_period_with_colon(date):
    return re.sub("(\d+)\.(\d+)", "\\1:\\2", date)


def is_email(text):
    return re.match("[^@]+@[^@]+\.[^@]+", text)


class RSVP(BotPlugin):
    """Plugin to enable RSVPing from Zulip."""

    def get_user_email(self, msg, name_or_nick):
        users = self.get_users()
        users = [
            user
            for user in users
            if user.get("nick", "") == name_or_nick
            or user.get("name", "") == name_or_nick
        ]
        if len(users) == 1:
            return users[0]["_id"]

    @staticmethod
    def get_event_id(name, date):
        if name.endswith("..."):
            name = name[:-4]
        next_day = date + timedelta(days=1)
        url = "{}/api/events/?start={:%Y-%m-%d}&end={:%Y-%m-%d}".format(
            BASE_URL, date, next_day
        )
        headers = {
            "Authorization": "token {}".format(os.environ["RSVP_TOKEN"])
        }
        events = requests.get(url, headers=headers).json()
        events = [event for event in events if event["name"].startswith(name)]
        if len(events) == 1:
            return events[0]["_id"]["$oid"]

    @staticmethod
    def get_event_id_from_message(msg):
        match = re.match(
            "(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) - (?P<name>.*)",
            msg.to.subject,
        )
        date, name = match.groups()
        start_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
        return RSVP.get_event_id(name, start_date)

    @staticmethod
    def do_rsvp(event_id, email):
        headers = {
            "Authorization": "token {}".format(os.environ["RSVP_TOKEN"])
        }
        url = "{}/api/rsvps/{}".format(BASE_URL, event_id)
        response = requests.post(
            url, json={"user": email}, headers=headers
        ).json()
        return response

    @staticmethod
    def get_event(event_id):
        headers = {
            "Authorization": "token {}".format(os.environ["RSVP_TOKEN"])
        }
        url = "{}/api/rsvps/{}".format(BASE_URL, event_id)
        response = requests.get(url, headers=headers).json()
        return response

    @staticmethod
    def get_users():
        headers = {
            "Authorization": "token {}".format(os.environ["RSVP_TOKEN"])
        }
        url = "{}/api/users/".format(BASE_URL)
        return requests.get(url, headers=headers).json()

    @botcmd
    def rsvp(self, msg, args):
        """RSVP to the app"""
        sender_email = args.strip() if args else msg.frm.id
        if not is_email(sender_email):
            sender_email = self.get_user_email(msg, sender_email)
        if not sender_email:
            return "User not found"

        try:
            event_id = self.get_event_id_from_message(msg)
        except Exception:
            event_id = None
        if not event_id:
            return "Could not find event"

        try:
            response = self.do_rsvp(event_id, sender_email)
        except Exception:
            return "Failed to RSVP"

        rsvp_id = response.get("_id", {}).get("$oid", "")
        return (
            self.rsvp_list(msg, args)
            if rsvp_id
            else response.get("error", "Failed to RSVP")
        )

    @botcmd
    def rsvp_list(self, msg, args):
        """List of RSVPs for an event"""
        try:
            event_id = self.get_event_id_from_message(msg)
        except Exception:
            event_id = None
        if not event_id:
            return "Could not find event"

        event = self.get_event(event_id)
        names = [
            (
                rsvp["user"].get("nick", "").strip() or rsvp["user"]["name"],
                rsvp.get("note"),
            )
            for rsvp in event["rsvps"]
            if not rsvp["cancelled"]
        ]
        rsvp_list = "\n".join(
            [
                "{}. {} *({})*".format(i, name, note)
                if note
                else "{}. {}".format(i, name, note)
                for (i, (name, note)) in enumerate(names, start=1)
            ]
        )
        content = "All RSVPs:\n\n{}".format(rsvp_list)
        return content if names else "No RSVPs"

    @staticmethod
    def create_event(name, date, time, description):
        url = "{}/event".format(BASE_URL)
        headers = {
            "Authorization": "token {}".format(os.environ["RSVP_TOKEN"])
        }
        response = requests.post(
            url,
            data={
                "date": date,
                "time": time,
                "event-name": name,
                "event-description": description,
            },
            headers=headers,
        )
        return "Success!" if response.status_code == 200 else "Failed"

    @staticmethod
    def update_event(event_id, description):
        url = "{}/api/event/{}".format(BASE_URL, event_id)
        headers = {
            "Authorization": "token {}".format(os.environ["RSVP_TOKEN"])
        }
        response = requests.patch(
            url, json={"description": description}, headers=headers
        )
        return (
            "Successfully updated event"
            if response.status_code == 200
            else "Failed"
        )

    # HACK: Need a regex command to allow not having a space after the command
    # name "create rsvp ". Errbot code splits on ' ' when trying to figure out
    # the command name, and if there's no space after the command name, but a
    # new-line, the match fails! We hack around this by using a regexp command.
    # Also, command name cannot start with rsvp, since rsvp list matches first
    # and this command never runs!
    @re_botcmd(pattern="create rsvp\s+([\s\S]*)")
    def create_rsvp(self, msg, match):
        """Create a new RSVP event"""
        info, = match.groups()
        name, date, description = info.strip().split("\n", 2)
        parsed_date = dateparser.parse(
            date_replace_period_with_colon(date),
            settings={"PREFER_DATES_FROM": "future"},
        )
        try:
            date, time = parsed_date.date(), parsed_date.time()
        except AttributeError:
            return "Could not parse date"

        event_id = self.get_event_id(name, date)
        if not event_id:
            return self.create_event(name, date, time, description)

        return self.update_event(event_id, description)
