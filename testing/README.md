TOPSAIL's ``testing`` directory
===============================

**This directory is mostly outdated**.

The files living in this directory have been moved to
``projects/*/testing``.

`run`
-----

This file is the main CI entrypoint. It should be re-written in Python
...

The `run` command performs some basic sanity checks before and after
running the test, and calls the project entrypoints. It operates by
rewriting its arguments:

```
run $PROJECT $FILE $ARGS*
# executes
projects/$PROJECT/testing/$FILE{.py|.sh} $ARGS*
```

The CI engines should call these commands:
```
run $PROJECT clusters create # if needed
run $PROJECT test prepare_ci
run $PROJECT test test_ci
run $PROJECT clusters destroy # if needed
```

See TOPSAIL's OpenShift CI configuration at [this
address](https://github.com/openshift/release/blob/master/ci-operator/config/openshift-psap/topsail/openshift-psap-topsail-main__rhoai.yaml).

* `clusters create` and `clusters destroy` are old (but working) Bash
  code. They create and destroy AWS clusters.

* `test prepare_ci` and `test test_ci` are the main test
  entrypoints. As their name suggest, they should prepare the cluster
  for running tests, and run the test itself (including any
  post-processing step).

`rhoai.py`
----------

This file is a helper on top of the `run` command. OpenShift CI does
not allow any dynamic configuration, so TOPSAIL had to built its down.
When this line is commented in the Github repository:
```
/test rhoai-light $PROJECT $FILE $ARGS*
```
the `rhoai.py` file will be launched, and it will call in turn:
```
run $PROJECT $FILE $ARGS
```

This saves us from defining one test per project (as it happened
before this file was written), and instead have a unique entrypoint
that dispatches to the right project.
