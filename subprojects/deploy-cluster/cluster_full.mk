cluster_full_entitled:
	@make all
	@make has_installer
	@make config_base_install
	@make manifest
	@make manifest_entitle
	@make install
	@make kubeconfig

cluster: cluster_full_entitled

# ---
