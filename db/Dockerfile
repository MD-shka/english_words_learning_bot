FROM postgres:16

RUN apt-get update && apt-get install -y python3 python3-pip jq

#COPY schema.sql /docker-entrypoint-initdb.d/schema.sql
COPY 01_run_generate_data_script.sh /docker-entrypoint-initdb.d/
COPY generate_data.py /docker-entrypoint-initdb.d/
COPY words.json /docker-entrypoint-initdb.d/
COPY data.sql /docker-entrypoint-initdb.d/data.sql