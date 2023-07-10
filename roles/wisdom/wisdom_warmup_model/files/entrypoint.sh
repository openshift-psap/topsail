#! /bin/bash
set -o errexit
set -o pipefail
set -o nounset
set -o errtrace
set -x


PROMPT="- name: Install tensorflow on RHEL"
CONTEXT=""

echo "CONCURRENCY: ${CONCURRENCY}"
echo "TOTAL_REQUESTS: ${TOTAL_REQUESTS}"
echo "PROMPT: ${PROMPT}"
echo "CONTEXT: ${CONTEXT}"

cd /etc/protos 

ghz --insecure --proto ./wisdomextservice.proto \
  --call caikit.runtime.WisdomExt.WisdomExtService/CodeGenerationTaskPredict \
  -d "{ \"prompt\": \"${PROMPT}\", \"context\": \"${CONTEXT}\" }" \
  modelmesh-serving.${WISDOM_NAMESPACE}.svc:8033 \
  --metadata="{\"mm-vmodel-id\":\"ansible-wisdom\"}" \
  -c ${CONCURRENCY} \
  --total ${TOTAL_REQUESTS} \
  --disable-template-data \
  -t 240s
