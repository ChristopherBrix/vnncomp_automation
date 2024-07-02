# VNN-COMP Automation

This repository provides the code that was used to automate the [VNN-COMP](https://vnncomp.christopher-brix.de).

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

This code is the snapshot of the code at the end of the VNN-COMP 2024.
The process was a bit convoluted and sometimes hectic, so best-practices were not always followed.

- An AWS key pair needs to be stored in `data/vnncomp.pem` (that name must also be used in AWS)
- An AWS Access key needs to be stored in `data/awskey.csv`
- To support uploading a benchmark to GitHub, create a new ssh key, enter the public key in GitHub and place the private `id_rsa` file in `data/id_rsa`
- Use `docker build -t vnncomp:latest . ; docker run --env ROOT_URL="https://vnncomp.christopher-brix.de" --mount type=bind,source="$(pwd)",target=/var/www/html/vnncomp -it -p 5000:5000 vnncomp:latest` to build and run the container. 
- For local usage, expose your localhost via `ngrok http 5000` (so AWS instances can ping it) and run `docker build -t vnncomp:latest . ; docker run --env ROOT_URL="$(curl -s localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')" --env GIT_COMMIT=$(git rev-parse HEAD) --mount type=bind,source="$(pwd)",target=/var/www/html/vnncomp -it -p 5000:5000 vnncomp:latest`

However, the code should still provide a good insight into how the competition was automated and should provide a good starting point for future iterations of the VNN-COMP or similiar events.

## To-Dos

To ensure that this code can be reused, several steps are currently planned

 - Create a docker environment to make the setup reproducible
 - Clean up the code to fix issues introduced by last-minute changes and avoid code that's commented out because it's only necessary in certain situations
 - Improve the frontend
 - Implement feedback (configuration of submissions via .yaml file, better testing of benchmark submissions, etc.)

This repository will be updated as those improvements are incorporated.
