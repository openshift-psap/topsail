# if 1, use the ODS_CATALOG_IMAGE OLM catalog.
# Otherwise, install RHODS from OCM addon.
OSD_USE_ODS_CATALOG=1

if [[ "$OSD_USE_ODS_CATALOG" == "0" ]]; then
    # deploying from the addon. Get the email address from the secret vault.
    ODS_ADDON_EMAIL_ADDRESS=$(cat "$PSAP_ODS_SECRET_PATH/addon.email")
fi

ODS_CATALOG_IMAGE="quay.io/modh/qe-catalog-source"
ODS_CATALOG_IMAGE_TAG="latest"

# if the value is different from 1, do not customize RHODS.
# see sutest_customize_rhods in `notebook_scale_test.sh`.
CUSTOMIZE_RHODS=1

# only taken into account if CUSTOMIZE_RHODS=1
# if not empty, force the given image for the rhods-dashboard container
# Mind that this requires stopping the rhods-operator.
# ODH main image: quay.io/opendatahub/odh-dashboard:main
CUSTOMIZE_RHODS_DASHBOARD_FORCED_IMAGE=

# only taken into account if CUSTOMIZE_RHODS=1
# if value is 1, remove the GPU images (to use less resources)
CUSTOMIZE_RHODS_REMOVE_GPU_IMAGES=1

# only taken into account if CUSTOMIZE_RHODS=1
# if value is not empty, use the given PVC size
CUSTOMIZE_RHODS_PVC_SIZE=5Gi

# only taken into account if CUSTOMIZE_RHODS=1
# if value is 1, define a custom notebook size named $ODS_NOTEBOOK_SIZE
# see sutest_customize_rhods_after_wait for the limits/requests values
CUSTOMIZE_RHODS_USE_CUSTOM_NOTEBOOK_SIZE=1
ODS_NOTEBOOK_SIZE=Tiny # needs to match an existing notebook size in OdhDashboardConfig.spec.notebookSizes
ODS_NOTEBOOK_CPU_SIZE=1
ODS_NOTEBOOK_MEMORY_SIZE_GI=4

# only taken into account if CUSTOMIZE_RHODS=1 and CUSTOMIZE_RHODS_DASHBOARD_FORCED_IMAGE is set
# number of replicas to set to the Dashboard deployment
CUSTOMIZE_RHODS_DASHBOARD_REPLICAS=5

LDAP_IDP_NAME=RHODS_CI_LDAP
LDAP_NB_USERS=1000
LDAP_USER_PREFIX=psapuser
