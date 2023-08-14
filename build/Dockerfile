FROM registry.access.redhat.com/ubi9/ubi

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP CI artifacts" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN yum install -y --quiet \
	        git jq vim wget rsync time gettext httpd-tools make \
		python3.9 python3-pip python3-setuptools procps go-toolset \
  && yum clean all \
  && pip install virtualenv \
  && rm -rf $HOME/.cache && rm -rf /var/cache/yum \
  && virtualenv -p /usr/bin/python3.9 $VIRTUAL_ENV \
  && pip install --upgrade pip

# Install dependencies: ocm, oc

ARG CURL_OPTIONS="--silent --location --fail --show-error"

# ARG OCP_CLI_URL=https://people.redhat.com/~kpouget/22-08-26/openshift-client-linux.tar.gz

ARG OCP_CLI_VERSION=latest
ARG OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz

RUN curl ${CURL_OPTIONS}  ${OCP_CLI_URL}  | tar xfz - -C /usr/local/bin oc

# Set up the runner user
ENV USER_NAME=psap-ci-runner \
    USER=psap-ci-runner \
    HOME=/opt/ci-artifacts/src \
    INSIDE_CI_IMAGE="y"
ENV ANSIBLE_CONFIG="${HOME}/config/ansible.cfg"

COPY . ${HOME}/

# Install Python requirements

RUN pip install --quiet --no-cache-dir -r ${HOME}/requirements.txt && \
    (cd ${HOME} && ./testing/common/visualize.py prepare_matbench && mv /tmp/prometheus/bin/prometheus /usr/local/bin)

# Prepare the CI `run` entrypoint

# Prepare the CI `matbench`

# Ensure directory permissions are properly set

# This should run after all the `pip` commands.  It is necessary so
# that we can `pip install` from inside the image.

RUN echo -e '#!/usr/bin/env bash \n\
exec ${HOME}/testing/run "$@" \n\
' > /usr/local/bin/run; chmod ugo+x /usr/local/bin/run \
 \
 && ln -s ${HOME}/subprojects/matrix-benchmarking/bin/matbench /usr/local/bin/ \
 \
 && mkdir -p ${HOME}/.ansible/tmp && chmod 777 ${HOME} -R \
 && chgrp -R 0 "${VIRTUAL_ENV}" \
 && chmod -R g=u "${VIRTUAL_ENV}"

RUN ln -s $(which oc) /usr/bin/kubectl

# Disable git dubious ownership detection in the image
RUN git config --global --add safe.directory '*'

WORKDIR ${HOME}

ENTRYPOINT ["bash"]
CMD ["run"]
