#!/bin/sh
set -eu
systemd-run --user --unit=nilim-disaster-reports-download \
 --description='NILIM disaster survey PDF collection: expanded official disaster reports' \
 --property=Nice=15 --property=IOSchedulingClass=idle --property=CPUQuota=25% \
 --property=MemoryMax=256M --property=Restart=no \
 --property=StandardOutput=append:/sata_hdd_24tb/hf_data/nilim-disaster-reports/data/download.log \
 --property=StandardError=append:/sata_hdd_24tb/hf_data/nilim-disaster-reports/data/download.log \
 /home/yuiseki/anaconda3/bin/python /sata_hdd_24tb/hf_data/nilim-disaster-reports/src/fetch.py \
 --root /sata_hdd_24tb/hf_data/nilim-disaster-reports/data
