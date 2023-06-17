# With minor modifications (create directories) from
# https://git.fh-aachen.de/embeddedutils/webdav_uploader

from webdav3.client import Client
import argparse
import os

version = "0.0.1"


class UploadType:
    File = 0
    Dir = 1
    NA = 2


parser = argparse.ArgumentParser(description="cli WebDav Uploader v" + version)
parser.add_argument(
    "-r",
    "--remote_path",
    type=str,
    help="Path in server where file or dir will be uploaded",
    required=True,
)
parser.add_argument(
    "-l", "--local_path", type=str, help="Path of File or Dir to upload", required=True
)
parser.add_argument(
    "-n", "--name", type=str, help="Name of the benchmark", required=True
)

args = vars(parser.parse_args())
args["server"] = "https://rwth-aachen.sciebo.de/remote.php/webdav"
args["username"] = os.getenv('SCIEBO_USERNAME')
args["pass"] = os.getenv('SCIEBO_PASSWORD') 

options = {
    "webdav_hostname": args["server"],
    "webdav_login": args["username"],
    "webdav_password": args["pass"],
}
client = Client(options)
client.mkdir("vnncomp2023/" + args["name"])
client.mkdir("vnncomp2023/" + args["name"] + "/seed_676744409")
client.clean("vnncomp2023/" + args["name"] + "/seed_676744409")
client.mkdir("vnncomp2023/" + args["name"] + "/seed_676744409")
client.mkdir("vnncomp2023/" + args["name"] + "/seed_676744409/onnx")
client.mkdir("vnncomp2023/" + args["name"] + "/seed_676744409/vnnlib")

# TODO This is a hack. The calling script will pass the whole path, but here we need the directory. We should fix that in the calling code, but it's easier here.
args["remote_path"] = "/".join(args["remote_path"].split("/")[:-1])

remote_path_check = client.check(args["remote_path"])
if not remote_path_check:
    raise Exception("Remote Path %s does not exist!" % args["remote_path"])

upload_type = UploadType.NA
upload_name = ""

if os.path.isdir(args["local_path"]):
    upload_type = UploadType.Dir
elif os.path.isfile(args["local_path"]):
    upload_type = UploadType.File
if upload_type == UploadType.NA:
    raise Exception("Upload path %s is neither a dir or file!" % args["local_path"])

upload_name = os.path.basename(args["local_path"])

remote_path = args["remote_path"] + "/seed_676744409/" + upload_name

print("Uploading %s to remote path: %s " % (args["local_path"], remote_path))

client.upload_sync(remote_path=remote_path, local_path=args["local_path"])

print("Upload finished!")
