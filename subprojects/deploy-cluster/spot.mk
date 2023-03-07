SPOT_WORKER_MACHINESET_FILES := ${CLUSTER_PATH}/openshift/99_openshift-cluster-api_worker-machineset-*.yaml

manifest_spot:
	@if [ "${USE_SPOT}" ]; then \
	  make _manifest_spot; \
	else \
	  echo "USE_SPOT not defined, not setting the spot instance option."; \
	fi

_manifest_spot:
	@echo "Setting the spot instance option."
	yq -yi '.spec.template.spec.providerSpec.value.spotMarketOptions = {}' $(wildcard ${SPOT_WORKER_MACHINESET_FILES})
