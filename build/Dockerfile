FROM centos:7 
MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

USER root

RUN yum -y update \
 && yum -y install epel-release centos-release-openshift-origin \
 && yum -y install origin-clients \
 && yum clean all

RUN yum install -y \
      ansible \
      ansible-runner \
      ansible-runner-http \
      python-kubernetes \
      python-openshift \
      python-jmespath \
      tini \
      jq \
      inotify-tools \
      python-requests-2.6.0-7.el7_7 \
 && yum clean all \
 && rm -rf /var/cache/yum

# Set up Ansible
RUN mkdir -p /etc/ansible \
    && echo "localhost ansible_connection=local" > /etc/ansible/hosts
COPY ansible.cfg /etc/ansible/ansible.cfg
RUN sed -i '19s/roles\//\/opt\/ci-artifacts\/roles/' /etc/ansible/ansible.cfg

COPY build/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set up the runner user
ENV USER_UID=1001 \
    USER_NAME=psap-ci-runner\
    HOME=/opt/ci-artifacts

COPY group_vars ${HOME}/group_vars
COPY inventory ${HOME}/inventory
COPY playbooks ${HOME}/playbooks
COPY roles ${HOME}/roles

RUN useradd -u ${USER_UID} -g 0 -d ${HOME} ${USER_NAME} 

# Ensure directory permissions are properly set
RUN mkdir -p ${HOME}/.ansible/tmp \
 && chown -R ${USER_UID}:0 ${HOME} \
 && chmod -R ug+rwx ${HOME}

USER ${USER_UID}
ENTRYPOINT ["entrypoint.sh"]
LABEL 	io.k8s.display-name="OpenShift PSAP Ci artifacts" \
      	io.k8s.description="This are artifacts to run PSAP Ci" \
 	name="ci-artifacts" \
	url="https://github.com/openshift-psap/ci-artifacts"
