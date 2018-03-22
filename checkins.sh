#!/bin/sh
DATETOUSE="$(TZ=Asia/Kolkata date "+%A. %B %d, %Y")"
SUBJECT="Checkins! $DATETOUSE"
CONTENT="Welcome to [checkins](https://raw.githubusercontent.com/punchagan/namma-bots/master/checkins.txt)!"
curl https://namma-loafers.zulipchat.com/api/v1/messages \
    -u $ZULIP_BOT_EMAIL_CHECKINS:$ZULIP_BOT_KEY_CHECKINS \
    -d "type=stream" \
    -d "to=checkins" \
    -d "subject=$SUBJECT" \
    -d "content=$CONTENT"
