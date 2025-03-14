FROM quay.io/centos/centos:stream9

MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>

LABEL 	io.k8s.display-name="OpenShift PSAP topsail" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="topsail" \
	url="https://github.com/openshift-psap/"

ARG PYTHON_VERSION=3.11
RUN dnf install -y epel-release && \
    dnf install --quiet -y \
         git jq vim wget rsync time gettext httpd-tools make file psmisc \
         python${PYTHON_VERSION}-pip python${PYTHON_VERSION}-setuptools procps gcc g++ \
         python${PYTHON_VERSION} python${PYTHON_VERSION}-devel \
         python-kubernetes python${PYTHON_VERSION}-numpy python3-pyyaml \
    && dnf clean all \
    && alternatives --install /usr/bin/python python3 /usr/bin/python${PYTHON_VERSION} 1 \
    && ln -sf /usr/bin/python${PYTHON_VERSION} /usr/bin/python3 \
    && rm -rf $HOME/.cache && rm -rf /var/cache/yum

# Install dependencies: ocm, oc

ARG CURL_OPTIONS="--silent --location --fail --show-error"
ARG OCP_CLI_VERSION=latest

# Detect architecture and set appropriate OCP client URL
RUN ARCH=$(uname -m) && \
    OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/${ARCH}/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz && \
    curl ${CURL_OPTIONS} ${OCP_CLI_URL} | tar xfz - -C /usr/local/bin oc

# Install Prometheus with architecture detection
ARG PROMETHEUS_VERSION=2.36.0
RUN ARCH=$(uname -m | sed 's/aarch64/arm64/; s/x86_64/amd64/') && \
    PROMETHEUS_URL=https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-${ARCH}.tar.gz && \
    wget --quiet "${PROMETHEUS_URL}" -O/tmp/prometheus.tar.gz && \
    tar xf "/tmp/prometheus.tar.gz" -C /tmp && \
    mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-${ARCH}/prometheus /usr/local/bin && \
    mkdir -p /etc/prometheus/ && \
    mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-${ARCH}/prometheus.yml /etc/prometheus/prometheus.yml

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
 && ln -s $(which oc) /usr/bin/kubectl && ln -s pip${PYTHON_VERSION} /usr/bin/pip

# Install Python requirements

RUN pip install --no-cache-dir -r ${HOME}/requirements.txt && \
    (cd ${HOME} && ./projects/matrix_benchmarking/library/visualize.py prepare_matbench)

# Disable git dubious ownership detection in the image
RUN git config --global --add safe.directory '*'

WORKDIR ${HOME}

ENTRYPOINT ["bash"]
CMD ["run"]
