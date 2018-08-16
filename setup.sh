# Setup errbot-zulip-backend
if [ ! -d errbot-backend-zulip ]; then
    git clone https://github.com/zulip/errbot-backend-zulip.git
fi
pushd errbot-backend-zulip
git pull origin master
pip install -r requirements.txt
popd

# Setup errbot
pip install -r requirements.txt
