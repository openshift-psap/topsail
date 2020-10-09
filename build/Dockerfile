FROM centos:8 

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

USER root

LABEL 	io.k8s.display-name="OpenShift PSAP Ci artifacts" \
      	io.k8s.description="This are artifacts to run PSAP Ci" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"

# Add image scripts and files for running as a system container
COPY build/root /

# Install openshift-ansible RPMs and some debugging tools
RUN yum install -y epel-release \
    && yum update -y \
    && yum install --setopt=tsflags=nodocs -y \
      jq wget git make vim \
      inotify-tools ansible \
      python3 openssh-clients \
 && yum clean all \
 && rm -rf /var/cache/yum

# Get kubectl binary
ENV OC_RELEASE=4.5.14
RUN wget https://mirror.openshift.com/pub/openshift-v4/clients/ocp/$OC_RELEASE/openshift-client-linux-$OC_RELEASE.tar.gz \ 
	&& tar -C /usr/local/bin -xzf openshift-client-linux-$OC_RELEASE.tar.gz \
	&& rm -f openshift-client-linux-$OC_RELEASE.tar.gz

# Set up Ansible
RUN mkdir -p /etc/ansible \
    && echo "localhost ansible_connection=local" > /etc/ansible/hosts
COPY ansible.cfg /etc/ansible/ansible.cfg
RUN sed -i '19s/roles\//\/opt\/ci-artifacts\/roles/' /etc/ansible/ansible.cfg

# Set up the runner user
ENV USER_UID=1001 \
    USER_NAME=psap-ci-runner \
    HOME=/opt/ci-artifacts/src/ \
    OPTS="-v" \
    WORK_DIR=/opt/ci-artifacts/src/

COPY group_vars ${HOME}/group_vars
COPY inventory ${HOME}/inventory
COPY playbooks ${HOME}/playbooks
COPY roles ${HOME}/roles

RUN useradd -u ${USER_UID} -g 0 -d ${HOME} ${USER_NAME} 

# Ensure directory permissions are properly set
RUN mkdir -p ${HOME}/.ansible/tmp \
 && chown -R ${USER_UID}:0 ${HOME} \
 && chmod -R ug+rwx ${HOME}

RUN /usr/local/bin/user_setup

USER ${USER_UID}
WORKDIR ${HOME}
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD [ "/usr/local/bin/run" ]
