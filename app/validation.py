import json
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageStat

from app.projects import write_json


def compare_images(original, reconstructed, output):
    a = Image.open(original).convert('RGB')
    b = Image.open(reconstructed).convert('RGB')
    dimension_warning = None
    if a.size != b.size:
        dimension_warning = f'Screenshot dimensions differ: {a.size} vs {b.size}. Reconstruction was resampled for a pixel comparison.'
        b = b.resize(a.size, Image.Resampling.LANCZOS)
    difference = ImageChops.difference(a, b)
    mae = sum(ImageStat.Stat(difference).mean) / 3
    # Keep neutral pixels dark; amplify mismatches for inspection.
    ImageEnhance.Contrast(ImageEnhance.Brightness(difference).enhance(3)).enhance(1.4).save(output)
    return {'mean_absolute_rgb_difference': round(mae, 4), 'normalized_pixel_agreement': round(100 * (1 - mae / 255), 2),
            'viewport_pixels': list(a.size), 'dimension_warning': dimension_warning,
            'metric_note': 'Pixel agreement measures RGB similarity at this viewport. It does not validate behavior, accessibility, semantics or backend functionality.'}


def quality_report(root, dom_report=None):
    root = Path(root)
    report = compare_images(root / 'screenshots/original.png', root / 'screenshots/reconstructed.png', root / 'screenshots/difference.png')
    if dom_report:
        report['dom'] = dom_report
    manifest = json.loads((root / 'metadata/project.json').read_text('utf-8'))
    report['capture_warnings'] = manifest.get('warnings', [])
    report['correction'] = 'Local resource paths are rewritten during export. No arbitrary CSS correction was attempted.'
    write_json(root / 'metadata/quality-report.json', report)
    return report
