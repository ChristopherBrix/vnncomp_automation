# from nikolaik/python-nodejs:python3.8-nodejs14
FROM python:3.8-slim-buster
RUN apt-get update && \
    apt-get install -y apache2-dev sqlite3 unzip less ssh && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel

WORKDIR "~"
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

RUN mkdir -p "/var/www/html/vnncomp"
WORKDIR "/var/www/html/vnncomp"

COPY ./requirements.txt .
RUN pip install -r requirements.txt
RUN rm ./requirements.txt

EXPOSE 5000

ENV PYTHONASYNCIODEBUG=1
ENV AWS_SCRIPT_ROOT="/var/www/html/vnncomp/vnncomp/"

CMD ["./launch_container.sh"]