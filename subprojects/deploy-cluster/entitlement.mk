manifest_entitle:
	@echo "PEM:	 ${ENTITLEMENT_PEM}"
	@echo "RHSM:	 ${ENTITLEMENT_RHSM}"
	@echo "Template: ${ENTITLEMENT_TEMPLATE}"
	@echo "Dest:	 ${ENTITLEMENT_DST_BASENAME}*"
	@cat "${ENTITLEMENT_TEMPLATE}" \
	  | sed "s/BASE64_ENCODED_PEM_FILE/$(shell base64 -w 0 ${ENTITLEMENT_PEM})/g" \
	  | sed "s/BASE64_ENCODED_RHSM_FILE/$(shell base64 -w 0 ${ENTITLEMENT_RHSM})/g" \
	  > "${ENTITLEMENT_DST_BASENAME}.yaml"
	@awk '{ print > "${ENTITLEMENT_DST_BASENAME}_"++i".yaml" }' RS='---\n' "${ENTITLEMENT_DST_BASENAME}.yaml"
	@rm "${ENTITLEMENT_DST_BASENAME}.yaml"
	@echo "Entitlement MachineConfig generated:"
	@ls "${ENTITLEMENT_DST_BASENAME}"_*
