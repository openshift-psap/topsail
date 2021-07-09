FROM registry.access.redhat.com/ubi8/ubi

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP CI artifacts" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"

# Add image scripts and files for running as a system container
COPY build/root /

COPY requirements.txt /

# Install openshift-ansible RPMs and some debugging tools
RUN yum install -y \
		glibc-langpack-en \
		go git make jq vim wget rsync \
		python3 python3-devel python3-pip python3-setuptools && \
	python3 -m pip install --no-cache-dir --upgrade setuptools pip wheel && \
	python3 -m pip install --no-cache-dir -r /requirements.txt && \
	yum clean all && \
	rm -rf $HOME/.cache && \
	rm -rf /var/cache/yum


# Install dependencies: `oc`
ARG OCP_CLI_VERSION=latest
ARG OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz
RUN curl ${OCP_CLI_URL} | tar xfz - -C /usr/local/bin oc

# Install dependencies: `helm`
ARG HELM_VERSION=v3.5.1
ARG HELM_URL=https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz
RUN curl ${HELM_URL} | tar xfz - -C /usr/local/bin --strip-components 1 linux-amd64/helm


# Install dependencies: `operator-sdk`
ARG OPERATOR_SDK_VERSION=v1.6.2
ARG OPERATOR_SDK_URL=https://github.com/operator-framework/operator-sdk/releases/download/${OPERATOR_SDK_VERSION}
RUN cd /usr/local/bin \
 && curl -LO ${OPERATOR_SDK_URL}/operator-sdk_linux_amd64 \
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
    HOME=/opt/ci-artifacts/src/ \
    ANSIBLE_CONFIG="/etc/ansible/ansible.cfg" \
    INSIDE_CI_IMAGE="y"

COPY . ${HOME}/

# Prepare the image for must-gather support
RUN mkdir /must-gather && chmod 777 /must-gather

# Prepare the GPU-operator's gather script
RUN ln -s ${HOME}/toolbox/gpu-operator/must-gather.sh /usr/bin/gpu-operator_gather

# Ensure directory permissions are properly set
RUN mkdir -p ${HOME}/.ansible/tmp && chmod 777 ${HOME} -R

WORKDIR ${HOME}
