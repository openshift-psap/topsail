manifest_tags:
	@if [ "${MACHINE_TAGS}" ]; then \
	  make _manifest_tags; \
	else \
	  echo "MACHINE_TAGS not defined, not setting custom machineset tags."; \
	fi

_manifest_tags:
	@echo "Setting the machineset tags."
	yq -yi '.spec.template.spec.providerSpec.value.tags = [${MACHINE_TAGS}]' $(wildcard ${MASTER_MACHINESET_FILES}) $(wildcard ${WORKER_MACHINESET_FILES})
