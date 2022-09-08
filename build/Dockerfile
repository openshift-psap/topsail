FROM registry.access.redhat.com/ubi8/ubi

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP CI artifacts" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN yum install -y --quiet \
	        git jq vim wget rsync time gettext httpd-tools make \
		python3.9 python3-pip python3-setuptools python3-virtualenv \
  && yum clean all \
  && rm -rf $HOME/.cache && rm -rf /var/cache/yum \
  && virtualenv -p /usr/bin/python3.9 $VIRTUAL_ENV \
  && pip install --upgrade pip

# Install dependencies: ocm, oc

ARG CURL_OPTIONS="--silent --location --fail --show-error"

ARG OCP_CLI_VERSION=latest
ARG OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz

ARG OCM_CLI_VERSION=v0.1.63
ARG OCM_CLI_URL=https://github.com/openshift-online/ocm-cli/releases/download/${OCM_CLI_VERSION}/ocm-linux-amd64

# Install dependencies: ocm, oc
RUN curl ${CURL_OPTIONS} ${OCP_CLI_URL} | tar xfz - -C /usr/local/bin oc \
 && curl ${CURL_OPTIONS} ${OCM_CLI_URL} --output /usr/local/bin/ocm && chmod +x /usr/local/bin/ocm

# Set up Ansible
RUN mkdir -p /etc/ansible \
    && echo "localhost ansible_connection=local" > /etc/ansible/hosts
COPY config/ansible.cfg /etc/ansible/ansible.cfg
COPY config/inventory/hosts /etc/ansible/inventory/hosts

RUN sed -i 's|roles/|/opt/ci-artifacts/roles/|' /etc/ansible/ansible.cfg \
 && sed -i 's|callback_plugins = ../|callback_plugins = /opt/ci-artifacts/src/|' /etc/ansible/ansible.cfg

# Set up the runner user
ENV USER_NAME=psap-ci-runner \
    USER=psap-ci-runner \
    HOME=/opt/ci-artifacts/src \
    ANSIBLE_CONFIG="/etc/ansible/ansible.cfg" \
    INSIDE_CI_IMAGE="y"

COPY . ${HOME}/

# Install Python requirements
RUN pip install --quiet --no-cache-dir -r ${HOME}/requirements.txt && \
    pip install --quiet --no-cache-dir -r ${HOME}/subprojects/wdm/requirements.txt \
    pip install --quiet --no-cache-dir -r ${HOME}/subprojects/cloud-watch/requirements.txt

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


WORKDIR ${HOME}

ENTRYPOINT ["bash"]
CMD ["run"]
