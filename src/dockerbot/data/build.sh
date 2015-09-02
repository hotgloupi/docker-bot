GIT_TAG="`git describe --always`"
cd src
zip -r dockerbot-${GIT_TAG}.zip __main__.py dockerbot yaml
