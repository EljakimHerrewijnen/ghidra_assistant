#!/bin/bash

if ! test -f .env; then
    echo "You need to copy .env.sample to .env, and then edit it"
    echo
    exit 1
fi

# create check return function
check_return() {
    if [ $? -ne 0 ]; then
        # Red color
        echo -e "\e[31m$1\e[0m"
        exit 1
    fi
}

ok() {
    # Green color
    echo -e "\e[32m$1\e[0m"
}

cd elastic-bsim
sudo docker build -t elastic-bsim:latest .
check_return "Failed to build elastic-bsim docker image"
cd ..

sudo docker compose up --wait
check_return "Failed to start docker compose"

# Wait 2min for Elasticsearch server to bootstrap
sleep 120

sudo docker compose exec elastic-bsim /usr/share/elasticsearch/bin/elasticsearch-reset-password -b -s -u elastic > elasticpw.txt
check_return "Failed to reset elastic password"

ELASTICPW=$(echo -n "$(cat ./elasticpw.txt)")

sed -i "s/ELASTIC_PASSWORD=\".*$/ELASTIC_PASSWORD=\"${ELASTICPW}\"/" .env
source .env

# Download and extract Ghidra
# curl -LJ -o ghidra.zip https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.1.2_build/ghidra_11.1.2_PUBLIC_20240709.zip
# unzip ghidra.zip
# rm ghidra.zip

# Create a new bsim database, using the existing elastic user creds
echo ""
echo "*********"
echo "Note that, below, you'll be prompted for the database password."
echo "The password for this database is: ${ELASTICPW}"
echo "*********"
echo ""

# Perform the database creation step
"${GHIDRA_ROOT}/support/bsim" createdatabase "${ELASTIC_URL}/bsim" medium_nosize "--user=elastic" "--name=Herreweb_BSIM"
