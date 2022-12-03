# from nikolaik/python-nodejs:python3.8-nodejs14
FROM python:3.8-slim-buster
RUN apt-get update && apt-get install -y apache2-dev && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip setuptools wheel

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
#CMD python -m vnncomp.main
#CMD gunicorn --bind 0.0.0.0:5000 wsgi
CMD ["./launch_container.sh"]