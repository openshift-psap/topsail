#! /bin/bash

BASE_BRANCH=master

for branch in $(git branch | grep release-)
do
    git checkout $branch
    git pull . $BASE_BRANCH --ff-only
    git push
done
git checkout master
git fetch
