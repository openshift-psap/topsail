Ansible configuration
=====================

This directory contains TOPSAIL's Ansible configuration files.

This directory should almost never be updated.

TOPSAIL uses Ansible in a lightweight way. It always runs with a
single machine in the inventory file, the `localhost`.

TOPSAIL provides its own ``stdout`` callback, `human_log.py
<ansible-config/callback_plugins/human_log.py>`_, which aims at
simplifying at its maximum the readability of the Ansible log file.

This aspect is critical for TOPSAIL, as post-mortem troubleshooting is
often a difficult task. The Ansible and the ``human_log`` callback helps by
making it clear what command has been executed, if it failed or not,
what was the stdout/stderr content, etc.

The other critical aspect of TOPSAIL Ansible roles is the creation of
a dedicated directory, reachable with ``{{ artifact_extra_logs_dir
}}``, which isolates the artifacts generated during the execution of
an Ansible role.
