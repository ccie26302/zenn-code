import os, sys
from PIL import Image, ImageDraw, ImageFont
PAGES = [["Quarterly operations report", "Storage costs fell by twelve percent this quarter.", "Most of the savings came from lifecycle rules.", "Old logs now move to archive after ninety days."],
         ["Security review", "All public buckets were closed in September.", "Service account keys are no longer created.", "Access is granted per bucket, not per project."],
         ["Next steps", "Enable budget alerts for every project.", "Review the IAM policy every month.", "Remove unused service accounts before December."]]
def font():
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(f): return ImageFont.truetype(f, 34)
    return ImageFont.load_default()
if __name__ == "__main__":
    fnt = font(); ims = []
    for lines in PAGES:
        im = Image.new("L", (1240, 1754), 255); d = ImageDraw.Draw(im)
        for i, l in enumerate(lines): d.text((100, 150 + i * 90), l, fill=0, font=fnt)
        ims.append(im.rotate(0.6, fillcolor=255).convert("RGB"))
    ims[0].save(os.path.join(sys.argv[1], "scan.pdf"), save_all=True, append_images=ims[1:], resolution=150)
