# VNN-COMP Automation

This repository provides the code that was used to automate the [VNN-COMP 2022](https://vnncomp.christopher-brix.de).

In the future, it will be updated to improve the process for the next iteration.

## General Structure

The website creates/terminates instances on AWS and communicates with them via SSH.
This is done via shell scripts that can be found in `app/scripts`.

`app/views.py` and `app/auth.py` list all URL routes.

The main logic can be found in

- `app/utils/aws_instance.py`: Stores all information related to AWS instances. The `AwsManager` takes care of tracking running instances and spawning new ones when necessary.
- `app/utils/task_steps.py`: Contains all steps that may be necessary to install/run a benchmark/toolkit.
- `app/utils/task.py`: Defines the tasks of evaluating a benchmark and a tool. This combines the previously defined steps to pipelines that are run sequentially.

## How to Set This Up?

This code is the snapshot of the code at the end of the VNN-COMP 2022.
The process was a bit convoluted and sometimes hectic, so best-practices were not always followed.

- An AWS access key needs to be stored in `~/.ssh/vnncomp.pem` to allow the server to manage AWS instances.
- Some magic is required to start the webserver.
- Some packages may be missing in the requirements, it's not clear how the Pipenv and requirements.txt need to be merged.
- A cronjob needs to ping `/manual_update` to fetch updates from running AWS instances and to move to the next steps of defined pipelines.
- Some code that was used during the competition is commented out.

However, the code should still provide a good insight into how the competition was automated and should provide a good starting point for future iterations of the VNN-COMP or similiar events.

## To-Dos

To ensure that this code can be reused, several steps are currently planned

 - Create a docker environment to make the setup reproducible
 - Clean up the code to fix issues introduced by last-minute changes and avoid code that's commented out because it's only necessary in certain situations
 - Improve the frontend
 - Implement feedback (configuration of submissions via .yaml file, better testing of benchmark submissions, etc.)

This repository will be updated as those improvements are incorporated.
