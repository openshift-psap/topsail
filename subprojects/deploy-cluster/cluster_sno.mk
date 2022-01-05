cluster_sno:
	@make all
	@make has_installer
	@make config_base_install
	@make config_sno
	@make manifest
	@make install
	@make kubeconfig

sno: cluster_sno

# ---

config_sno:
	yq --yml-output -i '.controlPlane.replicas=1' "${CLUSTER_PATH}/install-config.yaml"
	yq --yml-output -i 'del(.compute[0].platform)'  "${CLUSTER_PATH}/install-config.yaml"
	yq --yml-output -i '.compute[0].replicas=0'  "${CLUSTER_PATH}/install-config.yaml"
