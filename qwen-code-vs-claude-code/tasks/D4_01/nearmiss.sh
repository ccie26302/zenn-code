#!/bin/bash
# 惜しい誤答: 名前の順(a, b, c ではなく c, b, a)で結合する
cd "$1" && qpdf --empty --pages pdfs/c.pdf pdfs/b.pdf pdfs/a.pdf -- merged.pdf && mkdir -p split && for i in 1 2 3; do s=$(( (i-1)*10+1 )); e=$(( i*10 )); [ $e -gt 28 ] && e=28; qpdf merged.pdf --pages . $s-$e -- split/part-0$i.pdf; done
