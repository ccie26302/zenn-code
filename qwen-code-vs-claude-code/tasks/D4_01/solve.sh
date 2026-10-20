#!/bin/bash
cd "$1" && qpdf --empty --pages pdfs/a.pdf pdfs/b.pdf pdfs/c.pdf -- merged.pdf && mkdir -p split && for i in 1 2 3; do s=$(( (i-1)*10+1 )); e=$(( i*10 )); [ $e -gt 28 ] && e=28; qpdf merged.pdf --pages . $s-$e -- split/part-0$i.pdf; done
