if [[ -z "${PSAP_ODS_SECRET_PATH:-}" ]]; then
    echo "WARNING: the PSAP_ODS_SECRET_PATH was not provided"
elif [[ ! -d "$PSAP_ODS_SECRET_PATH" ]]; then
    echo "WARNING: the PSAP_ODS_SECRET_PATH does not point to a valid directory"
fi
PSAP_ODS_SECRET_PATH=${PSAP_ODS_SECRET_PATH:-UNDEFINED}

S3_LDAP_PROPS="$PSAP_ODS_SECRET_PATH/s3_ldap.passwords"
