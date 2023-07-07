cluster_single-master_entitled:
	@make all
	@make has_installer
	@make config_base_install
	@make config_single-master
	@make config_tags
	@make config_fips
	@make diff
	@make manifest
	@make manifest_entitle
	@make manifest_single-master
	@make manifest_spot
	@make install
	@make kubeconfig

cluster_light: cluster_single-master_entitled

# ---

config_single-master:
	yq -yi '.controlPlane.replicas=1' "${CLUSTER_PATH}/install-config.yaml"

manifest_single-master:
	cp -v ${SINGLE_MASTER_MANIFESTS} "${SINGLE_MASTER_DST}"
	cat "${SINGLE_MASTER_CVO_OVERRIDE}" >> "${CLUSTER_PATH}/manifests/cvo-overrides.yaml"

install_single-master_fix-authentication:
	env KUBECONFIG="${CLUSTER_PATH}/auth/kubeconfig" \
	oc apply -f "${SINGLE_MASTER_DIR}/single-authentication.yaml"
