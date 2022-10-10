if [[ "${ARTIFACT_DIR:-}" ]] && [[ -f "${ARTIFACT_DIR}/variable_overrides" ]]; then
    source "${ARTIFACT_DIR}/variable_overrides"
fi
