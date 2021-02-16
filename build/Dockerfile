FROM registry.access.redhat.com/ubi8/ubi

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP Ci artifacts" \
      	io.k8s.description="This are artifacts to run PSAP Ci" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"

# Add image scripts and files for running as a system container
COPY build/root /

# Install openshift-ansible RPMs and some debugging tools
RUN yum install -y \
		glibc-langpack-en \
		git make jq vim wget \
		python3 python3-devel python3-pip python3-setuptools && \
	pip3 install --no-cache-dir --upgrade setuptools pip && \
	pip3 install --no-cache-dir \
		openshift \
		ansible==2.9.* && \
	yum clean all && \
	rm -rf $HOME/.cache && \
	rm -rf /var/cache/yum

# Set up Ansible
RUN mkdir -p /etc/ansible \
    && echo "localhost ansible_connection=local" > /etc/ansible/hosts
COPY ansible.cfg /etc/ansible/ansible.cfg
RUN sed -i '19s/roles\//\/opt\/ci-artifacts\/roles/' /etc/ansible/ansible.cfg \
 && sed -i 's|callback_plugins = ./|callback_plugins = /opt/ci-artifacts/src/|' /etc/ansible/ansible.cfg

# Set up the runner user
ENV USER_NAME=psap-ci-runner \
    USER=psap-ci-runner \
    HOME=/opt/ci-artifacts/src/ \
    INSIDE_CI_IMAGE="y"

COPY . ${HOME}/
RUN rm ${HOME}/ansible.cfg

# Ensure directory permissions are properly set
RUN mkdir -p ${HOME}/.ansible/tmp && chmod 777 ${HOME} -R

WORKDIR ${HOME}
