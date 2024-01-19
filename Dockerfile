FROM registry.access.redhat.com/ubi9/ubi
MAINTAINER OpenShift PSAP Team <openshift-psap@redhat.com>
LABEL 	io.k8s.display-name="OpenShift PSAP CI artifacts" \
      	io.k8s.description="An image for running Ansible artifacts for OpenShift PSAP CI" \
 	name="topsail" \
	url="https://github.com/openshift-psap/topsail"

## Install packages dependencies
RUN yum install -y --quiet \
	  git jq vim wget rsync time gettext httpd-tools make file psmisc \
		python3.9 python3-pip python3-setuptools procps go-toolset

## Install CLI dependencies: ocm, oc
ARG CURL_OPTIONS="--silent --location --fail --show-error"
ARG OCP_CLI_VERSION=latest
ARG OCP_CLI_URL=https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/${OCP_CLI_VERSION}/openshift-client-linux.tar.gz
RUN curl ${CURL_OPTIONS}  ${OCP_CLI_URL}  | tar xfz - -C /usr/local/bin oc
RUN ln -s $(which oc) /usr/bin/kubectl
## Just in case we use old shebangs
RUN ln -s /usr/bin/python3 /usr/bin/python

## Install Prometheus
ARG PROMETHEUS_VERSION=2.36.0
RUN wget --quiet "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz" -O/tmp/prometheus.tar.gz \
  && tar xf "/tmp/prometheus.tar.gz" -C /tmp \
  && mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus /usr/local/bin \
  && mkdir -p /etc/prometheus/ \
  && mv /tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus.yml /etc/prometheus/prometheus.yml

## Matbench in the path
## This symbolic link wont work until the
## topsail user exists and we copy the whole
## project into topsail's home
RUN echo -e '#!/usr/bin/env bash \n\
exec /home/topsail/topsail/testing/run "$@" \n\
' > /usr/local/bin/run; chmod ugo+x /usr/local/bin/run \
 \
 && ln -s /home/topsail/topsail/subprojects/matrix-benchmarking/bin/matbench /usr/local/bin/

## Setting up the container user details
ARG USER=topsail
ARG UID=1001
ARG HOME=/home/$USER
RUN set -x && \
    \
    echo "==> Creating local user account..."  && \
    useradd --create-home --uid $UID --gid 0 $USER && \
    ln -s $HOME/topsail/ /topsail
ENV PYTHONPATH "${PYTHONPATH}:$HOME/topsail/"
WORKDIR $HOME/topsail
RUN chown -R ${USER}:0 $HOME
USER $USER
ENV PATH $HOME/.local/bin:$PATH
COPY --chown=${USER}:0 . .

## Get the submodules dependencies
RUN cd subprojects && git submodule update --init --recursive

## Install the project's Python dependencies
RUN set -x && \
    \
    echo "==> Adding ansible and dependencies..." && \
    python3 -m pip install --user --upgrade pip && \
    python3 -m pip install --user --upgrade wheel && \
    python3 -m pip install --quiet --no-cache-dir -r ./requirements.txt

## Disable git dubious ownership detection in the image
RUN git config --global --add safe.directory '*'