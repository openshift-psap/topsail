TOPSAIL development environment builder
=======

This simple repository provides scripts to assist in building a
development environment for TOPSAIL, based on Toolbx and Podman
images.

Install the few requirement dependencies, configure the few mandatory
paths, then `topsail_build` will build your container image, and
`topsail_enter` will launch a working TOPSAIL container environment
with direct access to your TOPSAIL repository (in your host system).

Requirements
------------

* You need to have the [Toolbx package](https://docs.fedoraproject.org/en-US/fedora-silverblue/toolbox/) installed:
```
sudo dnf install toolbox
```

* You need to have TOPSAIL cloned locally
```
git clone https://github.com/openshift-psap/topsail.git
```

Configuration
-------------

* Prepare and edit `topsail_host_config`
```
cp topsail_host_config{.sample,}
```

* Prepare and edit `topsail_container_env`
```
cp topsail_host_config{.sample,}
```

Usage
-----

* Build TOPSAIL image
```
./topsail_build
```

* Enter TOPSAIL toolbox and go to TOPSAIL directory
```
./topsail_enter
```

* Enter TOPSAIL toolbox and stay in the current directory
```
./topsail_enter_here
```

* Enter TOPSAIL toolbox and run a TOPSAIL toolbox command
```
./topsail_run_cmd
```

* Enter TOPSAIL toolbox and run a TOPSAIL `run` command
```
./topsail_run
```
