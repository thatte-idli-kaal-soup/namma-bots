#!/usr/bin/env python3

from collections import defaultdict
import datetime
from os import environ as env
import re
from os.path import abspath, dirname, join
import sys
import urllib

from lexrank import LexRank, STOPWORDS
import markdown
import jinja2
import numpy as np
import sendgrid
from sendgrid.helpers.mail import Email, Content, Mail, Personalization
import zulip


HERE = dirname(abspath(__file__))
SENDER_EMAIL = env.get("SENDER_EMAIL")
TITLE_FORMAT = "{} weekly summary ({:%d %b} to {:%d %b})"
LINK_RE = re.compile("(\[.*\]\(https{0,1}://.+\))|(https{0,1}://.+)")
PUNCTUATION_RE = re.compile("([.?!])\s")

# #### Helpers to generate urls from zulip server repo: zerver.lib.url_encoding


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


class Summarizer:
    def __init__(self, all_messages):
        self.documents = {}
        for stream, data in all_messages.items():
            for topic, messages in data["topics"].items():
                text = "\n".join(
                    self.clean_content(message) for message in messages
                )
                self.documents[(stream, topic)] = [
                    sentence.strip()
                    for sentence in text.splitlines()
                    if sentence.strip()
                ]
        self.summarizer = LexRank(
            self.documents.values(),
            keep_emails=True,
            keep_urls=True,
            stopwords=STOPWORDS["en"],
        )

    def get_summary(self, stream, topic, show_url_list=True):
        document = self.documents[(stream, topic)]
        threshold = 0.03
        summary_size = 2 if len(document) > 5 else 1
        fast_power_method = True
        lex_scores = self.summarizer.rank_sentences(
            document, threshold=threshold, fast_power_method=fast_power_method
        )

        sorted_ix = np.argsort(lex_scores)[::-1]
        url_list = self.get_url_list(document) if show_url_list else []
        return (
            [document[i] for i in sorted(sorted_ix[:summary_size])],
            url_list,
        )

    @staticmethod
    def get_url_list(document):
        links = [
            "[{link}]({link})".format(link=plain_link)
            if plain_link
            else md_link
            for sentence in document
            for (md_link, plain_link) in LINK_RE.findall(sentence)
        ]
        return links

    @staticmethod
    def clean_content(message):
        content = message["content"]
        return PUNCTUATION_RE.sub("\\1\n", content)


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


def create_email_body(messages, start_date, end_date, summarizer):
    env = jinja2.Environment(
        extensions=["jinja2.ext.i18n"], loader=jinja2.FileSystemLoader(HERE)
    )
    env.install_null_translations()
    template = env.get_template("weekly-summary-template.html")
    title = TITLE_FORMAT.format(SITE, start_date, end_date)
    return template.render(
        all_messages=messages,
        title=title,
        site=SITE,
        topic_narrow_url=topic_narrow_url,
        summarizer=summarizer,
        markdown=markdown.markdown,
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


def send_email(to_users, subject, html_body):
    sg = sendgrid.SendGridAPIClient(apikey=env.get("SENDGRID_API_KEY"))
    from_email = Email(SENDER_EMAIL)
    content = Content("text/html", html_body)
    to_emails = [
        Email("{} <{}>".format(name, email)) for name, email in to_users
    ]
    mail = Mail(from_email, subject, to_emails[0], content)
    for to_email in to_emails[1:]:
        personalization = Personalization()
        personalization.add_to(to_email)
        mail.add_personalization(personalization)
    print("Sending email...")
    try:
        response = sg.client.mail.send.post(request_body=mail.get())
    except Exception as e:
        # FIXME: Silently failing...
        print(e)
        return False

    return int(response.status_code / 200) == 2


def show_html_email(content):
    import tempfile
    import time
    import webbrowser

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf8", suffix="html"
    ) as f:
        f.write(content)
        webbrowser.open_new_tab(f.name)
        time.sleep(1)


def main():
    end_date = datetime.datetime.now()
    weekday = end_date.strftime("%A")
    if "DYNO" in env and weekday != env["HEROKU_CRON_DAY"]:
        sys.exit("Not running script today - {}".format(weekday))
    start_date = end_date - datetime.timedelta(days=7)
    all_messages = get_messages_in_timeperiod(start_date, end_date)
    messages = sort_streams(all_messages)
    summarizer = Summarizer(all_messages)
    content = create_email_body(messages, start_date, end_date, summarizer)
    subject = TITLE_FORMAT.format(SITE, start_date, end_date)
    users = [
        (member["full_name"], member["email"])
        for member in client.get_members()["members"]
        if not member["is_bot"]
    ]
    if "SENDGRID_API_KEY" in env:
        send_email(users, subject, content)
    else:
        show_html_email(content)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "zulip_api_email", help="Email ID of Zulip bot for fetching messages"
    )
    parser.add_argument(
        "zulip_api_key", help="API KEY of Zulip bot for fetching messages"
    )

    args = parser.parse_args()
    EMAIL = args.zulip_api_email
    API_KEY = args.zulip_api_key
    SITE = EMAIL.split("@")[-1]
    client = zulip.Client(email=EMAIL, api_key=API_KEY, site=SITE)
    main()
