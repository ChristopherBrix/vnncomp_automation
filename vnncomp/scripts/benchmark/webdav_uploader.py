# With minor modifications (create directories) from
# https://git.fh-aachen.de/embeddedutils/webdav_uploader

from webdav3.client import Client
from webdav3.exceptions import WebDavException
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
try:
    client.free()
    print("Login successfull")
except WebDavException as exception:
    print("HTTP error encountered: ", exception.code)
    raise

client.mkdir("vnncomp2024/" + args["name"])
client.mkdir("vnncomp2024/" + args["name"] + "/seed_896832480")
client.clean("vnncomp2024/" + args["name"] + "/seed_896832480")
client.mkdir("vnncomp2024/" + args["name"] + "/seed_896832480")
client.mkdir("vnncomp2024/" + args["name"] + "/seed_896832480/onnx")
client.mkdir("vnncomp2024/" + args["name"] + "/seed_896832480/vnnlib")

# TODO This is a hack. The calling script will pass the whole path, but here we need the directory. We should fix that in the calling code, but it's easier here.
upload_name = "/".join(args["local_path"].split("/")[-2:])
remote_path = "vnncomp2024" + "/" + args["name"] + "/seed_896832480/" + upload_name

upload_type = UploadType.NA

if os.path.isdir(args["local_path"]):
    upload_type = UploadType.Dir
elif os.path.isfile(args["local_path"]):
    upload_type = UploadType.File
if upload_type == UploadType.NA:
    raise Exception("Upload path %s is neither a dir or file!" % args["local_path"])

print("Uploading %s to remote path: %s " % (args["local_path"], remote_path))

client.upload_sync(remote_path=remote_path, local_path=args["local_path"])

print("Upload finished!")
