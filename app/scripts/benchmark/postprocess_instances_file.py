import sys

assert len(sys.argv) == 2
filename = sys.argv[1]

with open(filename, "r") as f:
    lines = f.readlines()

with open(filename, "w") as f:
    for line in lines:
        onnx = line.split(",")[0].split("/")[-1].strip()
        vnnlib = line.split(",")[1].split("/")[-1].strip()
        timeout = line.split(",")[2].strip()
        f.write(f"onnx/{onnx},vnnlib/{vnnlib},{timeout}\n")
