import json
import re

import bs4
from errbot import BotPlugin
import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_cn


def allowed_gai_family():
    family = socket.AF_INET  # force IPv4
    return family


# Force using IPv4 for the server where this code runs
urllib3_cn.allowed_gai_family = allowed_gai_family

JSON_DATA_RE = re.compile("window._sharedData = (.*);")
MSG_FORMAT = """\
{image}

**@{username}**: {description}

https://instagram.com/p/{shortcode}
"""


class Instagram(BotPlugin):
    """Plugin to track specific Instagram accounts in specific topics."""

    # Instagram to Zulip mapping
    users = {"ultiid": ("Ultimate Frisbee", "International Game")}

    def fetch_updates(self):
        """Fetch updates from specific instagram accounts to specific topics."""
        self.log.info("Fetching updates from instagram... ")
        for username, (topic, stream) in self.users.items():
            posts = fetch_instagram_updates(username)
            if not posts:
                self.log.error("No posts found for: {}".format(username))
                continue

            last_post_shorcode = self.get(username, None)
            if last_post_shorcode is None:
                posts = posts[:1]
            else:
                for i, post in enumerate(posts):
                    if post["shortcode"] == last_post_shorcode:
                        break
                posts = posts[:i]

            for post in posts:
                post.update(dict(username=username))
                self.send_zulip_message(post, stream, topic)

            if posts:
                self[username] = posts[0]["shortcode"]

    def activate(self):
        super().activate()
        self.start_poller(600, self.fetch_updates)

    def get_zulip_client(self):
        if hasattr(self._bot, "client"):
            return self._bot.client

        from zulip import Client

        config = dict(self.bot_config.BOT_IDENTITY)
        config["api_key"] = config.pop("key")
        client = Client(**config)
        self._bot.client = client
        return client

    def send_zulip_message(self, post, stream, topic):
        client = self.get_zulip_client()
        msg = {
            "subject": topic,
            "to": stream,
            "type": "stream",
            "content": MSG_FORMAT.format(**post),
        }
        return client.send_message(msg)


def fetch_instagram_updates(username):
    response = requests.get("https://instagram.com/{}/".format(username))
    soup = bs4.BeautifulSoup(response.text, features="html.parser")
    script = soup.find("script", text=JSON_DATA_RE)
    parsed_posts = []
    if script is None:
        return parsed_posts
    data = json.loads(JSON_DATA_RE.search(script.text).group(1))
    posts = data["entry_data"]["ProfilePage"][0]["graphql"]["user"][
        "edge_owner_to_timeline_media"
    ]["edges"]
    for post in posts:
        node = post["node"]
        image = node["display_url"]
        description = node["edge_media_to_caption"]["edges"][0]["node"]["text"]
        shortcode = node["shortcode"]
        parsed_posts.append(
            dict(image=image, description=description, shortcode=shortcode)
        )
    return parsed_posts
