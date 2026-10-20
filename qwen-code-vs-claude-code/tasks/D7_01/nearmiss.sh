#!/bin/bash
# 惜しい誤答: 同じ撮影日時を上書きしてしまう
cd "$1" && mkdir -p sorted no_exif && for f in $(ls camera | sort); do d=$(exiftool -s3 -DateTimeOriginal -d %Y%m%d_%H%M%S camera/$f); if [ -z "$d" ]; then mv camera/$f no_exif/; else mv -f camera/$f sorted/$d.jpg; fi; done
