FROM quay.io/centos/centos:stream9

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP topsail" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="topsail" \
	url="https://github.com/openshift-psap/"

RUN dnf install -y epel-release && \
    dnf install --quiet -y \
         git jq vim wget rsync time gettext httpd-tools make file psmisc \
         python3-pip python3-setuptools procps gcc g++ \
         python3 python3-devel \
         python-kubernetes python3-numpy python3-pyyaml \
  && dnf clean all \
  && pip install virtualenv \
  && rm -rf $HOME/.cache && rm -rf /var/cache/yum \
  && pip install --upgrade pip

# Install dependencies: ocm, oc

ARG CURL_OPTIONS="--silent --location --fail --show-error"
ARG OCP_CLI_VERSION=latest

# Detect architecture and set appropriate OCP client URL
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/aarch64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz; \
    else \
        OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz; \
    fi && \
    curl ${CURL_OPTIONS} ${OCP_CLI_URL} | tar xfz - -C /usr/local/bin oc

# Install Prometheus with architecture detection
ARG PROMETHEUS_VERSION=2.36.0
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        PROMETHEUS_ARCH="arm64"; \
    else \
        PROMETHEUS_ARCH="amd64"; \
    fi && \
    wget --quiet "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-${PROMETHEUS_ARCH}.tar.gz" -O/tmp/prometheus.tar.gz && \
    tar xf "/tmp/prometheus.tar.gz" -C /tmp && \
    mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-${PROMETHEUS_ARCH}/prometheus /usr/local/bin && \
    mkdir -p /etc/prometheus/ && \
    mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-${PROMETHEUS_ARCH}/prometheus.yml /etc/prometheus/prometheus.yml

# Set up the runner user
ENV USER_NAME=psap-ci-runner \
    USER=psap-ci-runner \
    HOME=/opt/topsail/src \
    INSIDE_CI_IMAGE="y"

ENV PYTHONPATH=$HOME

COPY . ${HOME}/

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
 \
 && ln -s /usr/bin/python3 /usr/bin/python

RUN ln -s $(which oc) /usr/bin/kubectl

# Install Python requirements

RUN pip install --no-cache-dir -r ${HOME}/requirements.txt && \
    (cd ${HOME} && ./projects/matrix_benchmarking/library/visualize.py prepare_matbench)

# Disable git dubious ownership detection in the image
RUN git config --global --add safe.directory '*'

WORKDIR ${HOME}

ENTRYPOINT ["bash"]
CMD ["run"]
