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

Currently, the code is set up to use the AWS region `us-west-2`. If you want to change this, search for this string and adapt the relevant scripts.
*Important*: If you use this AWS region to run any instances besides those managed by the VNN-COMP, you must assign them the tag `IgnoreForVNNComp`. Otherwise they will be automatically terminated when the server fails to connect to them.

- Create an AWS key pair with the name `vnncomp` in the `.pem` format and store the resulting `vnncomp.pem` file in the `data` directory.
- Create an AWS access key. Safe it in `data/awskey.csv` in the format
```
User Name,Access key ID,Secret access key
default,[ID],[SECRET]
```
- Create an AWS security group with the name `sshonly` that allows TCP inbound and arbitrary outbound traffic. The group id must be updated in `vnncomp/scripts/create_new_eni.sh`
- To support uploading a benchmark to GitHub, create a new ssh key, enter the public key in GitHub and place the private `id_rsa` file in `data/id_rsa`
- Use `docker build -t vnncomp:latest . ; docker run --name vnncomp --restart=always --env ROOT_URL=$WEBSITE_ROOT_URL --env GIT_COMMIT=$(git rev-parse HEAD) --env SCIEBO_USERNAME=$SCIEBO_USERNAME --env SCIEBO_PASSWORD=$SCIEBO_PASSWORD --env AUTO_APPLY_DB_UPGRADES=1 --mount type=bind,source="$(pwd)",target=/var/www/html/vnncomp -d -t -p 5000:5000 vnncomp:latest` with appropriate values for the environment variables to build and run the container. 
- For local usage, expose your localhost via `ngrok http 5000` (so AWS instances can ping it) and run `docker build -t vnncomp:latest . ; docker run --name vnncomp --env ROOT_URL="$(curl -s localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')" --env GIT_COMMIT=LOCAL --mount type=bind,source="$(pwd)",target=/var/www/html/vnncomp -it --rm -p 5000:5000 vnncomp:latest`. You can then open the website locally at `127.0.0.1:5000` and open a shell in this docker container using `docker exec -it vnncomp bash`.

## Development

If modify a class that's stored in the database, open a shell in the container, and run `flask db migrate -m "Description of the change"`. Verify that the generated migration file is correct. Then apply it using `flask db upgrade`. The server will always execute all new migration files if `AUTO_APPLY_DB_UPGRADES=1` is set.