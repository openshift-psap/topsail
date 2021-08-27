include utils/config.mk

all:
	@echo "config_new_install|config_base_install -> manifest -> manifest_entitle -> install -> kubeconfig -> uninstall -> cleanup"
	@echo
	@echo "CLUSTER_NAME = ${CLUSTER_NAME}"
	@echo "CLUSTER_PATH = ${CLUSTER_PATH}"
	@[ -f "${CLUSTER_PATH}/install.log" ] && echo "    Installed" || echo "    Not installed"
	@[ -f "${CLUSTER_PATH}/auth/kubeconfig" ] && echo "   Has kubeconfig" || echo "    No  kubeconfig"
	@[ -f "${CLUSTER_PATH}/uninstall.log" ] && echo "    Uninstalled" || echo "    Not uninstalled"
	@echo "OCP_VERSION = ${OCP_VERSION}"
	@[ -f "${OPENSHIFT_INSTALLER}" ] && echo "    Installer found" || echo "    Installer not found"
	@echo "OPENSHIFT_INSTALLER = ${OPENSHIFT_INSTALLER}"

cluster:
	@make all
	@make has_installer
	@make config_base_install
	@make manifest
	@make manifest_entitle
	@make install
	@make kubeconfig

cluster_light:
	@make all
	@make has_installer
	@make config_base_install
	@make config_single-master
	@make manifest
	@make manifest_entitle
	@make manifest_single-master
	@make install
	@make kubeconfig

# https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/openshift-install-linux.tar.gz"
# https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp-dev-preview/pre-release/openshift-install-linux.tar.gz"
has_installer: ${OPENSHIFT_INSTALLER}
${OPENSHIFT_INSTALLER}:
	@echo "WARNING: Installer v${OCP_VERSION} not found: ${OPENSHIFT_INSTALLER}"
	@echo "Downloading it from: "
	mkdir -p $$(dirname  "${OPENSHIFT_INSTALLER}")
	wget https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OCP_VERSION}/openshift-install-linux-${OCP_VERSION}.tar.gz && set -x \
        && tar xzf openshift-install-linux-${OCP_VERSION}.tar.gz openshift-install \
	&& mv openshift-install "${OPENSHIFT_INSTALLER}" \
	&& rm openshift-install-linux-${OCP_VERSION}.tar.gz
	test -e "${OPENSHIFT_INSTALLER}"

config_new_install: has_installer
	@mkdir ${CLUSTER_PATH} -p
	@if [ -f '${INSTALL_CONFIG}' ]; then\
	  echo "ERROR: ${INSTALL_CONFIG} already exists ...";\
	  exit 1;\
	fi
	@echo "Generating ${CLUSTER_PATH}/install-config.yaml ..."
	${OPENSHIFT_INSTALLER} create install-config --dir=${CLUSTER_PATH} --log-level=debug

config_base_install:
	@mkdir ${CLUSTER_PATH} -p
	@if [ ! -f ${CLUSTER_PATH}/install-config.yaml ]; then \
	  if [ ! -f ${BASE_INSTALL_CONFIG} ]; then \
	    echo "ERROR: Base install config file not found in ${BASE_INSTALL_CONFIG}."; \
	    echo "1. Generate one with 'make config_new_install'"; \
	    echo "2. Give 'cluster-name' as cluster name"; \
	    echo "3. Customize it with your pull secret & ssh key"; \
	    echo "4. Move it to '${BASE_INSTALL_CONFIG}'"; \
	    exit 1; \
	  fi; \
	  cp ${BASE_INSTALL_CONFIG} ${CLUSTER_PATH}/install-config.yaml; \
	  sed -i "s/cluster-name/${CLUSTER_NAME} # OCP_VERSION ${OCP_VERSION}/" ${CLUSTER_PATH}/install-config.yaml; \
	fi; \
	if [ ! -f ${BASE_INSTALL_CONFIG} ]; then \
		echo "You must copy ${CLUSTER_PATH}/install-config.yaml to ${BASE_INSTALL_CONFIG}"; \
		exit 1; \
	fi; \
	${DIFF_TOOL} ${BASE_INSTALL_CONFIG} ${CLUSTER_PATH}/install-config.yaml

config_single-master:
	CONFIG_CONTENT=$$(cat ${CLUSTER_PATH}/install-config.yaml); \
	yq -y '.controlPlane.replicas=1' ${CLUSTER_PATH}/install-config.yaml > ${CLUSTER_PATH}/install-config.yaml.new
	diff -b ${CLUSTER_PATH}/install-config.yaml{,.new} || true
	mv ${CLUSTER_PATH}/install-config.yaml{.new,}

manifest: has_installer
	@[[ -f ${CLUSTER_PATH}/install-config.yaml ]] && cp ${CLUSTER_PATH}/install-config{,.back}.yaml || echo
	${OPENSHIFT_INSTALLER} create manifests --dir=${CLUSTER_PATH} > /dev/null;

manifest_entitle:
	@echo "PEM:	 ${ENTITLEMENT_PEM}"
	@echo "RHSM:	 ${ENTITLEMENT_RHSM}"
	@echo "Template: ${ENTITLEMENT_TEMPLATE}"
	@echo "Dest:	 ${ENTITLEMENT_DST_BASENAME}*"
	@cat ${ENTITLEMENT_TEMPLATE} \
	  | sed "s/BASE64_ENCODED_PEM_FILE/$(shell base64 -w 0 ${ENTITLEMENT_PEM})/g" \
	  | sed "s/BASE64_ENCODED_RHSM_FILE/$(shell base64 -w 0 ${ENTITLEMENT_RHSM})/g" \
	  > ${ENTITLEMENT_DST_BASENAME}.yaml
	@awk '{ print > "${ENTITLEMENT_DST_BASENAME}_"++i".yaml" }' RS='---\n' ${ENTITLEMENT_DST_BASENAME}.yaml
	@rm ${ENTITLEMENT_DST_BASENAME}.yaml
	@echo "Entitlement MachineConfig generated:"
	@ls ${ENTITLEMENT_DST_BASENAME}_*

manifest_single-master:
	cp -v ${SINGLE_MASTER_MANIFESTS} ${SINGLE_MASTER_DST}
	cat ${SINGLE_MASTER_CVO_OVERRIDE} >> ${CLUSTER_PATH}/manifests/cvo-overrides.yaml

install_single-master_fix-authentication:
	env KUBECONFIG=${CLUSTER_PATH}/auth/kubeconfig \
	oc apply -f ${SINGLE_MASTER_DIR}/single-authentication.yaml

install: has_installer
	@[[ -f ${CLUSTER_PATH}/install-config.yaml ]] && cp ${CLUSTER_PATH}/install-config{,.back}.yaml || echo
	@if [ -e ${CLUSTER_PATH}/install.log ]; then \
	  echo "INFO: Found ${CLUSTER_PATH}/install.log" \
	  echo "ERROR: Cluster already installed ..."; \
	  exit 1; \
	fi;
	time ${OPENSHIFT_INSTALLER} create cluster --dir=${CLUSTER_PATH} --log-level=debug 2>&1 | tee ${CLUSTER_PATH}/install.log

kubeconfig:
	@if [ ! -e ${CLUSTER_PATH}/auth/kubeconfig ]; then \
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
	@if [ -e ${CLUSTER_PATH}/uninstall.log ]; then \
	  echo "INFO: Found ${CLUSTER_PATH}/uninstall.log"; \
	  echo "ERROR: Cluster already uninstalled ..."; \
	  exit 1; \
	fi;
	time ${OPENSHIFT_INSTALLER} destroy cluster --dir=${CLUSTER_PATH} --log-level=debug 2>&1 | tee ${CLUSTER_PATH}/uninstall.log

cleanup:
	@if [ ! -e ${CLUSTER_PATH}/uninstall.log ]; then \
	  echo "INFO: Could not find ${CLUSTER_PATH}/uninstall.log"; \
	  echo "ERROR: Cluster not uninstalled ..."; \
	  exit 1; \
	fi;
	rm -rf ${CLUSTER_PATH}
