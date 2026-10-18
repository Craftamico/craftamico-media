"""Render Craftamico social cards (KW43) – 4:5 for IG/FB/LinkedIn, 9:16 frames for TikTok."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os

OUT = '/tmp/claude-0/render/out'
os.makedirs(OUT, exist_ok=True)
FD = '/tmp/claude-0/fontpkg/package/files/'
BALOO = FD + 'baloo-2-latin-800-normal.woff'
INTER_R = '/usr/share/fonts/opentype/inter/Inter-Regular.otf'
INTER_M = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'
INTER_B = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'

BG_TOP = (28, 42, 140)
BG_BOT = (17, 24, 98)
WHITE = (255, 255, 255)
SOFT = (214, 220, 255)
ACCENT = (150, 165, 255)
AMBER = (240, 190, 70)


def font(path, size):
    return ImageFont.truetype(path, size)


def gradient(w, h, top=BG_TOP, bot=BG_BOT):
    im = Image.new('RGB', (w, h), top)
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    return im


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split('\n'):
        words = para.split(' ')
        cur = ''
        for w in words:
            test = (cur + ' ' + w).strip()
            if draw.textlength(test, font=fnt) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_lines(draw, x, y, lines, fnt, fill, lh):
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def wordmark(draw, x, y, size=44, color=WHITE):
    f = font(BALOO, size)
    draw.text((x, y), 'Craftamico', font=f, fill=color)
    w = draw.textlength('Craftamico', font=f)
    draw.text((x + w + 2, y), '.', font=f, fill=ACCENT)


def pill(draw, x, y, text, size=30):
    f = font(INTER_M, size)
    tw = draw.textlength(text, font=f)
    pad_x, h = 26, size + 30
    draw.rounded_rectangle([x, y, x + tw + 2 * pad_x, y + h], radius=h // 2,
                           fill=(255, 255, 255, 30), outline=(255, 255, 255, 90), width=2)
    draw.text((x + pad_x, y + 13), text, font=f, fill=SOFT)
    return y + h


def base(w, h):
    im = gradient(w, h).convert('RGBA')
    # soft glow
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([int(w * 0.45), -int(h * 0.15), int(w * 1.3), int(h * 0.45)], fill=(90, 110, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    return Image.alpha_composite(im, glow)


def text_card(w, h, tag, headline, body, footer, top_y=None, head_size=None, body_size=None, list_items=None):
    im = base(w, h)
    ov = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    mx = 96
    maxw = w - 2 * mx
    y = top_y if top_y is not None else int(h * 0.12)
    wordmark(d, mx, y, 46)
    y += 110
    y = pill(d, mx, y, tag) + 48
    hs = head_size or 92
    hf = font(BALOO, hs)
    hl = wrap(d, headline, hf, maxw)
    y = draw_lines(d, mx, y, hl, hf, WHITE, int(hs * 1.08)) + 44
    if list_items:
        nf = font(BALOO, 64)
        lf = font(INTER_B, 40)
        for i, it in enumerate(list_items, 1):
            d.text((mx, y - 6), str(i), font=nf, fill=AMBER)
            ll = wrap(d, it, lf, maxw - 80)
            y = draw_lines(d, mx + 80, y + 8, ll, lf, WHITE, 52) + 26
        y += 10
    if body:
        bs = body_size or 42
        bf = font(INTER_R, bs)
        bl = wrap(d, body, bf, maxw)
        y = draw_lines(d, mx, y, bl, bf, SOFT, int(bs * 1.38)) + 30
    if footer:
        ff = font(INTER_B, 38)
        d.text((mx, y), footer, font=ff, fill=ACCENT)
        y += 50
    if top_y is None or h < 1900:
        start = int(h * 0.12) if top_y is None else top_y
        shift = int((h - (y - start)) / 2) - start
        ov = ov.transform(ov.size, Image.AFFINE, (1, 0, 0, 0, 1, -shift))
    return Image.alpha_composite(im, ov).convert('RGB')


def photo_round(path, size, radius=40):
    ph = Image.open(path).convert('RGB')
    ph = ImageOps.fit(ph, size, Image.LANCZOS, centering=(0.5, 0.5))
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0], size[1]], radius=radius, fill=255)
    return ph, mask


def label(d, x, y, text, size=28, dark=False):
    f = font(INTER_B, size)
    tw = d.textlength(text, font=f)
    h = size + 22
    d.rounded_rectangle([x, y, x + tw + 36, y + h], radius=h // 2,
                        fill=(255, 255, 255, 235) if not dark else (20, 26, 90, 220))
    d.text((x + 18, y + 9), text, font=f, fill=(20, 26, 90) if not dark else WHITE)


def before_after_card(w, h, before, after, tag, headline, footer, ai_note='KI-Visualisierung'):
    im = base(w, h)
    ov = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    mx = 72
    y = 70
    wordmark(d, mx, y, 42)
    y += 92
    hf = font(BALOO, 66)
    hl = wrap(d, headline, hf, w - 2 * mx)
    y = draw_lines(d, mx, y, hl, hf, WHITE, 72) + 26
    gap = 24
    pw = (w - 2 * mx - gap) // 2
    ph_h = int(h - y - 150)
    for i, (p, lab) in enumerate([(before, 'Vorher'), (after, 'Nachher · ' + ai_note)]):
        photo, mask = photo_round(p, (pw, ph_h))
        x = mx + i * (pw + gap)
        im.paste(photo, (x, y), mask)
        label(d, x + 18, y + 18, lab, 26)
    y += ph_h + 36
    ff = font(INTER_B, 36)
    d.text((mx, y), footer, font=ff, fill=ACCENT)
    tf = font(INTER_R, 26)
    note = 'Beispielbild, ' + ai_note + ' – echtes Ergebnis kann abweichen'
    d.text((mx, y + 52), note, font=tf, fill=(170, 178, 230))
    return Image.alpha_composite(im, ov).convert('RGB')


def tiktok_photo_frame(photo_path, top_text, sub, ai=None):
    """9:16 full-bleed photo with readable text in the upper third (nothing in the bottom area)."""
    w, h = 1080, 1920
    ph = ImageOps.fit(Image.open(photo_path).convert('RGB'), (w, h), Image.LANCZOS)
    im = ph.convert('RGBA')
    shade = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for yy in range(0, 900):
        a = int(215 * (1 - yy / 900))
        sd.line([(0, yy), (w, yy)], fill=(10, 14, 60, a))
    im = Image.alpha_composite(im, shade)
    d = ImageDraw.Draw(im)
    mx = 80
    y = 200
    hf = font(BALOO, 92)
    for ln in wrap(d, top_text, hf, w - 2 * mx):
        tw = d.textlength(ln, font=hf)
        d.text(((w - tw) / 2, y), ln, font=hf, fill=WHITE)
        y += 98
    if sub:
        sf = font(INTER_B, 44)
        y += 40
        for ln in wrap(d, sub, sf, w - 2 * mx):
            tw = d.textlength(ln, font=sf)
            d.text(((w - tw) / 2, y), ln, font=sf, fill=SOFT)
            y += 58
    if ai:
        f = font(INTER_B, 30)
        tw = d.textlength(ai, font=f)
        x = (w - tw - 36) / 2
        d.rounded_rectangle([x, y + 24, x + tw + 36, y + 24 + 52], radius=26, fill=(255, 255, 255, 230))
        d.text((x + 18, y + 33), ai, font=f, fill=(20, 26, 90))
    return im.convert('RGB')


def end_frame():
    w, h = 1080, 1920
    im = base(w, h)
    d = ImageDraw.Draw(im)
    f = font(BALOO, 140)
    t = 'Craftamico'
    tw = d.textlength(t, font=f)
    x = (w - tw - 40) / 2
    d.text((x, 700), t, font=f, fill=WHITE)
    d.text((x + tw + 4, 700), '.', font=f, fill=ACCENT)
    sf = font(INTER_M, 46)
    s = 'Renovieren. Planen. Transformieren.'
    d.text(((w - d.textlength(s, font=sf)) / 2, 900), s, font=sf, fill=SOFT)
    uf = font(INTER_B, 44)
    u = 'craftamico.com'
    d.text(((w - d.textlength(u, font=uf)) / 2, 990), u, font=uf, fill=ACCENT)
    return im.convert('RGB')


UP = '/mnt/user-data/uploads/'
BATH_B = UP + 'Dated_1970s_bathroom_interior_20261018142923.jpg'
BATH_A = UP + 'Bathroom_renovation_design_and_s__20261018142928.jpg'
LIV_B = UP + 'Living_room_from_1980s_20261018151457.jpg'
LIV_A = UP + 'Modern_living_room_renovation_de__20261018151502.jpg'

if __name__ == '__main__':
    S45 = (1080, 1350)
    # Mo – Gründerstory
    text_card(*S45, 'Warum es Craftamico gibt',
              'Stundenlang Handwerker suchen. Und raten, was es kostet.',
              'Genau darauf hatte ich vor jeder Renovierung keine Lust mehr. Also habe ich angefangen, Craftamico zu bauen.',
              'craftamico.com').save(f'{OUT}/mo-gruender-4x5.png', quality=95)
    # Di – Bad vorher/nachher
    before_after_card(*S45, BATH_B, BATH_A, 'Badsanierung',
                      'Was kostet mein neues Bad? Sieh es, bevor du anfängst.',
                      'craftamico.com/badsanierung-mannheim').save(f'{OUT}/di-bad-4x5.png', quality=95)
    # Do – Besichtigung
    items = ['Was genau gemacht werden soll', 'Wie es vor Ort wirklich aussieht', 'Ob das Budget zum Vorhaben passt']
    text_card(*S45, 'Für Handwerksbetriebe', '3 Dinge, die du vor jeder Besichtigung wissen willst',
              'Bei Craftamico stehen sie schon in der Anfrage: Foto, Beschreibung und KI-Kostenrahmen.',
              'craftamico.com/handwerker', head_size=80, body_size=38, list_items=items).save(f'{OUT}/do-besichtigung-4x5.png', quality=95)
    text_card(1080, 1920, 'Für Handwerksbetriebe', '3 Dinge, die du vor jeder Besichtigung wissen willst',
              'Bei Craftamico stehen sie schon in der Anfrage: Foto, Beschreibung und KI-Kostenrahmen.',
              'craftamico.com/handwerker', top_y=360, head_size=86, body_size=40, list_items=items).save(f'{OUT}/do-besichtigung-9x16.png', quality=95)
    # Sa – Wohnzimmer
    before_after_card(*S45, LIV_B, LIV_A, 'Renovierung',
                      'Gleicher Raum. Andere Welt.',
                      'craftamico.com/renovierung-mannheim').save(f'{OUT}/sa-wohnzimmer-4x5.png', quality=95)
    tiktok_photo_frame(LIV_B, 'Wohnzimmer noch im 80er-Look?', 'Wie würde es renoviert aussehen?').save(f'{OUT}/sa-tt-1.png', quality=95)
    tiktok_photo_frame(LIV_A, 'Gleicher Raum. Andere Welt.', 'Foto hochladen, KI-Vorschau mit Kostenrahmen bekommen.', ai='KI-Visualisierung').save(f'{OUT}/sa-tt-2.png', quality=95)
    # So – Frage an Handwerker
    text_card(*S45, 'Ehrliche Frage an Handwerker', 'Was nervt dich an Kundenanfragen am meisten?',
              'A) Kein Foto, nur „Können Sie mal vorbeikommen?“\nB) Budget passt nicht zum Wunsch\nC) Nach dem Angebot hört man nie wieder was',
              'Schreib A, B oder C in die Kommentare', head_size=86, body_size=40).save(f'{OUT}/so-frage-4x5.png', quality=95)
    text_card(1080, 1920, 'Ehrliche Frage an Handwerker', 'Was nervt dich an Kundenanfragen am meisten?',
              'A) Kein Foto, nur „Können Sie mal vorbeikommen?“\nB) Budget passt nicht zum Wunsch\nC) Nach dem Angebot hört man nie wieder was',
              'Schreib A, B oder C in die Kommentare', top_y=360, head_size=92, body_size=42).save(f'{OUT}/so-frage-9x16.png', quality=95)
    end_frame().save(f'{OUT}/end-9x16.png', quality=95)
    print('ok')
