from errbot import BotPlugin, botcmd

MESSAGE = """{}, you should [read this message](https://namma-loafers.zulipchat.com/#narrow/stream/115322-zulip/subject/Keybindings.2FShortcuts/near/131101688) - some shortcuts + a picture that sort of describes the UI - to start feeling comfortable here.

If you are on a desktop, set your zoom level to 120% or so, to make the UI less overwhelming (`Ctrl+Shift++`)
"""


class Welcome(BotPlugin):
    """Plugin to welcome new users."""

    @botcmd
    def welcome(self, msg, args):
        """Welcome new users"""
        return MESSAGE.format(args)
