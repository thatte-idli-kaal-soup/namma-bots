#!/usr/bin/env bash
git push origin master

ssh muse-amuse.in <<EOF
pushd ~/code/namma-bots

pushd errbot-backend-zulip
git pull origin master
popd

git pull origin master
source .envrc
killall errbot
errbot -d
EOF
