#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x


env
PROMPT="- name: Install python-3.12 on RHEL"
CONTEXT=""
cd /etc/protos
ls
   
grpcurl -plaintext -proto wisdomextservice.proto \
    -d "{ \"prompt\": \"${PROMPT}\", \"context\": \"${CONTEXT}\" }" \
    -H "mm-vmodel-id: ansible-wisdom" \
    modelmesh-serving.${WISDOM_NAMESPACE}.svc:8033 \
    caikit.runtime.WisdomExt.WisdomExtService/CodeGenerationTaskPredict
