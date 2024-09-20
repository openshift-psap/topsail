import os
import pathlib


from projects.repo.scripts.validate_role_files import main as role_files_main
from projects.repo.scripts.validate_role_vars_used import main as role_vars_used_main
import projects.repo.scripts.ansible_default_config

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
        Generate the 'defaults/main/config.yml' file of the Ansible roles, based on the Python definition.
        """
        projects.repo.scripts.ansible_default_config.generate_all(projects.core.library.ansible_toolbox.Toolbox())
        exit(0)

    @staticmethod
    def send_job_completion_notification(
            reason: str,
            status: str,
            github = True,
            slack = True,
    ):
        """
        Send a *job completion* notification to github and/or slack about the completion of a test job.

        A *job completion* notification is the message sent at the end of a CI job.

        Args:
          reason: reason of the job completion. Can be ERR or EXIT.
          status: a status message to write at the top of the notification.
          github: enable or disable sending the *job completion* notification to Github
          slack: enable or disable sending the *job completion* notification to Slack
        """

        # lazy import to avoid loading this vvv anytime `./run_toolbox.py` is launched
        import projects.repo.toolbox.notifications.send as send_notif

        failed = send_notif.send_job_completion_notification(reason, status, github, slack)

        exit(1 if failed else 0)
