cluster_full:
	@make all
	@make has_installer
	@make config_base_install
	@make config_tags
	@make config_fips
	@make diff
	@make manifest
	@make manifest_spot
	@make install
	@make kubeconfig

cluster: cluster_full

# ---
