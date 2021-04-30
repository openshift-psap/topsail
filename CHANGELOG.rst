**What has changed in ci-artifacts?**

(Organized release by release)

Changes since version May 7th, 2021
-----------------------------------

Toolbox
~~~~~~~

Retro-compatibility breaks
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Change scaleup to set_scale - supported scale other than just 1 node `#139 <https://github.com/openshift-psap/ci-artifacts/pull/139>`_

  - ``toolbox/cluster/scaleup.sh`` has been removed,
  - ``toolbox/cluster/set_scale.sh`` has been `introduced <https://openshift-psap.github.io/ci-artifacts/toolbox/cluster.html#cluster-scale>`_ as a replacement.

Other changes
^^^^^^^^^^^^^

- Change scaleup to set_scale - supported scale other than just 1 node `#139 <https://github.com/openshift-psap/ci-artifacts/pull/139>`_

  - ``toolbox/cluster/set_scale.sh`` has been `introduced
    <https://openshift-psap.github.io/ci-artifacts/toolbox/cluster.html#cluster-scale>`_
    to control the scale (node count, of a given AWS instance-type) of
    a cluster


CI Image and Testing
~~~~~~~~~~~~~~~~~~~~

-


Bug fixes
~~~~~~~~~

-
