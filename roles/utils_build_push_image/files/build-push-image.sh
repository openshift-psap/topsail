#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset

function help() {
    echo "Options:
        -h: Help
        -n: Name of image
        -t: Tag for image
        -d: Path/Name of Dockerfile
        -g: Git repo containing Dockerfile
        -p: Path/Name of git repo Dockerfile
        -b: Branch of repo to clone
        -q: Quay.io Org/Repo
        -a: Authfile for quay.io
    "
}

while getopts n:t:g:d:p:q:a:b:h flag
do
    case "${flag}" in
        h) help
           exit 0 ;;
        n) name=${OPTARG};;
        t) tag=${OPTARG};;
        g) repo=${OPTARG};;
        d) dockerfile=${OPTARG};;
        p) path=${OPTARG};;
        q) quay="quay.io/${OPTARG}";;
        a) authfile=${OPTARG};;
        b) branch=${OPTARG};;
        *) exit 1 ;;
    esac
done

if [[ -z $repo && -z $dockerfile ]] ; then
    echo "Either a git repo (-g) or Dockerfile (-d) is required"
    exit 1
elif [[ -n $repo && -n $dockerfile ]] ; then
    echo "Cannot have both -g and -d"
    exit 1
elif [[ -n $repo && -z $path ]] ; then
    echo -- "Must supply path to Dockerfile within git repo (-p)"
    exit 1
elif [[ -z $name || -z $tag ]] ; then
    echo -- "Image name (-n) and tag (-t) required"
    exit 1
fi

if [[ -n $dockerfile ]] ; then
    podman build -t $name:tag -f $dockerfile
elif [[ -n $repo ]] ; then
    if [[ -n $branch ]] ; then
        git clone --depth 1 $repo --branch $branch repo
    else
        git clone --depth 1 $repo repo
    fi
    cd repo
    podman build -t $name:tag -f $path
fi

if [[ -n ${quay:8} ]] ; then
    if [[ -z $authfile ]] ; then
        echo "Authfile (-a) required for push"
    fi
    podman tag $name:$tag $quay:$tag
    podman push --tls-verify=false --authfile $authfile $quay:$tag
fi
