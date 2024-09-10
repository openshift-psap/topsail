TOPSAIL should be executed within its container image, define in this Containerfile.

The TOPSAIL CI engines ([OpenShift CI](https://github.com/openshift/release/blob/master/ci-operator/config/openshift-psap/topsail/openshift-psap-topsail-main__rhoai.yaml) and Jenkins) use this file to build their image.

TOPSAIL users should use [TOPSAIL/Launcher](../launcher#readme)'s `topsail_build` command to build TOPSAIL image.
