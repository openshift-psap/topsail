:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Repo.send_job_completion_notification


repo send_job_completion_notification
=====================================

Send a *job completion* notification to github and/or slack about the completion of a test job.

A *job completion* notification is the message sent at the end of a CI job.


Parameters
----------


``reason``  

* Reason of the job completion. Can be ERR or EXIT.
* type: Str


``status``  

* A status message to write at the top of the notification.
* type: Str


``github``  

* Enable or disable sending the *job completion* notification to Github

* default value: ``True``


``slack``  

* Enable or disable sending the *job completion* notification to Slack

* default value: ``True``


``dry_run``  

* If enabled, don't send any notification, just show the message in the logs

