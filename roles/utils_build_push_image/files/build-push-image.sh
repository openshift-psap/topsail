#! /bin/bash

function help() {
    printf -- "Options:
        -h: Help
        -n: Name of image
        -t: Tag for image
        -d: Path/Name of Dockerfile
        -g: Git repo containing Dockerfile
        -p: Path/Name of git repo Dockerfile
        -q: Quay.io Org/Repo
        -a: Authfile for quay.io
    "
}

while getopts n:t:g:d:p:q:a:h flag
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
        *) exit 1 ;;
    esac
done

if [[ -z $repo && -z $dockerfile ]] ; then
    printf -- "Either a git repo (-g) or Dockerfile (-d) is required\n"
    exit 1
elif [[ -n $repo && -n $dockerfile ]] ; then
    printf -- "Cannot have both -g and -d\n"
    exit 1
elif [[ -n $repo && -z $path ]] ; then
    printf -- "Must supply path to Dockerfile within git repo (-p)\n"
    exit 1
elif [[ -z $name || -z $tag ]] ; then
    printf -- "Image name (-n) and tag (-t) required\n"
    exit 1
fi

if [[ -n $dockerfile ]] ; then
    podman build -t $name:tag -f $dockerfile
elif [[ -n $repo ]] ; then
    git clone $repo
    podman build -t $name:tag -f $path
fi

if [[ -n ${quay:8} ]] ; then
    if [[ -z $authfile ]] ; then
        printf -- "Authfile (-a) required for push\n"
    fi
    podman tag $name:$tag $quay:$tag
    podman push --tls-verify=false --authfile $authfile $quay:$tag
fi
