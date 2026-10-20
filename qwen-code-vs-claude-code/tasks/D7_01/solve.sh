#!/bin/bash
cd "$1" && mkdir -p sorted no_exif && for f in $(ls camera | sort); do d=$(exiftool -s3 -DateTimeOriginal -d %Y%m%d_%H%M%S camera/$f); if [ -z "$d" ]; then mv camera/$f no_exif/; else n=$d.jpg; k=2; while [ -e sorted/$n ]; do n=${d}_$k.jpg; k=$((k+1)); done; mv camera/$f sorted/$n; fi; done
