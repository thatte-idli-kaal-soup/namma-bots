import re

from errbot import BotPlugin, botcmd, arg_botcmd


def get_youtube_ids(text):
    # Taken from https://github.com/zulip/zulip/blob/b570c0dafa9cd8cf7d4b2af51c5cc8496197f405/zerver/lib/bugdown/__init__.py#L676
    schema_re = r"(?:https?://)"
    host_re = r"(?:youtu\.be/|(?:\w+\.)?youtube(?:-nocookie)?\.com/)"
    param_re = r"(?:(?:(?:v|embed)/)|(?:(?:watch(?:_popup)?(?:\.php)?)?(?:\?|#!?)(?:.+&)?v=))"
    id_re = r"([0-9A-Za-z_-]+)"
    youtube_re = r"({schema_re}?{host_re}{param_re}?)?{id_re}(?(1).+)?"
    youtube_re = youtube_re.format(
        schema_re=schema_re, host_re=host_re, id_re=id_re, param_re=param_re
    )
    ids = [id_ for prefix, id_ in re.findall(youtube_re, text) if prefix]
    return ids


def get_playlist(text):
    ids = get_youtube_ids(text)
    unique = sorted(set(ids), key=lambda x: ids.index(x), reverse=True)
    last_50 = ",".join(unique[:50])
    return "http://www.youtube.com/watch_videos?video_ids={}".format(last_50)


class Playlist(BotPlugin):
    """Plugin to playlists in Zulip."""

    @arg_botcmd("--topic", type=str)
    @arg_botcmd("--stream", type=str)
    def playlist(self, msg, stream, topic):
        """Create a new playlist from specific topic or stream."""

        if msg.to._client is None:
            from zulip import Client

            config = dict(self.bot_config.BOT_IDENTITY)
            config["api_key"] = config.pop("key")
            client = Client(**config)

        else:
            client = self._bot.client
            if stream is None:
                stream = msg.to.title
                topic = msg.to.subject

        narrow = [
            {"negated": False, "operator": "stream", "operand": stream},
            {"negated": False, "operator": "topic", "operand": topic},
        ]
        if topic is None:
            narrow = narrow[:1]

        request = {
            "apply_markdown": False,
            "num_before": 5000,
            "num_after": 0,
            "anchor": 10000000000000000,
            "narrow": narrow,
        }
        result = client.get_messages(request)
        if "messages" not in result:
            return "No messages in {} > {}".format(stream, topic)
        messages = result["messages"]
        content = [m["content"] for m in messages]
        text = "\n".join(content)
        return get_playlist(text)
