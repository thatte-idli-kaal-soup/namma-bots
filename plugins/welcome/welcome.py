from errbot import BotPlugin, botcmd

MESSAGE = """{}, welcome to :zulip:!

Check out the tour [here](https://zulipchat.com/hello/) to get a quick overview of Zulip's streams and topics.

[This comic](https://pbs.twimg.com/media/DbCNzaPX4AATH1A.jpg) gives the same overview, if you prefer hand drawn comics!

If you are on a desktop, set your zoom level to 120% or so, to make the UI less overwhelming (`Ctrl+Shift++`)

It might also be useful to tweak your [notification settings](#settings/notifications).

**A few keyboard shortcuts**

- `Ctrl + Enter` sends a new message. (can be changed by clicking a checkbox below compose box)
- `Enter` just inserts a new line - to send longer messages.
- `?` will show a list of keyboard shortcuts - quite useful.
- `n` will take you to the next unread topic.
- `j` and `k` will scroll through messages within the current narrow/view.
- `p` will take you to next unread private message.
-  :left:  key lets you edit the last sent message.
- Hitting the `+` key when a message is selected (blue frame appears around it) adds a :+1: reaction to it. Hit `:` to add other reactions.

"""


class Welcome(BotPlugin):
    """Plugin to welcome new users."""

    @botcmd
    def welcome(self, msg, args):
        """Welcome new users"""
        return MESSAGE.format(args.strip())
