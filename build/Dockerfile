FROM registry.access.redhat.com/ubi8/ubi

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP CI artifacts" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"

# Install openshift-ansible RPMs and some debugging tools
RUN yum install -y --quiet \
		glibc-langpack-en \
		go git make jq vim wget rsync time gettext httpd-tools \
		python3.9 python3-pip python3-setuptools python3-virtualenv && \
	yum clean all && \
	rm -rf $HOME/.cache && \
	rm -rf /var/cache/yum

ENV VIRTUAL_ENV=/opt/venv
RUN virtualenv -p /usr/bin/python3.9 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip

# Install dependencies: `oc`
ARG OCP_CLI_VERSION=latest
ARG OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz
RUN curl --silent ${OCP_CLI_URL} | tar xfz - -C /usr/local/bin oc

# Install dependencies: `ocm`
ARG OCM_CLI_VERSION=v0.1.63
ARG OCM_CLI_URL=https://github.com/openshift-online/ocm-cli/releases/download/${OCM_CLI_VERSION}/ocm-linux-amd64
RUN curl --silent -L ${OCM_CLI_URL} --output /usr/local/bin/ocm
RUN chmod +x /usr/local/bin/ocm

# Install dependencies: `helm`
ARG HELM_VERSION=v3.5.1
ARG HELM_URL=https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz
RUN curl --silent ${HELM_URL} | tar xfz - -C /usr/local/bin --strip-components 1 linux-amd64/helm

# Install dependencies: `rosa`
ARG ROSA_VERSION=latest
ARG ROSA_URL=https://mirror.openshift.com/pub/openshift-v4/clients/rosa/${ROSA_VERSION}/rosa-linux.tar.gz
RUN curl --silent ${ROSA_URL} | tar xfz - -C /usr/local/bin

# Install dependencies: `operator-sdk`
ARG OPERATOR_SDK_VERSION=v1.6.2
ARG OPERATOR_SDK_URL=https://github.com/operator-framework/operator-sdk/releases/download/${OPERATOR_SDK_VERSION}
RUN cd /usr/local/bin \
 && curl --silent -LO ${OPERATOR_SDK_URL}/operator-sdk_linux_amd64 \
 && mv operator-sdk_linux_amd64 operator-sdk \
 && chmod +x operator-sdk

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
RUN echo -e '#!/usr/bin/env bash \n\
exec ${HOME}/testing/run "$@" \n\
' > /usr/local/bin/run; chmod ugo+x /usr/local/bin/run

# Prepare the CI `matbench`
RUN ln -s ${HOME}/subprojects/matrix-benchmarking/bin/matbench /usr/local/bin/

# Ensure directory permissions are properly set
RUN mkdir -p ${HOME}/.ansible/tmp && chmod 777 ${HOME} -R

# This should run after all the `pip` commands.  It is necessary so
# that we can `pip install` from inside the image.
RUN chgrp -R 0 "${VIRTUAL_ENV}" \
 && chmod -R g=u "${VIRTUAL_ENV}"


WORKDIR ${HOME}

ENTRYPOINT ["bash"]
CMD ["run"]
