FROM postgres:9.6

RUN apt-get update && apt-get install -y postgresql-q3c

ADD ./q3c.sh /docker-entrypoint-initdb.d/init-user-db.sh



