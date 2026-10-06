#!/bin/sh
set -eu
systemd-run --user --unit=nilim-disaster-reports-jsonl \
 --description='NILIM disaster PDFs to page JSONL' \
 --property=Nice=15 --property=IOSchedulingClass=idle \
 --property=CPUQuota=50% --property=MemoryMax=512M --property=Restart=no \
 --property=StandardOutput=append:/sata_hdd_24tb/hf_data/nilim-disaster-reports/data/jsonl/extract.log \
 --property=StandardError=append:/sata_hdd_24tb/hf_data/nilim-disaster-reports/data/jsonl/extract.log \
 /home/yuiseki/anaconda3/bin/python /sata_hdd_24tb/hf_data/nilim-disaster-reports/src/extract_jsonl.py \
 --root /sata_hdd_24tb/hf_data/nilim-disaster-reports/data \
 --out /sata_hdd_24tb/hf_data/nilim-disaster-reports/data/jsonl
