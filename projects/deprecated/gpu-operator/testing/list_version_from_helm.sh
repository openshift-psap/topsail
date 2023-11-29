#! /bin/bash

HELM_REPO_NAME="nvidia"
HELM_REPO_ADDR="https://nvidia.github.io/gpu-operator"
HELM_REPO_PROJ="gpu-operator"

# https://stackoverflow.com/a/21189044/341106
function parse_yaml {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

YAML_VALUES=$(mktemp /tmp/gpu-operator_helm_values.XXXXXX.yaml)
curl -s ${HELM_REPO_ADDR}/index.yaml > $YAML_VALUES


print_name_versions() {
    target_name="$1"
    echo "Version of '$target_name' available in ${HELM_REPO_ADDR}:"

    in_name=0
    while read line; do
        key=$(echo $line | cut -d= -f1)
        value=$(echo $line | cut -d= -f2 | sed 's/^"//' | sed 's/"$//')
        HELM_values[$key]=$value
        if [[ "$key" == "entries__name" ]]; then
            [ "$value" == "$target_name" ] && in_name=1 || in_name=0
        fi
        if [[ "$key" == "entries__version" && "$in_name" == "1" ]]; then
            echo "- $value"
        fi
    done <<< $(parse_yaml ${YAML_VALUES} "")
}
print_name_versions "gpu-operator"
