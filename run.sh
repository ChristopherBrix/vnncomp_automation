docker build -t vnncomp:latest . ; docker run --mount type=bind,source="$(pwd)/data",target=/var/www/html/vnncomp/data -it -p 5000:5000 vnncomp:latest
