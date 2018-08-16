import logging
import os
from os.path import abspath, dirname, join

HERE = dirname(abspath(__file__))
BACKEND = 'Zulip'
BOT_EXTRA_BACKEND_DIR = join(HERE, 'errbot-backend-zulip')
BOT_DATA_DIR = join(HERE, 'data')
BOT_EXTRA_PLUGIN_DIR = join(HERE, 'plugins')
BOT_LOG_FILE = join(HERE, 'errbog.log')
BOT_LOG_LEVEL = logging.INFO
BOT_IDENTITY = {  # Fill this with the corresponding values in your bot's `.zuliprc`
    'email': 'edison-bot@namma-loafers.zulipchat.com',
    'key': os.environ.get('ZULIP_API_SECRET'),
    'site': 'https://namma-loafers.zulipchat.com',
}
BOT_ADMINS = ('punchagan@muse-amuse.in',)
CHATROOM_PRESENCE = ()
BOT_PREFIX = '@**Edison** '
