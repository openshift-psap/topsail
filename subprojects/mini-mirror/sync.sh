#!/bin/bash

set -euxo pipefail

reposync -p $SYNC_DESTINATION --download-metadata --repoid rhel-8-for-x86_64-baseos-rpms
reposync -p $SYNC_DESTINATION --download-metadata --repoid rhel-8-for-x86_64-baseos-eus-rpms --releasever=8.2

reposync -p $SYNC_DESTINATION --download-metadata --repoid rhocp-4.6-for-rhel-8-x86_64-rpms
reposync -p $SYNC_DESTINATION --download-metadata --repoid rhocp-4.7-for-rhel-8-x86_64-rpms
reposync -p $SYNC_DESTINATION --download-metadata --repoid rhocp-4.8-for-rhel-8-x86_64-rpms

touch healthy
