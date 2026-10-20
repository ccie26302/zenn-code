# 別解: pdfimages で画像を抜き出して OCR
cd "$1" && pdfimages -png scan.pdf im && : > scan.txt && for f in $(ls im-*.png | sort); do tesseract $f stdout 2>/dev/null >> scan.txt; done && rm -f im-*.png
