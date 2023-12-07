config_fips:
	@if [ "${USE_FIPS}" ]; then \
	  make _config_fips; \
	else \
	  echo "USE_FIPS not defined, not setting the fips cluster option."; \
	fi

_config_fips:
	@echo "Setting the fips cluster option."
	yq -yi '.fips = ${USE_FIPS}' "${CLUSTER_PATH}/install-config.yaml"
