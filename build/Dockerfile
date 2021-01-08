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
RUN sed -i '19s/roles\//\/opt\/ci-artifacts\/roles/' /etc/ansible/ansible.cfg

# Set up the runner user
ENV USER_UID=1001 \
    USER_NAME=psap-ci-runner \
    HOME=/opt/ci-artifacts/src/ \
    ANSIBLE_OPTS="-vvv" \
    WORK_DIR=/opt/ci-artifacts/src/

COPY group_vars ${HOME}/group_vars
COPY inventory ${HOME}/inventory
COPY playbooks ${HOME}/playbooks
COPY roles ${HOME}/roles

RUN useradd -u ${USER_UID} -g 0 -d ${HOME} ${USER_NAME}

# Ensure directory permissions are properly set
RUN mkdir -p ${HOME}/.ansible/tmp && \
	chown -R ${USER_UID}:0 ${HOME} && \
	chmod -R ug+rwx ${HOME}

RUN /usr/local/bin/user_setup

USER ${USER_UID}
WORKDIR ${HOME}
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD [ "/usr/local/bin/run" ]
