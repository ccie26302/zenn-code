# 2段階の loudnorm: 1回目で測り、2回目で linear=true で合わせる
import json, re, subprocess, sys
src, dst, I = sys.argv[1], sys.argv[2], sys.argv[3]
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "loudnorm=I=%s:TP=-2:LRA=11:print_format=json" % I, "-f", "null", "-"], capture_output=True, text=True)
m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
af = ("loudnorm=I=%s:TP=-2:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
      % (I, m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"], m["target_offset"]))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, "-ar", "44100", dst], check=True)
