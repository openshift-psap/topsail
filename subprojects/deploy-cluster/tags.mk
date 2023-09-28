config_tags:
ifneq ($(MACHINE_TAGS),)
	make _config_tags;
else
	echo "MACHINE_TAGS not defined, not setting custom machine tags."
endif

_config_tags:
	@echo "Setting the AWS user tags."
	yq -yi '.platform.aws.userTags = ${MACHINE_TAGS}' "${CLUSTER_PATH}/install-config.yaml"
