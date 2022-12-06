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
# COPY . .

# RUN rm -r "./data"

RUN rm ./requirements.txt



#RUN python -m venv venv
#RUN source ./venv/bin/activate



EXPOSE 5000
#CMD flask --app main --debug run

ENV PYTHONASYNCIODEBUG=1
ENV AWS_SCRIPT_ROOT="/var/www/html/vnncomp/vnncomp/"

#CMD python -m vnncomp.main
#CMD gunicorn --bind 0.0.0.0:5000 wsgi
CMD ["./launch_container.sh"]