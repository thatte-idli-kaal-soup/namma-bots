git push origin master

ssh muse-amuse.in <<EOF
pushd ~/code/namma-bots
git pull origin master
source .envrc
killall errbot
errbot -d
EOF
