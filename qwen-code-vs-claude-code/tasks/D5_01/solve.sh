cd "$1" && pdftoppm -r 300 -png scan.pdf pg && : > scan.txt && for f in $(ls pg-*.png | sort); do tesseract $f - -l eng 2>/dev/null >> scan.txt; done && rm -f pg-*.png
