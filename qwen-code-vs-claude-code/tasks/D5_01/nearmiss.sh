# 惜しい誤答: 1ページ目だけを OCR する
cd "$1" && pdftoppm -r 300 -png -f 1 -l 1 scan.pdf pg && tesseract $(ls pg-*.png | head -1) - -l eng 2>/dev/null > scan.txt && rm -f pg-*.png
