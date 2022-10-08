if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
    echo "ERROR: the PSAP_ODS_SECRET_PATH was not provided"
    false # can't exit here
elif [[ ! -d "$PSAP_ODS_SECRET_PATH" ]]; then
    echo "ERROR: the PSAP_ODS_SECRET_PATH does not point to a valid directory"
    false # can't exit here
fi

S3_LDAP_PROPS="${PSAP_ODS_SECRET_PATH}/s3_ldap.passwords"
