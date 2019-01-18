#!/usr/bin/env python3

from collections import defaultdict
import datetime
import os
from os.path import abspath, dirname, join
import sys
import urllib

import jinja2
import zulip


HERE = dirname(abspath(__file__))
EMAIL = os.environ.get("ZULIP_API_EMAIL")
API_KEY = os.environ.get("ZULIP_API_SECRET")
SITE = EMAIL.split("@")[-1]
client = zulip.Client(email=EMAIL, api_key=API_KEY, site=SITE)

# Helpers to generate urls from zulip server repo: zerver.lib.url_encoding


def hash_util_encode(string: str) -> str:
    # Do the same encoding operation as hash_util.encodeHashComponent on the
    # frontend.
    # `safe` has a default value of "/", but we want those encoded, too.
    return (
        urllib.parse.quote(string.encode("utf-8"), safe=b"")
        .replace(".", "%2E")
        .replace("%", ".")
    )


def encode_stream(stream_id: int, stream_name: str) -> str:
    # We encode streams for urls as something like 99-Verona.
    stream_name = stream_name.replace(" ", "-")
    return str(stream_id) + "-" + hash_util_encode(stream_name)


def topic_narrow_url(site, stream_id, stream_name, topic) -> str:
    base_url = "https://%s/#narrow/stream/" % (site,)
    return "%s%s/topic/%s" % (
        base_url,
        encode_stream(stream_id, stream_name),
        hash_util_encode(topic),
    )


##########################################################################


def filter_messages_by_date(messages, start_date, end_date):
    filtered_messages = [
        message
        for message in messages
        if start_date.timestamp()
        <= message["timestamp"]
        <= end_date.timestamp()
    ]
    return filtered_messages


def filter_messages_ignored_messages(messages):
    messages = [
        message
        for message in messages
        if (
            message["sender_email"] != EMAIL
            and "mentioned" not in message["flags"]
        )
    ]
    return messages


def group_messages_by_topic(messages):
    by_topic = defaultdict(list)
    for message in messages:
        by_topic[message["subject"]].append(message)

    return by_topic


def get_streams():
    result = client.get_streams()
    streams = result["streams"]
    return streams


def get_stream_messages(stream_name, start_date, end_date):
    request = {
        "apply_markdown": False,
        "num_before": 5000,
        "num_after": 0,
        "anchor": 10000000000000000,
        "narrow": [
            {"negated": False, "operator": "stream", "operand": stream_name}
        ],
    }
    result = client.get_messages(request)
    messages = result["messages"]
    messages = filter_messages_by_date(messages, start_date, end_date)
    messages = filter_messages_ignored_messages(messages)
    return messages


def get_messages_in_timeperiod(start_date, end_date):
    streams = get_streams()
    all_messages = {}
    print("Fetching stream messages", end=" ")
    for stream in streams:
        print(".", end="")
        sys.stdout.flush()
        messages = get_stream_messages(stream["name"], start_date, end_date)
        if messages:
            all_messages[stream["name"]] = {
                "stream": stream,
                "topics": group_messages_by_topic(messages),
            }
    return all_messages


def create_email_body(messages, start_date, end_date):
    env = jinja2.Environment(
        extensions=["jinja2.ext.i18n"], loader=jinja2.FileSystemLoader(HERE)
    )
    env.install_null_translations()
    template = env.get_template("weekly-summary-template.html")
    title = "Zulip weekly summary ({:%d %b} to {:%d %b})".format(
        start_date, end_date
    )
    return template.render(
        all_messages=messages,
        title=title,
        site=SITE,
        topic_narrow_url=topic_narrow_url,
    )


def sort_topics(stream_data):
    topics = stream_data["topics"]
    topics = sorted(
        topics.items(), key=lambda item: len(item[1]), reverse=True
    )
    sorted_topics = dict(stream_data)
    sorted_topics["topics"] = topics
    return sorted_topics


def sort_streams(data):
    data = sorted(
        data.items(), key=lambda item: len(item[1]["topics"]), reverse=True
    )
    return [
        (stream_name, sort_topics(stream_data))
        for stream_name, stream_data in data
    ]


if __name__ == "__main__":
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=7)
    all_messages = get_messages_in_timeperiod(start_date, end_date)
    messages = sort_streams(all_messages)
    content = create_email_body(messages, start_date, end_date)
