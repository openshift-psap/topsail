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
	@echo "OpenShift Installer URL: ${OPENSHIFT_INSTALLER_URL}"
	@echo "DIFF_TOOL = ${DIFF_TOOL}"

# ---

include config_install.mk

include cluster_full.mk
include cluster_single-master.mk
include cluster_sno.mk

include entitlement.mk
include spot.mk
include tags.mk
include fips.mk
