# 模範解答と惜しい誤答の共通: しきい値 MIN 秒以上の無音だけを、前後0.1秒を残して切り詰める
import re, subprocess, sys
src, dst, MIN = sys.argv[1], sys.argv[2], float(sys.argv[3])
r = subprocess.run(["ffmpeg", "-i", src, "-af", "silencedetect=noise=-30dB:d=%s" % MIN, "-f", "null", "-"], capture_output=True, text=True)
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
keep, cur = [], 0.0
for s, e in zip(st, en):
    keep.append((cur, s + 0.1)); cur = e - 0.1
keep.append((cur, total))
f = ";".join("[0:a]atrim=%f:%f,asetpts=PTS-STARTPTS[a%d]" % (a, b, i) for i, (a, b) in enumerate(keep))
f += ";" + "".join("[a%d]" % i for i in range(len(keep))) + "concat=n=%d:v=0:a=1[o]" % len(keep)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", f, "-map", "[o]", dst], check=True)
