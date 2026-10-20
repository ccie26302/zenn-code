# 動画・音声の判定の共通部品(ffprobe / ffmpeg)
import json, re, subprocess
def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None
def stream(pr, kind):
    return next((s for s in (pr or {}).get("streams", []) if s.get("codec_type") == kind), None)
def dur(pr):
    return float((pr or {}).get("format", {}).get("duration", 0) or 0)
def frame_gray(p, t, w=64, h=36, crop=None):
    vf = ("crop=%s," % crop if crop else "") + "scale=%d:%d,format=gray" % (w, h)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", p, "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-"], capture_output=True)
    return r.stdout
def silences(p, noise="-30dB", d=0.5):
    r = subprocess.run(["ffmpeg", "-i", p, "-af", "silencedetect=noise=%s:d=%s" % (noise, d), "-f", "null", "-"], capture_output=True, text=True)
    return len(re.findall(r"silence_end", r.stderr)), r.stderr.count("silence_start")
def ebur(p):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", p, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", tail); TP = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return (float(I.group(1)) if I else None, float(TP.group(1)) if TP else None)
def packets(p, sel="v:0"):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "packet=size", "-of", "csv=p=0", p], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.strip().isdigit()]
def silence_list(p, noise="-30dB", d=0.5):
    r = subprocess.run(["ffmpeg", "-i", p, "-af", "silencedetect=noise=%s:d=%s" % (noise, d), "-f", "null", "-"], capture_output=True, text=True)
    return [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", r.stderr)]
