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
        -o: Output dir for build config
        -q: Quay.io Org/Repo
        -a: Authfile for quay.io
    "
}

while getopts n:t:g:d:p:q:a:b:o:h flag
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
        o) outdir=${OPTARG};;
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
elif [[ -z $outdir ]] ; then
    echo -- "Build config output dir (-o) required"
    exit 1
fi

export image_name=$name
export image_tag=$tag
if [[ -n $dockerfile ]] ; then
    export docker_path=$dockerfile
    template="roles/utils_build_push_image/templates/local.yml"
    #FIXME: INCOMPLETE OPTION
elif [[ -n $repo ]] ; then
    export git_repo=$repo
    export context_dir=$path
    export branch=$branch
    template="roles/utils_build_push_image/templates/repo.yml"
fi

rm -f "$outdir/config.yml $outdir/temp.yml"
( echo "cat <<EOF >$outdir/config.yml";
  cat "$template";
  echo "EOF";
) >"$outdir/temp.yml"
source "$outdir/temp.yml"
rm -f "$outdir/temp.yml"
