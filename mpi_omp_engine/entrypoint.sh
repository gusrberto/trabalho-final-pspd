#!/bin/bash
set -e

# Garante que o diretório e o arquivo config existem
if [ ! -d /home/mpiuser/.ssh ]; then
  mkdir -p /home/mpiuser/.ssh
  chown mpiuser:mpiuser /home/mpiuser/.ssh
fi

if [ ! -f /home/mpiuser/.ssh/config ]; then
  echo -e "Host *\n    Port 2222\n    StrictHostKeyChecking no\n    UserKnownHostsFile /dev/null" > /home/mpiuser/.ssh/config
  chown mpiuser:mpiuser /home/mpiuser/.ssh/config
fi

exec "$@"