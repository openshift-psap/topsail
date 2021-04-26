#! /bin/bash

echo "# md5sum of entitlement file (debug)"
if md5sum /etc/rhsm/rhsm.conf /etc/pki/entitlement/entitlement{,-key}.pem; then
    echo "# INFO: entitlement files found"
else
    echo "#"
    echo "# WARNING: entitlement files missing"
    echo "#"
fi

echo
echo "# ensure that RH repositories can be accessed"

exec dnf list kernel-core --showduplicates
