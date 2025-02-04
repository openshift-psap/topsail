import os
import pathlib
import sys

from projects.repo.scripts.validate_role_files import main as role_files_main
from projects.repo.scripts.validate_role_vars_used import main as role_vars_used_main
import projects.repo.scripts.ansible_default_config
import projects.repo.scripts.toolbox_rst_documentation

import projects.core.library.ansible_toolbox

TOOLBOX_THIS_DIR = pathlib.Path(__file__).absolute().parent
PROJECT_DIR = TOOLBOX_THIS_DIR.parent
TOPSAIL_DIR = TOOLBOX_THIS_DIR.parent.parent.parent

class Repo:
    """
    Commands to perform consistency validations on this repo itself
    """
    @staticmethod
    def validate_role_files():
        """
        Ensures that all the Ansible variables defining a
        filepath (`project/*/toolbox/`) do point to an existing file.
        """
        exit(role_files_main())

    @staticmethod
    def validate_role_vars_used():
        """
        Ensure that all the Ansible variables defined are
        actually used in their role (with an exception for symlinks)
        """
        exit(role_vars_used_main())

    @staticmethod
    def validate_no_wip():
        """
        Ensures that none of the commits have the WIP flag in their
        message title.
        """

        retcode = os.system(str(PROJECT_DIR / "scripts" / "validate_no_wip.sh"))
        # I don't know why this ^^^ return 256 on failure
        # but Python swallows it :/
        if retcode == 256: retcode = 1

        exit(retcode)


    @staticmethod
    def validate_no_broken_link():
        """
        Ensure that all the symlinks point to a file
        """

        has_broken_links = os.system("find . -type l -exec file {} \\; | grep 'broken symbolic link'") == 0
        exit(1 if has_broken_links else 0)

    @staticmethod
    def generate_ansible_default_settings():
        """
        Generate the `defaults/main/config.yml` file of the Ansible roles, based on the Python definition.
        """
        projects.repo.scripts.ansible_default_config.generate_all(projects.core.library.ansible_toolbox.Toolbox())
        exit(0)

    @staticmethod
    def send_job_completion_notification(
            reason: str,
            status: str,
            github = True,
            slack = True,
            dry_run = False,
    ):
        """
        Send a *job completion* notification to github and/or slack about the completion of a test job.

        A *job completion* notification is the message sent at the end of a CI job.

        Args:
          reason: reason of the job completion. Can be ERR or EXIT.
          status: a status message to write at the top of the notification.
          github: enable or disable sending the *job completion* notification to Github
          slack: enable or disable sending the *job completion* notification to Slack
          dry_run: if enabled, don't send any notification, just show the message in the logs
        """

        # lazy import to avoid loading this vvv anytime `./run_toolbox.py` is launched
        import projects.repo.toolbox.notifications.send as send_notif

        failed = send_notif.send_job_completion_notification(reason, status, github, slack, dry_run)

        exit(1 if failed else 0)

    @staticmethod
    def generate_middleware_ci_secret_boilerplate(name, description, varname=None):
        """
        Generate the boilerplace code to include a new secret in the Middleware CI configuration

        Args:
          name: name of the new secret to include
          description: description of the secret to include
          varname: optional short name of the file
        """
        if varname is None:
            varname = name.replace(".", "_").replace("-", "_")

        print(f"""
0. Prepare the environment:

- install 'git secret'
- clone the middlewareperformance/lab-ci repository, `main` branch
- clone the middlewareperformance/performance-lab-scripts repository, `wreicher-rhods` branch

========================
in the `perflab-ci` repo
========================

1 execute this command:

```
cp $PSAP_ODS_SECRET_PATH/{name} jobs/external-teams/rhods/
```

2. include this code in `jobs/external-teams/rhods/A00_dir.groovy`

```
        def {varname}_file = readFileFromWorkspace("jobs/external-teams/rhods/{name}")
        configNode << 'org.jenkinsci.plugins.plaincredentials.impl.FileCredentialsImpl' {{
          id('{varname}')
          description('{description}')
          fileName('{name}')
          secretBytes(Base64.encoder.encodeToString({varname}_file.getBytes("UTF-8")))
        }}
```

3. execute the following commands:

```
git secret add jobs/external-teams/rhods/{name}

git secret hide -F -m -d  |& grep -v 'file not found'

git add -p
# .gitignore
# .gitsecret/paths/mapping.cfg
# jobs/external-teams/rhods/A00_dir.groovy

git add jobs/external-teams/rhods/{name}.secret

git commit -m "Add {name} secret to the RHODS/topsail project"
```

4. Open the PR against the `main` branch.

========================
in the `performance-lab-scripts` repo
========================

1. edit the `Jenkinsfile`:
```
                        file(credentialsId: '{varname}', variable: '{varname}_file'),
```
and
```
                    writeFile file: 'secret/{name}', text: readFile({varname}_file)
```

2. execute the following commands:
```
git add -p Jenkinsfile
git commit -m "Add {name} secret"
```

3. Open the PR against the `wreicher-rhods` branch.
""")

    @staticmethod
    def generate_toolbox_rst_documentation():
        """
        Generate the `doc/toolbox.generated/*.rst` file, based on the Toolbox Python definition.
        """
        projects.repo.scripts.toolbox_rst_documentation.generate_all(projects.core.library.ansible_toolbox.Toolbox())
        exit(0)

    @staticmethod
    def generate_toolbox_related_files():
        """
        Generate the rst document and Ansible default settings, based on the Toolbox Python definition.
        """
        sys.argv[2] = "generate_toolbox_rst_documentation"
        projects.repo.scripts.toolbox_rst_documentation.generate_all(projects.core.library.ansible_toolbox.Toolbox())

        sys.argv[2] = "generate_ansible_default_settings"
        projects.repo.scripts.ansible_default_config.generate_all(projects.core.library.ansible_toolbox.Toolbox())

        exit(0)
