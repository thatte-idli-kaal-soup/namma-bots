#!/bin/sh
DATETOUSE="$(TZ=Asia/Kolkata date "+%A. %B %d, %Y")"
SUBJECT="Checkins! $DATETOUSE"
CONTENT="Welcome to [checkins](checkins.txt)!"
curl https://api.zulip.com/v1/messages \
    -u $ZULIP_BOT_EMAIL_CHECKINS:$ZULIP_BOT_KEY_CHECKINS \
    -d "type=stream" \
    -d "to=checkins" \
    -d "subject=$SUBJECT" \
    -d "content=$CONTENT"
