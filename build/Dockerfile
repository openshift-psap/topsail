FROM registry.access.redhat.com/ubi9/ubi

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP topsail" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="topsail" \
	url="https://github.com/openshift-psap/"

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN yum install -y --quiet \
	        git jq vim wget rsync time gettext httpd-tools make file psmisc \
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

# Install Prometheus
ARG PROMETHEUS_VERSION=2.36.0
RUN wget --quiet "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz" -O/tmp/prometheus.tar.gz \
  && tar xf "/tmp/prometheus.tar.gz" -C /tmp \
  && mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus /usr/local/bin \
  && mkdir -p /etc/prometheus/ \
  && mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus.yml /etc/prometheus/prometheus.yml

# Set up the runner user
ENV USER_NAME=psap-ci-runner \
    USER=psap-ci-runner \
    HOME=/opt/topsail/src \
    INSIDE_CI_IMAGE="y"

ENV PYTHONPATH=$HOME

COPY . ${HOME}/

# Install Python requirements

RUN pip install --quiet --no-cache-dir -r ${HOME}/requirements.txt && \
    (cd ${HOME} && ./projects/matrix_benchmarking/library/visualize.py prepare_matbench)

# Ensure directory permissions are properly set

# This should run after all the `pip` commands.  It is necessary so
# that we can `pip install` from inside the image.

RUN echo -e '#!/usr/bin/env bash \n\
exec ${HOME}/testing/run "$@" \n\
' > /usr/local/bin/run; chmod ugo+x /usr/local/bin/run \
 \
 && ln -s ${HOME}/projects/matrix_benchmarking/subproject/bin/matbench /usr/local/bin/ \
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
