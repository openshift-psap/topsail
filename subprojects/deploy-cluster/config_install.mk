# https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-install-linux.tar.gz"
# https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp-dev-preview/pre-release/openshift-install-linux.tar.gz"

SHELL=/usr/bin/env bash -o pipefail

has_installer: ${OPENSHIFT_INSTALLER}
${OPENSHIFT_INSTALLER}:
	@echo "WARNING: Installer v${OCP_VERSION} not found: ${OPENSHIFT_INSTALLER}"
	@echo "Downloading it from: "
	mkdir -p $$(dirname  "${OPENSHIFT_INSTALLER}")
	wget --quiet "${OPENSHIFT_INSTALLER_URL}" && set -x \
	&& tar xzf openshift-install-linux-${OCP_VERSION}.tar.gz openshift-install \
	&& mv openshift-install "${OPENSHIFT_INSTALLER}" \
	&& rm openshift-install-linux-${OCP_VERSION}.tar.gz
	test -e "${OPENSHIFT_INSTALLER}"

manifest: has_installer

	[ -f "${CLUSTER_PATH}/install-config.yaml.back" ] && cp "${CLUSTER_PATH}"/install-config{.back,}.yaml || echo
	[ -f "${CLUSTER_PATH}/install-config.yaml" ] && cp "${CLUSTER_PATH}"/install-config{,.back}.yaml || echo
	mkdir -p "${CLUSTER_PATH}"

	"${OPENSHIFT_INSTALLER}" create manifests --dir="${CLUSTER_PATH}" --log-level=debug 2> "${CLUSTER_PATH}/create_manifests.log";


install: has_installer
	@[ -f "${CLUSTER_PATH}/install-config.yaml" ] && cp "${CLUSTER_PATH}"/install-config{,.back}.yaml || echo
	@if [ -e "${CLUSTER_PATH}/install.log" ]; then \
	  echo "INFO: Found ${CLUSTER_PATH}/install.log" \
	  echo "ERROR: Cluster already installed ..."; \
	  exit 1; \
	fi

	"${OPENSHIFT_INSTALLER}" create ignition-configs --dir="${CLUSTER_PATH}" --log-level=debug 2> "${CLUSTER_PATH}/create_ignition_configs.log";
	[[ "${METADATA_JSON_DEST}" ]] && cp "${CLUSTER_PATH}/metadata.json" "${METADATA_JSON_DEST}"

	time "${OPENSHIFT_INSTALLER}" create cluster --dir="${CLUSTER_PATH}" --log-level=debug 2>&1 \
		| grep --line-buffered -v 'password\|X-Auth-Token\|UserData:' \
		| tee "${CLUSTER_PATH}/install.log"

config_new_install: has_installer
	@mkdir "${CLUSTER_PATH}" -p
	@if [ -f "${INSTALL_CONFIG}" ]; then\
	  echo "ERROR: ${INSTALL_CONFIG} already exists ...";\
	  exit 1;\
	fi
	@echo "Generating ${CLUSTER_PATH}/install-config.yaml ..."
	"${OPENSHIFT_INSTALLER}" create install-config --dir="${CLUSTER_PATH}" --log-level=debug

config_base_install:
	@mkdir -p "${CLUSTER_PATH}"
	@if [ ! -f "${CLUSTER_PATH}/install-config.yaml" ]; then \
	  if [ ! -f "${BASE_INSTALL_CONFIG}" ]; then \
	    echo "ERROR: Base install config file not found in ${BASE_INSTALL_CONFIG}."; \
	    echo "1. Generate one with 'make config_new_install'"; \
	    echo "2. Give 'cluster-name' as cluster name"; \
	    echo "3. Customize it with your pull secret & ssh key"; \
	    echo "4. Move it to '${BASE_INSTALL_CONFIG}'"; \
	    exit 1; \
	  fi; \
	  cp "${BASE_INSTALL_CONFIG}" "${CLUSTER_PATH}/install-config.yaml"; \
	  sed -i "s/cluster-name/${CLUSTER_NAME} # OCP_VERSION ${OCP_VERSION}/" "${CLUSTER_PATH}/install-config.yaml"; \
	fi
	@if [ ! -f "${BASE_INSTALL_CONFIG}" ]; then \
		echo "You must copy ${CLUSTER_PATH}/install-config.yaml to ${BASE_INSTALL_CONFIG}"; \
		exit 1; \
	fi

diff:
	@if [ "${DIFF_TOOL}" ]; then \
           "${DIFF_TOOL}" "${BASE_INSTALL_CONFIG}" "${CLUSTER_PATH}/install-config.yaml"; \
	fi

kubeconfig:
	@if [ ! -e "${CLUSTER_PATH}/auth/kubeconfig" ]; then \
	  echo "Kubeconfig for ${CLUSTER_NAME} not found in ${CLUSTER_PATH}/auth/kubeconfig"; \
	  exit 1;\
	fi

	@echo "Command:"
	@echo "export KUBECONFIG=${CLUSTER_PATH}/auth/kubeconfig"
	@echo "project ${CLUSTER_NAME}"

uninstall: has_installer
	@if [ ! -d "${CLUSTER_PATH}/" ]; then \
	  echo "ERROR: Cluster not found"; \
	  exit 1; \
	fi
	@if [ -e "${CLUSTER_PATH}/uninstall.log" ]; then \
	  echo "INFO: Found ${CLUSTER_PATH}/uninstall.log"; \
	  echo "ERROR: Cluster already uninstalled ..."; \
	  exit 1; \
	fi
	time "${OPENSHIFT_INSTALLER}" destroy cluster --dir="${CLUSTER_PATH}" --log-level=debug 2>&1 | tee "${CLUSTER_PATH}/uninstall.log"

cleanup:
	@if [ ! -e "${CLUSTER_PATH}/uninstall.log" ]; then \
	  echo "INFO: Could not find ${CLUSTER_PATH}/uninstall.log"; \
	  echo "ERROR: Cluster not uninstalled ..."; \
	  exit 1; \
	fi
	@if [ -e "${CLUSTER_PATH}/metadata.json" ]; then \
	  echo "INFO: ${CLUSTER_PATH}/metadata.json still exists"; \
	  echo "ERROR: Cluster not fully destroyed by openshift-installer ..."; \
	  exit 1; \
	fi
	rm -rf "${CLUSTER_PATH}"
