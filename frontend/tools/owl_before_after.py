"""Label unmodified browser captures at desktop display scale and 2x pixels.

This makes review evidence only. It never renders a pose or changes owl assets.
"""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/owl-diagonal-repair'
BACKGROUND = '#eaf3f9'
INK = '#244253'
MUTED = '#587284'
CASES = [
    {'id': 0, 'title': 'Up-right: yaw +7.5, pitch +4.5', 'region': 'Eyes', 'crop': [380, 115, 715, 270]},
    {'id': 2, 'title': 'Up-right: yaw +12, pitch +7.2', 'region': 'Eyes', 'crop': [380, 115, 715, 270]},
    {'id': 1, 'title': 'Down-left: yaw -7.5, pitch -4.5', 'region': 'Neck', 'crop': [260, 335, 700, 555]},
    {'id': 3, 'title': 'Down-left: yaw -12, pitch -7.2', 'region': 'Neck', 'crop': [260, 335, 700, 555]},
]


def font(size):
    for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def flat(image):
    result = Image.new('RGBA', image.size, BACKGROUND)
    result.alpha_composite(image.convert('RGBA'))
    return result.convert('RGB')


def panel(case, before, after):
    width, height, margin, gap, column = 1832, 978, 24, 24, 880
    result = Image.new('RGB', (width, height), BACKGROUND)
    draw = ImageDraw.Draw(result)
    draw.text((margin, 17), case['title'], fill=INK, font=font(25))
    draw.text((margin, 53), 'Same coordinates, unchanged browser pixels, pale background for alpha inspection', fill=MUTED, font=font(16))
    context_box = (150, 0, 900, 610)
    normal_scale = 590 / 1163
    context_size = tuple(round(v * normal_scale) for v in (750, 610))
    for index, (label, source) in enumerate([('BEFORE', before), ('AFTER', after)]):
        x = margin + index * (column + gap)
        draw.text((x, 88), label, fill=INK, font=font(22))
        draw.text((x, 120), 'Normal desktop scale: full owl width 590 px', fill=MUTED, font=font(16))
        context = flat(source.crop(context_box)).resize(context_size, Image.Resampling.LANCZOS)
        result.paste(context, (x + (column - context.width)//2, 148))
        draw.text((x, 483), f"{case['region']} detail: 2x source pixels (nearest-neighbor enlargement)", fill=MUTED, font=font(16))
        crop = flat(source.crop(case['crop']))
        crop = crop.resize((crop.width*2, crop.height*2), Image.Resampling.NEAREST)
        result.paste(crop, (x + (column-crop.width)//2, 518))
    draw.line((width//2, 86, width//2, height-20), fill='#c7d9e4', width=1)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', default='native-before')
    parser.add_argument('--after', default='silhouette-final')
    parser.add_argument('--out', default='before-after-review')
    args = parser.parse_args()
    before_dir, after_dir, out = (EVIDENCE / value for value in [args.before, args.after, args.out])
    before_poses = json.loads((before_dir / 'poses.json').read_text())
    after_poses = json.loads((after_dir / 'poses.json').read_text())
    if before_poses != after_poses:
        raise ValueError('Before/after pose metadata differs')
    images, records = {}, []
    for case in CASES:
        paths = [folder / f"pose-{case['id']:03d}.png" for folder in [before_dir, after_dir]]
        pair = [Image.open(path).convert('RGBA') for path in paths]
        if any(image.size != (1163, 1353) for image in pair):
            raise ValueError(f'Unexpected native capture size: {paths}')
        images[case['id']] = pair
        records.append({**case, 'pose': before_poses[case['id']], 'sources': [{'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]})
    out.mkdir(parents=True, exist_ok=True)
    panels = []
    for case in CASES:
        result = panel(case, *images[case['id']])
        result.save(out / f"pose-{case['id']:03d}-comparison.png")
        panels.append(result)
    combined = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), BACKGROUND)
    y = 0
    for result in panels:
        combined.paste(result, (0, y)); y += result.height
    combined.save(out / 'diagonal-before-after.png')
    # Compact normal-scale sheet: no enlargement of the source pixels.
    normal = Image.new('RGB', (880, 4*365), BACKGROUND); draw=ImageDraw.Draw(normal)
    for row, case in enumerate(CASES):
        draw.text((15, row*365+9), case['title'], fill=INK, font=font(17))
        for col, (label, source) in enumerate(zip(['BEFORE', 'AFTER'], images[case['id']])):
            draw.text((col*440+15, row*365+36), label, fill=MUTED, font=font(15))
            crop=flat(source.crop((150,0,900,610))).resize((380,309),Image.Resampling.LANCZOS)
            normal.paste(crop,(col*440+30,row*365+56))
    normal.save(out / 'normal-scale-before-after.png')
    (out / 'comparison.json').write_text(json.dumps({'scope': 'Four static browser poses, not temporal or whole-field approval', 'before': args.before, 'after': args.after, 'background': BACKGROUND, 'nativeSize': [1163,1353], 'desktopFullOwlWidth':590, 'detailScale':2, 'detailResampling':'nearest', 'cases':records},indent=2)+'\n')
    print(out)


if __name__ == '__main__':
    main()
