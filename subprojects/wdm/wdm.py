#! /usr/bin/python3

import yaml
import sys, os
import subprocess
import tempfile

deps = {}
resolved = set()

tested = dict()
installed = dict()

WDM_DEPENDENCY_FILE = None
wdm_mode = None

def run_ansible(task, depth):
    tmp = tempfile.NamedTemporaryFile("w+", dir=os.getcwd(), delete=False)

    play = [
        dict(name=f"Run { task['name']}",
             connection="local",
             gather_facts=False,
             hosts="localhost",
             tasks=task["spec"],
             )
    ]

    yaml.dump(play, tmp)
    tmp.close()

    print("-"*(depth+2))
    env = os.environ.copy()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    env["ANSIBLE_CONFIG"] = dir_path + "/../../config/ansible.cfg"

    try:
        proc = subprocess.run(["ansible-playbook", tmp.name],
                              env=env, stdin=None)

        ret = proc.returncode
    finally:
        os.remove(tmp.name)

    print("-"*(depth+2))

    return ret == 0

    pass

def run_shell(task, depth):
    cmd = task["spec"]
    print(" "*depth, f"|>SHELL<| \n{cmd.strip()}")

    print("-"*(depth+2))
    proc = subprocess.run(["/bin/bash", "-ceuo", "pipefail", cmd], stdin=subprocess.PIPE)
    ret = proc.returncode
    print("-"*(depth+2))

    return ret == 0

def run(task, depth):
    print(" "*depth, f"|Running '{task['name']}' ...")
    type_ = task["type"]
    if type_ == "shell":
        success = run_shell(task, depth)
    elif type_ == "ansible":
        success = run_ansible(task, depth)
    else:
        print(f"ERROR: unknown task type: {type_}.")
        sys.exit(1)

    print(" "*depth, f"|Running '{task['name']}':", "Success" if success else "Failure")
    print(" "*depth, f"|___")
    return success


def do_test(dep, depth, print_first_test=True):
    if not dep["spec"].get("tests"):
        if print_first_test:
            print(f"Nothing to test for '{dep['name']}'")
        return True

    for task in dep["spec"].get("tests", []):
        if print_first_test:
            print(" "*depth, f"Testing '{dep['name']}' ...")
            print_first_test = False


        success = run(task, depth) if wdm_mode != "dryrun" else None

        tested[f"{dep['name']} -> {task['name']}"] = success
        if success:
            return True

    return False


def resolve(dep, depth=0):
    print(" "*depth, f"Treating '{dep['name']}' dependency ...")

    if dep['name'] in resolved:
        print(" "*depth, f"Dependency '{dep['name']}' has already need resolved, skipping.")
        return

    for req in dep["spec"].get("requirements", []):
        print(" "*depth, f"Dependency '{dep['name']}' needs '{req}' ...")
        try:
            next_dep = deps[req]
        except KeyError as e:
            print(f"ERROR: missing dependency: {req}")
            sys.exit(1)
        resolve(next_dep, depth=depth+1)

        print(" "*depth, f"Nothing to test for '{dep['name']}'.")

    if do_test(dep, depth) == True:
        if dep["spec"].get("tests"):
            print(" "*depth, f"Dependency '{dep['name']}' is satisfied, no need to install.")
        else:
            print(" "*depth, f"Nothing to test for '{dep['name']}'.")

    elif wdm_mode in ("dryrun", "test"):
        print(" "*depth, f"Running in test mode, skipping '{dep['name']}' installation.")
        for task in dep["spec"].get("install", []):
            installed[f"{dep['name']} -> {task['name']}"] = True
    else:
        first_install = True
        for task in dep["spec"].get("install", []):
            if first_install:
                first_install = False
                print(" "*depth, f"Installing '{dep['name']}' ...")

            if not run(task, depth):
                print(f"ERROR: install of '{dep['name']}' failed.")
                sys.exit(1)

            installed[f"{dep['name']} -> {task['name']}"] = True

        if first_install:
            # no install task available

            print(f"ERROR: '{dep['name']}' test failed, but no install script provided.")
            sys.exit(1)

        if not do_test(dep, depth, print_first_test=False):
            print(f"ERROR: '{dep['name']}' installed, but test still failing.")
            sys.exit(1)


    resolved.add(dep['name'])
    print(" "*depth, f"Done with {dep['name']}.")

def usage(full=False):
    print("""\
wdm <mode> target

    <mode>: dryrun|test|install|usage
    - usage: prints this message.
    - dryrun: do not run test nor install tasks.
    - test: only test if a dependency is satisfied.
    - install: test dependencies and install those unsatisfied.

Environment:
    WDM_DEPENDENCY_FILE must point to a valid WDM dependency file.

Returns:
    2 if an error occured
    1 if the testing is unsuccessful (test mode)
    1 if an installation failed (ensure mode)
    0 if the testing is successful (test mode)
    0 if the dependencies are all satisfied (ensure mode)
""")
    if not full: return
    print("""\
Examples:
    $ export WDM_DEPENDENCY_FILE=...
    $ wdm test has_nfd
    $ wdm ensure has_gpu_operator
---
name: has_gpu_operator
spec:
  requirements:
  - has_nfd
  tests:
  - name: has_nfd_operatorhub
    type: shell
    spec: oc get pod -l app.kubernetes.io/component=gpu-operator -A -oname
  install:
  - name: install_gpu_operator
    type: shell
    spec: ./run_toolbox.py gpu_operator deploy_from_operatorhub
  - name: install_gpu_operator
    type: shell
    spec: ./run_toolbox.py gpu_operator wait_deployment
---
name: has_nfd
spec:
  tests:
  - name: has_nfd_labels
    type: shell
    spec: ./run_toolbox.py nfd has_labels
  install:
  - name: install_nfd_from_operatorhub
    type: shell
    spec: ./run_toolbox.py nfd_operator deploy_from_operatorhub
""")

def main():
    global WDM_DEPENDENCY_FILE, wdm_mode

    try: wdm_mode = sys.argv[1]
    except KeyError: wdm_mode = None

    if wdm_mode == "usage":
        usage(full=True)
        sys.exit(0)

    if wdm_mode not in ("dryrun", "test", "ensure"):
        print("ERROR: <mode> must be 'dryrun', 'test' or 'ensure', not '{wdm_mode}'.")
        usage()
        sys.exit(2)

    WDM_DEPENDENCY_FILE = os.getenv("WDM_DEPENDENCY_FILE")
    if WDM_DEPENDENCY_FILE is None:
        print("ERROR: WDM_DEPENDENCY_FILE must give the path to the dependency file.")
        usage()
        sys.exit(2)

    # ---

    with open(WDM_DEPENDENCY_FILE) as f:
        docs = list(yaml.safe_load_all(f))

    for doc in docs:
        if doc is None: continue # empty block
        deps[doc["name"]] = doc

    try:
        entrypoint = sys.argv[2]
    except IndexError:
        entrypoint = docs[0]["name"]

    resolve(deps[entrypoint])
    print("All done.")

    if wdm_mode in ("dryrun"):
        print("Would have tested:")
    else:
        print("Tested:")

    has_test_failures = False
    for taskname, success in tested.items():
        print(f"- {'☑ ' if success else ('' if success is None else '❎ ')}{taskname}")
        if success == False: has_test_failures = True

    if installed:
        if wdm_mode in ("test", "dryrun"):
            print("Would have installed:")
        else:
            print("Installed:")
        [print(f"- {taskname}") for taskname in installed]
    else:
        if wdm_mode in ("test", "dryrun"):
            print("Would have installed: nothing.")
        else:
            print("Installed: nothing.")

    if has_test_failures:
        print("Some tests failed, exit with errcode=1.")
        sys.exit(1)


if __name__ == "__main__":
    main()
