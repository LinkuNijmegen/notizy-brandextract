#!/usr/bin/env python3
import argparse
import json
import re
import zipfile
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'v': 'urn:schemas-microsoft-com:vml',
}

DEFAULT_PROFILE = {
    'extras': {
        'disclaimer': {
            'text': '',
            'enabled': False,
            'alignment': 'left',
        },
        'fonts_used': [],
        'colors_used': [],
    },
    'layout': {
        'page_size': 'A4',
        'margins_mm': {'top': 20, 'left': 20, 'right': 20, 'bottom': 20},
        'orientation': 'portrait',
    },
    'cover_page': {
        'meta': [
            {'label': 'Datum', 'value': '{{generated_at}}'},
            {'label': 'Type', 'value': '{{meeting_type}}'},
        ],
        'title': '{{document_title}}',
        'divider': {
            'show': False,
            'color': '#000000',
            'thickness': 1,
            'width_ratio': 0.3,
        },
        'enabled': False,
        'spacing': {
            'after_meta': 20,
            'after_title': 12,
            'before_title': 0,
            'after_subtitle': 8,
        },
        'subtitle': '{{organization_name}}',
        'alignment': 'left',
        'show_logo': False,
        'meta_color': '#000000',
        'title_color': '#000000',
        'meta_font_size': 9,
        'subtitle_color': '#000000',
        'title_font_size': 24,
        'background_color': None,
        'subtitle_font_size': 14,
    },
    'typography': {
        'body': {
            'alignment': 'left',
            'font_size': 9,
            'text_color': '#000000',
            'font_family': 'Calibri',
            'font_weight': 'Light',
            'line_spacing': 1.3,
            'paragraph_spacing': {'after': 4, 'before': 0},
        },
        'lists': {
            'font_size': 9,
            'indent_mm': 8,
            'font_family': 'Calibri',
            'font_weight': 'Light',
            'bullet_color': '#000000',
            'line_spacing': 1.3,
            'spacing_between_items': 2,
            'bullet_indent_adjust_mm': 2,
        },
        'quote': {
            'font_size': 9,
            'padding_mm': 4,
            'text_color': '#000000',
            'font_family': 'Calibri',
            'font_weight': 'Light',
            'border_color': '#CCCCCC',
            'line_spacing': 1.15,
            'background_color': '#F5F5F5',
        },
        'table': {
            'font_size': 9,
            'text_color': '#000000',
            'font_family': 'Calibri',
            'font_weight': 'Light',
            'border_color': '#CCCCCC',
            'border_width': 0.5,
            'line_spacing': 1.15,
            'cell_padding_mm': 2,
            'header_text_color': '#FFFFFF',
            'header_font_weight': 'Bold',
            'alternate_row_color': None,
            'header_background_color': '#2C3E50',
        },
        'headings': {
            'color': '#333333',
            'sizes': {'h1': 13, 'h2': 12, 'h3': 11, 'h4': 11},
            'padding_mm': 3,
            'font_family': 'Calibri',
            'font_weight': 'Bold',
            'line_spacing': {'h1': 1.15, 'h2': 1.15, 'h3': 1.15, 'h4': 1.15},
            'divider_color': '#000000',
            'spacing_after': {'h1': 4, 'h2': 3, 'h3': 2, 'h4': 2},
            'spacing_before': {'h1': 8, 'h2': 6, 'h3': 4, 'h4': 3},
            'show_divider_for_h1': False,
        },
    },
    'page_footer': {
        'text': '',
        'alignment': 'right',
        'font_size': 7,
        'text_color': '#000000',
        'font_family': 'Calibri',
        'font_weight': 'Light',
        'show_on_cover': True,
        'show_page_numbers': True,
        'page_number_format': 'Pagina {{page_number}} van {{total_pages}}',
    },
    'page_header': {
        'logo': {
            'show': True,
            'position': 'right',
            'max_width_mm': 50,
            'max_height_mm': 15,
        },
        'text': '',
        'alignment': 'left',
        'font_size': 7,
        'text_color': '#cccccc',
        'font_family': 'Calibri',
        'font_weight': 'Light',
        'show_on_cover': True,
    },
    'action_table': {
        'show': False,
        'columns': [
            {'name': 'Item', 'width_percentage': 60},
            {'name': 'Verantwoordelijke', 'width_percentage': 20},
            {'name': 'Deadline', 'width_percentage': 20},
        ],
        'border_color': '#CCCCCC',
        'border_width': 0.5,
        'cell_padding_mm': 2,
        'header_text_color': '#FFFFFF',
        'header_background_color': '#95A5A6',
    },
    'contact_info': {
        'show': False,
        'fields': [
            'Kanaalstraat 200',
            '6541 XN Nijmegen',
            'Tel +31(0)88 024 93 33',
            'info@klokgroep.nl',
            'www.klokgroep.nl',
        ],
        'position': 'top_right',
        'alignment': 'right',
        'font_size': 8,
        'text_color': '#000000',
        'font_family': 'Calibri',
        'line_spacing': 1.2,
    },
    'category_tags': {
        'show': True,
        'tags': [
            {'text': 'Beeldvormend', 'text_color': '#FFFFFF', 'background_color': '#C77B2D'},
            {'text': 'Oordeelsvormend', 'text_color': '#FFFFFF', 'background_color': '#5E81AC'},
            {'text': 'Besluitvormend', 'text_color': '#FFFFFF', 'background_color': '#E74C3C'},
            {'text': 'Informerend', 'text_color': '#FFFFFF', 'background_color': '#27AE60'},
        ],
        'position': 'below_metadata',
        'font_size': 9,
        'padding_mm': 2,
        'font_family': 'Calibri',
        'font_weight': 'Bold',
        'spacing_after': 12,
        'spacing_between': 2,
    },
    'document_info': {
        'font_size': 9,
        'font_family': 'Arial',
        'line_spacing': 1.3,
        'spacing_after': 12,
        'metadata_fields': [
            {'label': 'Betreft:', 'value': '{{document_title}}', 'bold_label': False},
            {'label': 'Referentie:', 'value': '{{reference}}', 'bold_label': False},
            {'label': 'Pagina:', 'value': '{{page_info}}', 'bold_label': False},
            {'label': 'Voorzitter:', 'value': '{{chairman}}', 'bold_label': False},
            {'label': 'Notulist:', 'value': '{{secretary}}', 'bold_label': False},
            {'label': 'Deelnemers:', 'value': '{{participants}}', 'bold_label': False},
            {'label': 'Datum:', 'value': '{{date}}', 'bold_label': False},
            {'label': 'CC:', 'value': '{{cc}}', 'bold_label': False},
        ],
        'label_font_weight': 'Regular',
        'value_font_weight': 'Regular',
        'show_metadata_block': False,
    },
    'section_headers': {
        'colors': {
            'acties': '#95A5A6',
            'opening': '#2C3E50',
            'rondvraag': '#95A5A6',
            'informerend': '#27AE60',
            'beeldvormend': '#C77B2D',
            'besluitvormend': '#E74C3C',
            'oordeelsvormend': '#5E81AC',
        },
        'font_size': 11,
        'padding_mm': 3,
        'text_color': '#FFFFFF',
        'font_weight': 'Bold',
        'show_background': True,
    },
    'next_meeting_table': {
        'show': True,
        'columns': [
            {'name': 'Volgend overleg', 'width_percentage': 60},
            {'name': 'Datum', 'width_percentage': 20},
            {'name': 'Tijd', 'width_percentage': 20},
        ],
        'border_color': '#CCCCCC',
        'border_width': 0.5,
        'cell_padding_mm': 2,
        'header_text_color': '#FFFFFF',
        'header_background_color': '#2C3E50',
    },
}


def qw(tag):
    return '{%s}%s' % (NS['w'], tag)


def qr(tag):
    return '{%s}%s' % (NS['r'], tag)


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def twips_to_mm(value):
    if value is None:
        return None
    return value * 25.4 / 1440.0


def twips_to_pt(value):
    if value is None:
        return None
    return value / 20.0


def halfpoints_to_pt(value):
    if value is None:
        return None
    return value / 2.0


def points_to_mm(value):
    if value is None:
        return None
    return value * 25.4 / 72.0


def hex_to_rgb(value):
    if not value:
        return None
    value = value.lstrip('#')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', value):
        return None
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    if not rgb:
        return None
    return '#%02X%02X%02X' % rgb


def apply_tint_shade(color_hex, tint=None, shade=None):
    rgb = hex_to_rgb(color_hex)
    if not rgb:
        return None
    r, g, b = rgb
    if shade:
        try:
            factor = int(shade, 16) / 255.0
        except ValueError:
            factor = None
        if factor is not None:
            r = round(r * factor)
            g = round(g * factor)
            b = round(b * factor)
    if tint:
        try:
            factor = int(tint, 16) / 255.0
        except ValueError:
            factor = None
        if factor is not None:
            r = round(r + (255 - r) * factor)
            g = round(g + (255 - g) * factor)
            b = round(b + (255 - b) * factor)
    return rgb_to_hex((max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))


def normalize_docx_color(value):
    if not value:
        return None
    value = value.strip()
    if value.lower() in ('auto', 'none'):
        return None
    if re.fullmatch(r'[0-9a-fA-F]{6}', value):
        return '#' + value.upper()
    return None


def parse_theme_fonts(theme_root):
    if theme_root is None:
        return {}
    font_scheme = theme_root.find('.//a:fontScheme', NS)
    if font_scheme is None:
        return {}
    result = {'major': {}, 'minor': {}}
    for group in ('major', 'minor'):
        group_el = font_scheme.find('a:%sFont' % group, NS)
        if group_el is None:
            continue
        latin = group_el.find('a:latin', NS)
        ea = group_el.find('a:ea', NS)
        cs = group_el.find('a:cs', NS)
        result[group]['latin'] = latin.get('typeface') if latin is not None else None
        result[group]['ea'] = ea.get('typeface') if ea is not None else None
        result[group]['cs'] = cs.get('typeface') if cs is not None else None
    return result


def parse_theme_colors(theme_root):
    colors = {}
    if theme_root is None:
        return colors
    clr_scheme = theme_root.find('.//a:clrScheme', NS)
    if clr_scheme is None:
        return colors
    for child in list(clr_scheme):
        name = child.tag.split('}')[-1].lower()
        srgb = child.find('a:srgbClr', NS)
        if srgb is not None:
            value = srgb.get('val')
        else:
            sysclr = child.find('a:sysClr', NS)
            value = sysclr.get('lastClr') if sysclr is not None else None
        if value and re.fullmatch(r'[0-9a-fA-F]{6}', value):
            colors[name] = '#' + value.upper()
    return colors


def resolve_theme_font(theme_fonts, theme_value):
    if not theme_fonts or not theme_value:
        return None
    value = theme_value.lower()
    group = None
    if value.startswith('major'):
        group = 'major'
    elif value.startswith('minor'):
        group = 'minor'
    if not group:
        return None
    if 'eastasia' in value or value.endswith('ea'):
        return theme_fonts.get(group, {}).get('ea') or theme_fonts.get(group, {}).get('latin')
    if 'bidi' in value or value.endswith('cs'):
        return theme_fonts.get(group, {}).get('cs') or theme_fonts.get(group, {}).get('latin')
    return theme_fonts.get(group, {}).get('latin')


def resolve_docx_color(color_el, theme_colors):
    if color_el is None:
        return None
    val = get_attr(color_el, 'val')
    color = normalize_docx_color(val)
    if color:
        return color
    theme_color = get_attr(color_el, 'themeColor')
    if theme_color and theme_colors:
        key = theme_color.lower()
        theme_map = {
            'dark1': 'dk1',
            'light1': 'lt1',
            'dark2': 'dk2',
            'light2': 'lt2',
            'text1': 'dk1',
            'text2': 'dk2',
            'background1': 'lt1',
            'background2': 'lt2',
        }
        base = theme_colors.get(theme_map.get(key, key))
        if base:
            tint = get_attr(color_el, 'themeTint')
            shade = get_attr(color_el, 'themeShade')
            return apply_tint_shade(base, tint=tint, shade=shade)
    return None


def average(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def dedupe_preserve_order(items):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def extract_contact_lines(text):
    if not text:
        return []
    email_re = re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}', re.IGNORECASE)
    url_re = re.compile(r'(https?://\\S+|www\\.[^\\s]+)', re.IGNORECASE)
    phone_re = re.compile(r'(tel\\.?\\s*)?(\\+?\\d[\\d\\s().-]{6,}\\d)', re.IGNORECASE)
    postcode_re = re.compile(r'\\b\\d{4}\\s?[A-Z]{2}\\b', re.IGNORECASE)
    address_hint_re = re.compile(r'\\b(straat|laan|weg|plein|gracht|dreef|singel|kade|steeg|straat)\\b', re.IGNORECASE)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if email_re.search(line) or url_re.search(line) or phone_re.search(line) or postcode_re.search(line):
            lines.append(line)
            continue
        if address_hint_re.search(line) and any(ch.isdigit() for ch in line):
            lines.append(line)
    return lines


def extract_contact_info_from_extracted(extracted):
    sources = []
    header = extracted.get('page_header') or {}
    footer = extracted.get('page_footer') or {}
    if header.get('text'):
        sources.append(('header', header.get('text'), header))
    if footer.get('text'):
        sources.append(('footer', footer.get('text'), footer))
    fields = []
    format_info = {}
    for source, text, fmt in sources:
        lines = extract_contact_lines(text)
        if lines:
            fields.extend(lines)
            if not format_info:
                format_info = dict(fmt)
    fields = dedupe_preserve_order(fields)
    return {
        'fields': fields,
        'format': format_info,
    }


def split_font_family_weight(font_name):
    if not font_name:
        return None, None
    raw = font_name.strip()
    if not raw:
        return None, None
    weight_tokens = {
        'thin': 'Thin',
        'extralight': 'ExtraLight',
        'ultralight': 'ExtraLight',
        'light': 'Light',
        'book': 'Book',
        'regular': 'Regular',
        'normal': 'Regular',
        'medium': 'Medium',
        'semibold': 'SemiBold',
        'demibold': 'DemiBold',
        'bold': 'Bold',
        'extrabold': 'ExtraBold',
        'ultrabold': 'ExtraBold',
        'black': 'Black',
        'heavy': 'Black',
    }
    normalized = raw.replace('_', ' ')
    parts = re.split(r'[-\\s]+', normalized.strip())
    if not parts:
        return raw, None
    for token_count in (2, 1):
        if len(parts) >= token_count:
            candidate = ''.join(parts[-token_count:]).lower()
            if candidate in weight_tokens:
                family = ' '.join(parts[:-token_count]).strip()
                family = family if family else raw
                return family, weight_tokens[candidate]
    return raw, None


def guess_from_fonts_used(fonts_used):
    if not isinstance(fonts_used, dict) or not fonts_used:
        return None, None
    best_font = None
    best_count = -1
    for font, sizes in fonts_used.items():
        size_count = len([s for s in sizes if s is not None])
        if size_count > best_count:
            best_count = size_count
            best_font = font
    if not best_font:
        return None, None
    sizes = [s for s in fonts_used.get(best_font, []) if s is not None]
    if not sizes:
        return best_font, None
    return best_font, min(sizes)


def normalize_pdf_color(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = (value[0], value[0], value[0])
        if len(value) >= 3:
            rgb = []
            for channel in value[:3]:
                if isinstance(channel, float):
                    channel = int(round(channel * 255))
                channel = int(channel)
                rgb.append(max(0, min(255, channel)))
            return '#%02X%02X%02X' % tuple(rgb)
    if isinstance(value, (int, float)):
        channel = int(round(value * 255)) if isinstance(value, float) else int(value)
        channel = max(0, min(255, channel))
        return '#%02X%02X%02X' % (channel, channel, channel)
    return None


def normalize_pdf_font_name(name):
    if not name:
        return None
    if '+' in name and len(name.split('+', 1)[0]) == 6:
        return name.split('+', 1)[1]
    return name


def is_header_char(ch, height, band):
    top = ch.get('top')
    if top is None:
        y1 = ch.get('y1')
        if y1 is None:
            return False
        top = height - y1
    return top <= band


def is_footer_char(ch, height, band):
    bottom = ch.get('bottom')
    if bottom is None:
        y0 = ch.get('y0')
        if y0 is None:
            return False
        bottom = height - y0
    return bottom >= height - band


def read_docx_xml(zipf, path):
    try:
        data = zipf.read(path)
    except KeyError:
        return None
    return ET.fromstring(data)


def get_attr(element, attr, ns='w'):
    if element is None:
        return None
    return element.get('{%s}%s' % (NS[ns], attr)) or element.get(attr)


def parse_rpr(rpr, theme_fonts=None, theme_colors=None):
    info = {'font_family': None, 'font_size': None, 'color': None, 'bold': None}
    if rpr is None:
        return info
    rfonts = rpr.find('w:rFonts', NS)
    if rfonts is not None:
        for key in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
            value = get_attr(rfonts, key)
            if value:
                info['font_family'] = value
                break
        if not info['font_family']:
            for key in ('asciiTheme', 'hAnsiTheme', 'csTheme', 'eastAsiaTheme'):
                value = get_attr(rfonts, key)
                if value:
                    resolved = resolve_theme_font(theme_fonts, value)
                    if resolved:
                        info['font_family'] = resolved
                        break
    size_el = rpr.find('w:sz', NS) or rpr.find('w:szCs', NS)
    size_val = safe_int(get_attr(size_el, 'val'))
    info['font_size'] = halfpoints_to_pt(size_val) if size_val is not None else None
    color_el = rpr.find('w:color', NS)
    info['color'] = resolve_docx_color(color_el, theme_colors)
    bold_el = rpr.find('w:b', NS)
    if bold_el is not None:
        val = get_attr(bold_el, 'val')
        if val is None:
            info['bold'] = True
        else:
            info['bold'] = val not in ('0', 'false', 'off')
    return info


def parse_ppr(ppr, font_size_pt=None):
    info = {
        'alignment': None,
        'spacing_before': None,
        'spacing_after': None,
        'line_spacing': None,
    }
    if ppr is None:
        return info
    jc = ppr.find('w:jc', NS)
    info['alignment'] = get_attr(jc, 'val')
    spacing = ppr.find('w:spacing', NS)
    if spacing is not None:
        info['spacing_before'] = twips_to_pt(safe_int(get_attr(spacing, 'before')))
        info['spacing_after'] = twips_to_pt(safe_int(get_attr(spacing, 'after')))
        line = safe_int(get_attr(spacing, 'line'))
        line_rule = get_attr(spacing, 'lineRule')
        if line is not None:
            if line_rule in (None, 'auto'):
                info['line_spacing'] = round(line / 240.0, 2)
            elif line_rule == 'exact' and font_size_pt:
                info['line_spacing'] = round((line / 20.0) / font_size_pt, 2)
    return info


def parse_doc_defaults(styles_root, theme_fonts=None, theme_colors=None):
    defaults = {'rpr': {}, 'ppr': {}}
    if styles_root is None:
        return defaults
    doc_defaults = styles_root.find('w:docDefaults', NS)
    if doc_defaults is None:
        return defaults
    rpr_default = doc_defaults.find('w:rPrDefault/w:rPr', NS)
    ppr_default = doc_defaults.find('w:pPrDefault/w:pPr', NS)
    rpr = parse_rpr(rpr_default, theme_fonts=theme_fonts, theme_colors=theme_colors)
    ppr = parse_ppr(ppr_default, rpr.get('font_size'))
    defaults['rpr'] = rpr
    defaults['ppr'] = ppr
    return defaults


def merge_rpr(base, override):
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if value is None:
            continue
        merged[key] = value
    return merged


def merge_ppr(base, override):
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if value is None:
            continue
        merged[key] = value
    return merged


def resolve_style(style_id, styles, resolved, defaults):
    if style_id in resolved:
        return resolved[style_id]
    style = styles.get(style_id)
    if not style:
        return None
    base_rpr = defaults.get('rpr', {}) if defaults else {}
    base_ppr = defaults.get('ppr', {}) if defaults else {}
    based_on = style.get('based_on')
    if based_on:
        parent = resolve_style(based_on, styles, resolved, defaults)
        if parent:
            base_rpr = merge_rpr(base_rpr, parent.get('rpr'))
            base_ppr = merge_ppr(base_ppr, parent.get('ppr'))
    resolved_style = dict(style)
    resolved_style['rpr'] = merge_rpr(base_rpr, style.get('rpr'))
    resolved_style['ppr'] = merge_ppr(base_ppr, style.get('ppr'))
    resolved[style_id] = resolved_style
    return resolved_style


def parse_styles(styles_root, theme_fonts=None, theme_colors=None):
    styles = {}
    if styles_root is None:
        return {}, {}, {}
    defaults = parse_doc_defaults(styles_root, theme_fonts=theme_fonts, theme_colors=theme_colors)
    for style in styles_root.findall('w:style', NS):
        style_id = get_attr(style, 'styleId')
        name_el = style.find('w:name', NS)
        name = get_attr(name_el, 'val') or style_id
        based_on_el = style.find('w:basedOn', NS)
        based_on = get_attr(based_on_el, 'val')
        outline_el = style.find('w:pPr/w:outlineLvl', NS)
        outline_level = safe_int(get_attr(outline_el, 'val'))
        rpr = parse_rpr(style.find('w:rPr', NS), theme_fonts=theme_fonts, theme_colors=theme_colors)
        ppr = parse_ppr(style.find('w:pPr', NS), rpr.get('font_size'))
        styles[style_id] = {
            'name': name,
            'style_id': style_id,
            'type': get_attr(style, 'type'),
            'based_on': based_on,
            'outline_level': outline_level,
            'rpr': rpr,
            'ppr': ppr,
        }
    resolved = {}
    for style_id in styles.keys():
        resolve_style(style_id, styles, resolved, defaults)
    styles_by_name = {}
    for style in resolved.values():
        name = style.get('name')
        if name:
            styles_by_name[name.lower()] = style
    return resolved, styles_by_name, defaults


def collect_fonts_and_colors(styles, doc_root, theme_fonts=None, theme_colors=None):
    fonts = defaultdict(set)
    colors = set()

    def add_info(info):
        if not info:
            return
        font = info.get('font_family')
        size = info.get('font_size')
        color = info.get('color')
        if font:
            if size:
                fonts[font].add(round(size, 2))
            else:
                fonts[font].add(None)
        if color:
            colors.add(color)

    for style in styles.values():
        add_info(style.get('rpr'))

    if doc_root is not None:
        for rpr in doc_root.findall('.//w:rPr', NS):
            add_info(parse_rpr(rpr, theme_fonts=theme_fonts, theme_colors=theme_colors))

    return fonts, colors


def extract_layout(doc_root):
    layout = {}
    if doc_root is None:
        return layout
    sections = doc_root.findall('.//w:sectPr', NS)
    if not sections:
        return layout
    page_sizes = []
    orientations = []
    margins = []
    for sect in sections:
        pg_sz = sect.find('w:pgSz', NS)
        pg_mar = sect.find('w:pgMar', NS)
        width_twips = safe_int(get_attr(pg_sz, 'w'))
        height_twips = safe_int(get_attr(pg_sz, 'h'))
        width_mm = twips_to_mm(width_twips) if width_twips else None
        height_mm = twips_to_mm(height_twips) if height_twips else None
        orient = get_attr(pg_sz, 'orient') or (
            'landscape' if width_mm and height_mm and width_mm > height_mm else 'portrait'
        )
        orientations.append(orient)
        if width_mm and height_mm:
            page_sizes.append(detect_page_size(width_mm, height_mm))
        if pg_mar is not None:
            margins.append((
                round(twips_to_mm(safe_int(get_attr(pg_mar, 'top'))), 2),
                round(twips_to_mm(safe_int(get_attr(pg_mar, 'left'))), 2),
                round(twips_to_mm(safe_int(get_attr(pg_mar, 'right'))), 2),
                round(twips_to_mm(safe_int(get_attr(pg_mar, 'bottom'))), 2),
            ))
    layout['orientation'] = most_common(orientations)
    layout['page_size'] = most_common(page_sizes)
    margin_choice = most_common(margins)
    if margin_choice:
        layout['margins_mm'] = {
            'top': margin_choice[0],
            'left': margin_choice[1],
            'right': margin_choice[2],
            'bottom': margin_choice[3],
        }
    return layout


def detect_page_size(width_mm, height_mm):
    if width_mm is None or height_mm is None:
        return None
    w = round(width_mm, 1)
    h = round(height_mm, 1)
    if (abs(w - 210) <= 2 and abs(h - 297) <= 2) or (abs(w - 297) <= 2 and abs(h - 210) <= 2):
        return 'A4'
    return '%.1fx%.1fmm' % (w, h)


def match_heading_level(value):
    if not value:
        return None
    value = value.strip()
    match = re.match(r'(heading|kop)\\s*(\\d+)$', value, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(2))
    except ValueError:
        return None


def extract_heading_styles(styles):
    headings = {}
    for style in styles.values():
        level = None
        if style.get('type') == 'paragraph':
            outline = style.get('outline_level')
            if outline is not None:
                level = outline + 1
        if level is None:
            level = match_heading_level(style.get('name'))
        if level is None:
            level = match_heading_level(style.get('style_id'))
        if level and 1 <= level <= 4 and level not in headings:
            headings[level] = style
    return headings


def tokens_from_instr(instr_text):
    if not instr_text:
        return []
    text = instr_text.upper()
    tokens = []
    if 'NUMPAGES' in text or 'SECTIONPAGES' in text:
        tokens.append('{{total_pages}}')
    if 'PAGE' in text:
        tokens.append('{{page_number}}')
    return tokens


def extract_field_tokens(paragraph):
    tokens = []
    for instr in paragraph.findall('.//w:instrText', NS):
        tokens.extend(tokens_from_instr(instr.text))
    for fld in paragraph.findall('.//w:fldSimple', NS):
        tokens.extend(tokens_from_instr(get_attr(fld, 'instr')))
    return tokens


def extract_header_footer_text(root, theme_fonts=None, theme_colors=None):
    texts = []
    alignments = []
    run_infos = []
    for p in root.findall('.//w:p', NS):
        ppr = p.find('w:pPr', NS)
        align = get_attr(ppr.find('w:jc', NS), 'val') if ppr is not None else None
        if align:
            alignments.append(align)
        text = ''.join(t.text for t in p.findall('.//w:t', NS) if t.text)
        text = text.strip() if text else ''
        tokens = extract_field_tokens(p)
        if tokens:
            token_text = ' '.join(tokens)
            if text:
                text = (text + ' ' + token_text).strip()
            else:
                text = token_text
        if text:
            texts.append(text)
        for r in p.findall('w:r', NS):
            run_infos.append(parse_rpr(r.find('w:rPr', NS), theme_fonts=theme_fonts, theme_colors=theme_colors))
    return {
        'text': '\n'.join(texts).strip(),
        'alignment': most_common(alignments),
        'runs': run_infos,
    }


def parse_relationships_from(zipf, rels_path, ignore_external=True):
    rels_root = read_docx_xml(zipf, rels_path)
    rels = {}
    if rels_root is None:
        return rels
    for rel in rels_root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
        r_id = rel.get('Id')
        target = rel.get('Target')
        mode = rel.get('TargetMode')
        if ignore_external and mode and mode.lower() == 'external':
            continue
        if r_id and target:
            rels[r_id] = target
    return rels


def parse_relationships(zipf):
    return parse_relationships_from(zipf, 'word/_rels/document.xml.rels')


def most_common(values):
    values = [v for v in values if v]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def get_header_footer_targets(doc_root, zipf):
    header_info = {}
    footer_info = {}
    if doc_root is None:
        return [], []
    rels = parse_relationships(zipf)
    header_targets = []
    footer_targets = []
    for sect in doc_root.findall('.//w:sectPr', NS):
        for ref in sect.findall('w:headerReference', NS):
            r_id = ref.get(qr('id'))
            if r_id and r_id in rels:
                header_targets.append(rels[r_id])
        for ref in sect.findall('w:footerReference', NS):
            r_id = ref.get(qr('id'))
            if r_id and r_id in rels:
                footer_targets.append(rels[r_id])
    return header_targets, footer_targets


def extract_headers_and_footers(doc_root, zipf, theme_fonts=None, theme_colors=None):
    header_targets, footer_targets = get_header_footer_targets(doc_root, zipf)
    header_info = merge_header_footer_targets(zipf, header_targets, theme_fonts=theme_fonts, theme_colors=theme_colors)
    footer_info = merge_header_footer_targets(zipf, footer_targets, theme_fonts=theme_fonts, theme_colors=theme_colors)
    return header_info, footer_info


def merge_header_footer_targets(zipf, targets, theme_fonts=None, theme_colors=None):
    texts = []
    alignments = []
    runs = []
    for target in targets:
        path = 'word/%s' % target
        root = read_docx_xml(zipf, path)
        if root is None:
            continue
        info = extract_header_footer_text(root, theme_fonts=theme_fonts, theme_colors=theme_colors)
        if info.get('text'):
            texts.append(info['text'])
        if info.get('alignment'):
            alignments.append(info['alignment'])
        runs.extend(info.get('runs', []))
    return {
        'text': '\n'.join(texts).strip(),
        'alignment': most_common(alignments),
        'runs': runs,
    }


def normalize_rel_target(target):
    if not target:
        return None
    target = target.replace('\\', '/')
    if '://' in target:
        return None
    while target.startswith('../'):
        target = target[3:]
    if target.startswith('/'):
        target = target[1:]
    if not target.startswith('word/'):
        target = 'word/' + target
    return target


def rels_path_for_part(part_path):
    part_path = part_path.replace('\\', '/')
    if '/' not in part_path:
        return '_rels/%s.rels' % part_path
    base = part_path.rsplit('/', 1)[-1]
    parent = part_path.rsplit('/', 1)[0]
    return parent + '/_rels/' + base + '.rels'


def safe_filename(name):
    name = name or 'asset'
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    if not name or name in ('.', '..'):
        name = 'asset'
    return name


def unique_filename(name, used_names):
    base = Path(name).stem
    suffix = Path(name).suffix
    candidate = name
    counter = 1
    while candidate in used_names:
        candidate = '%s_%d%s' % (base, counter, suffix)
        counter += 1
    used_names.add(candidate)
    return candidate


def find_docx_images_in_part(zipf, part_path):
    root = read_docx_xml(zipf, part_path)
    if root is None:
        return []
    rels = parse_relationships_from(zipf, rels_path_for_part(part_path))
    if not rels:
        return []
    r_ids = set()
    for blip in root.findall('.//a:blip', NS):
        r_id = blip.get(qr('embed')) or blip.get(qr('link'))
        if r_id:
            r_ids.add(r_id)
    for img in root.findall('.//v:imagedata', NS):
        r_id = img.get(qr('id'))
        if r_id:
            r_ids.add(r_id)
    targets = []
    for r_id in r_ids:
        target = rels.get(r_id)
        norm = normalize_rel_target(target)
        if norm:
            targets.append(norm)
    return targets


def save_zip_member(zipf, member_path, dest_dir, used_names):
    try:
        data = zipf.read(member_path)
    except KeyError:
        return None
    filename = safe_filename(Path(member_path).name)
    filename = unique_filename(filename, used_names)
    dest_path = dest_dir / filename
    with open(dest_path, 'wb') as handle:
        handle.write(data)
    return dest_path


def derive_header_footer_format(info):
    if not info:
        return {}
    runs = info.get('runs', [])
    font = most_common([r.get('font_family') for r in runs if r])
    size = most_common([r.get('font_size') for r in runs if r])
    color = most_common([r.get('color') for r in runs if r])
    return {
        'text': info.get('text') or '',
        'alignment': info.get('alignment'),
        'font_family': font,
        'font_size': size,
        'text_color': color,
    }


def extract_body_style(styles):
    name_candidates = {
        'normal',
        'body text',
        'body',
        'bodytext',
        'text body',
        'standaard',
        'tekstblok',
    }
    for style in styles.values():
        if style.get('type') not in (None, 'paragraph'):
            continue
        name = (style.get('name') or '').lower()
        style_id = (style.get('style_id') or '').lower()
        if name in name_candidates or style_id in name_candidates:
            return style
    return None


def paragraph_style_id(paragraph):
    ppr = paragraph.find('w:pPr', NS)
    if ppr is None:
        return None
    pstyle = ppr.find('w:pStyle', NS)
    return get_attr(pstyle, 'val')


def is_heading_paragraph(paragraph, styles):
    ppr = paragraph.find('w:pPr', NS)
    if ppr is not None:
        outline_el = ppr.find('w:outlineLvl', NS)
        if outline_el is not None:
            outline_val = safe_int(get_attr(outline_el, 'val'))
            if outline_val is not None and outline_val <= 3:
                return True
    style_id = paragraph_style_id(paragraph)
    if style_id and style_id in styles:
        style = styles[style_id]
        outline_level = style.get('outline_level')
        if outline_level is not None and outline_level <= 3:
            return True
        name = style.get('name')
        if match_heading_level(name) or match_heading_level(style_id):
            return True
    return False


def derive_body_from_paragraphs(doc_root, styles, defaults, theme_fonts=None, theme_colors=None):
    if doc_root is None:
        return {}
    font_counts = Counter()
    size_counts = Counter()
    color_counts = Counter()
    alignment_counts = Counter()
    spacing_before = []
    spacing_after = []
    line_spacing = []

    defaults_rpr = (defaults or {}).get('rpr') or {}
    defaults_ppr = (defaults or {}).get('ppr') or {}

    for paragraph in doc_root.findall('.//w:p', NS):
        if is_heading_paragraph(paragraph, styles):
            continue
        style_id = paragraph_style_id(paragraph)
        style = styles.get(style_id) if style_id else None
        style_rpr = style.get('rpr') if style else {}
        style_ppr = style.get('ppr') if style else {}

        ppr = paragraph.find('w:pPr', NS)
        ppr_info = parse_ppr(ppr, style_rpr.get('font_size'))
        ppr_eff = merge_ppr(defaults_ppr, merge_ppr(style_ppr, ppr_info))
        if ppr_eff.get('alignment'):
            alignment_counts[ppr_eff['alignment']] += 1
        if ppr_eff.get('spacing_before') is not None:
            spacing_before.append(ppr_eff['spacing_before'])
        if ppr_eff.get('spacing_after') is not None:
            spacing_after.append(ppr_eff['spacing_after'])
        if ppr_eff.get('line_spacing') is not None:
            line_spacing.append(ppr_eff['line_spacing'])

        runs = paragraph.findall('.//w:r', NS)
        if not runs:
            rpr_eff = merge_rpr(defaults_rpr, style_rpr)
            if rpr_eff.get('font_family'):
                font_counts[rpr_eff['font_family']] += 1
            if rpr_eff.get('font_size'):
                size_counts[round(rpr_eff['font_size'], 2)] += 1
            if rpr_eff.get('color'):
                color_counts[rpr_eff['color']] += 1
            continue
        for run in runs:
            run_rpr = parse_rpr(run.find('w:rPr', NS), theme_fonts=theme_fonts, theme_colors=theme_colors)
            rpr_eff = merge_rpr(defaults_rpr, merge_rpr(style_rpr, run_rpr))
            if rpr_eff.get('font_family'):
                font_counts[rpr_eff['font_family']] += 1
            if rpr_eff.get('font_size'):
                size_counts[round(rpr_eff['font_size'], 2)] += 1
            if rpr_eff.get('color'):
                color_counts[rpr_eff['color']] += 1

    body = {
        'font_family': font_counts.most_common(1)[0][0] if font_counts else None,
        'font_size': size_counts.most_common(1)[0][0] if size_counts else None,
        'text_color': color_counts.most_common(1)[0][0] if color_counts else None,
        'alignment': alignment_counts.most_common(1)[0][0] if alignment_counts else None,
        'spacing_before': average(spacing_before),
        'spacing_after': average(spacing_after),
        'line_spacing': average(line_spacing),
    }
    return body


def build_extracted_from_docx(path, results_dir=None):
    extracted = {}
    results_dir = Path(results_dir) if results_dir else Path('results')
    with zipfile.ZipFile(path) as zipf:
        theme_root = read_docx_xml(zipf, 'word/theme/theme1.xml')
        theme_fonts = parse_theme_fonts(theme_root)
        theme_colors = parse_theme_colors(theme_root)
        styles_root = read_docx_xml(zipf, 'word/styles.xml')
        doc_root = read_docx_xml(zipf, 'word/document.xml')
        styles, _styles_by_name, defaults = parse_styles(
            styles_root,
            theme_fonts=theme_fonts,
            theme_colors=theme_colors,
        )
        fonts, colors = collect_fonts_and_colors(
            styles,
            doc_root,
            theme_fonts=theme_fonts,
            theme_colors=theme_colors,
        )
        extracted['fonts_used'] = fonts
        extracted['colors_used'] = colors
        extracted['layout'] = extract_layout(doc_root)

        body_style = extract_body_style(styles)
        body_from_paras = derive_body_from_paragraphs(
            doc_root,
            styles,
            defaults,
            theme_fonts=theme_fonts,
            theme_colors=theme_colors,
        )
        if not any(value is not None for value in body_from_paras.values()):
            body_from_paras = {}
        body = dict(body_from_paras)
        if body_style:
            body_rpr = body_style.get('rpr', {})
            body_ppr = body_style.get('ppr', {})
            style_body = {
                'font_family': body_rpr.get('font_family'),
                'font_size': body_rpr.get('font_size'),
                'text_color': body_rpr.get('color'),
                'line_spacing': body_ppr.get('line_spacing'),
                'spacing_before': body_ppr.get('spacing_before'),
                'spacing_after': body_ppr.get('spacing_after'),
                'alignment': body_ppr.get('alignment'),
            }
            for key, value in style_body.items():
                if body.get(key) is None:
                    body[key] = value
        if defaults:
            defaults_rpr = defaults.get('rpr') or {}
            defaults_ppr = defaults.get('ppr') or {}
            if body.get('font_family') is None:
                body['font_family'] = defaults_rpr.get('font_family')
            if body.get('font_size') is None:
                body['font_size'] = defaults_rpr.get('font_size')
            if body.get('text_color') is None:
                body['text_color'] = defaults_rpr.get('color')
            if body.get('line_spacing') is None:
                body['line_spacing'] = defaults_ppr.get('line_spacing')
            if body.get('spacing_before') is None:
                body['spacing_before'] = defaults_ppr.get('spacing_before')
            if body.get('spacing_after') is None:
                body['spacing_after'] = defaults_ppr.get('spacing_after')
            if body.get('alignment') is None:
                body['alignment'] = defaults_ppr.get('alignment')
        extracted['body'] = body

        headings = extract_heading_styles(styles)
        heading_info = {
            'sizes': {},
            'spacing_before': {},
            'spacing_after': {},
            'line_spacing': {},
            'font_family': None,
            'font_weight': None,
            'color': None,
        }
        for level, style in headings.items():
            rpr = style.get('rpr', {})
            ppr = style.get('ppr', {})
            if rpr.get('font_size'):
                heading_info['sizes']['h%d' % level] = rpr['font_size']
            if ppr.get('spacing_before') is not None:
                heading_info['spacing_before']['h%d' % level] = ppr['spacing_before']
            if ppr.get('spacing_after') is not None:
                heading_info['spacing_after']['h%d' % level] = ppr['spacing_after']
            if ppr.get('line_spacing') is not None:
                heading_info['line_spacing']['h%d' % level] = ppr['line_spacing']
            if not heading_info['font_family'] and rpr.get('font_family'):
                heading_info['font_family'] = rpr.get('font_family')
            if not heading_info['color'] and rpr.get('color'):
                heading_info['color'] = rpr.get('color')
            if rpr.get('bold'):
                heading_info['font_weight'] = 'Bold'
        extracted['headings'] = heading_info

        header_info, footer_info = extract_headers_and_footers(
            doc_root,
            zipf,
            theme_fonts=theme_fonts,
            theme_colors=theme_colors,
        )
        extracted['page_header'] = derive_header_footer_format(header_info)
        extracted['page_footer'] = derive_header_footer_format(footer_info)
        extracted['contact_info'] = extract_contact_info_from_extracted(extracted)

        header_targets, footer_targets = get_header_footer_targets(doc_root, zipf)
        document_targets = ['document.xml']
        assets_dir = results_dir / 'assets'
        assets_dir.mkdir(parents=True, exist_ok=True)
        used_names = set()
        asset_map = {}

        def add_assets_from_targets(targets, source_label):
            for target in targets:
                part_path = target
                if not part_path.startswith('word/'):
                    part_path = 'word/' + part_path
                image_targets = find_docx_images_in_part(zipf, part_path)
                for image_target in image_targets:
                    if image_target in asset_map:
                        asset_map[image_target]['sources'].add(source_label)
                        continue
                    saved_path = save_zip_member(zipf, image_target, assets_dir, used_names)
                    if not saved_path:
                        continue
                    asset_map[image_target] = {
                        'file': str(saved_path),
                        'original': image_target,
                        'sources': {source_label},
                    }

        add_assets_from_targets(header_targets, 'header')
        add_assets_from_targets(footer_targets, 'footer')
        add_assets_from_targets(document_targets, 'document')

        assets = []
        logo_files = []
        for item in asset_map.values():
            item['sources'] = sorted(item['sources'])
            assets.append(item)
            if 'header' in item['sources']:
                logo_files.append(item['file'])
        if assets:
            extracted['assets'] = assets
        if logo_files:
            extracted['logo_files'] = sorted(logo_files)

    return extracted


def build_extracted_from_pdf(path):
    try:
        import pdfplumber
    except ImportError:
        raise SystemExit('pdfplumber is required for PDF input. Install with: pip install pdfplumber')

    extracted = {
        'fonts_used': defaultdict(set),
        'colors_used': set(),
        'layout': {},
    }
    font_counts = Counter()
    size_counts = Counter()
    margin_samples = []
    header_texts = []
    footer_texts = []
    header_font_counts = Counter()
    header_size_counts = Counter()
    header_color_counts = Counter()
    footer_font_counts = Counter()
    footer_size_counts = Counter()
    footer_color_counts = Counter()

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            width = page.width
            height = page.height
            extracted['layout'].setdefault('page_size', detect_page_size(points_to_mm(width), points_to_mm(height)))
            orient = 'landscape' if width > height else 'portrait'
            extracted['layout'].setdefault('orientation', orient)

            chars = page.chars or []
            if chars:
                min_x0 = min(c['x0'] for c in chars)
                max_x1 = max(c['x1'] for c in chars)
                min_y0 = min(c['y0'] for c in chars)
                max_y1 = max(c['y1'] for c in chars)
                margin_samples.append({
                    'left': points_to_mm(min_x0),
                    'right': points_to_mm(width - max_x1),
                    'bottom': points_to_mm(min_y0),
                    'top': points_to_mm(height - max_y1),
                })

            header_band = height * 0.1
            footer_band = height * 0.1
            for ch in chars:
                font = normalize_pdf_font_name(ch.get('fontname'))
                size = ch.get('size')
                if font:
                    font_counts[font] += 1
                    if size:
                        extracted['fonts_used'][font].add(round(size, 2))
                if size:
                    size_counts[round(size, 2)] += 1
                color = normalize_pdf_color(ch.get('nonstroking_color') or ch.get('stroking_color'))
                if color:
                    extracted['colors_used'].add(color)
                if is_header_char(ch, height, header_band):
                    if font:
                        header_font_counts[font] += 1
                    if size:
                        header_size_counts[round(size, 2)] += 1
                    if color:
                        header_color_counts[color] += 1
                elif is_footer_char(ch, height, footer_band):
                    if font:
                        footer_font_counts[font] += 1
                    if size:
                        footer_size_counts[round(size, 2)] += 1
                    if color:
                        footer_color_counts[color] += 1
            header_page = page.within_bbox((0, 0, width, header_band))
            footer_page = page.within_bbox((0, height - footer_band, width, height))
            header_text = header_page.extract_text() if header_page else ''
            footer_text = footer_page.extract_text() if footer_page else ''
            if header_text:
                header_texts.append(header_text.strip())
            if footer_text:
                footer_texts.append(footer_text.strip())

    if margin_samples:
        extracted['layout']['margins_mm'] = {
            'top': round(sum(m['top'] for m in margin_samples) / len(margin_samples), 2),
            'left': round(sum(m['left'] for m in margin_samples) / len(margin_samples), 2),
            'right': round(sum(m['right'] for m in margin_samples) / len(margin_samples), 2),
            'bottom': round(sum(m['bottom'] for m in margin_samples) / len(margin_samples), 2),
        }

    most_common_font = None
    if font_counts:
        most_common_font = font_counts.most_common(1)[0][0]
        extracted['body'] = {
            'font_family': most_common_font,
            'font_size': size_counts.most_common(1)[0][0] if size_counts else None,
            'text_color': None,
            'line_spacing': None,
            'spacing_before': None,
            'spacing_after': None,
            'alignment': None,
        }

    sizes_sorted = [size for size, _ in size_counts.most_common()]
    body_size = extracted.get('body', {}).get('font_size')
    if sizes_sorted:
        heading_info = {
            'sizes': {},
            'spacing_before': {},
            'spacing_after': {},
            'line_spacing': {},
            'font_family': None,
            'font_weight': None,
            'color': None,
        }
        larger_sizes = [size for size in sorted(set(sizes_sorted), reverse=True) if body_size is None or size > body_size]
        chosen_sizes = larger_sizes if larger_sizes else sorted(set(sizes_sorted), reverse=True)
        for idx, size in enumerate(chosen_sizes[:4]):
            heading_info['sizes']['h%d' % (idx + 1)] = size
        heading_info['font_family'] = most_common_font if font_counts else None
        extracted['headings'] = heading_info

    extracted['page_header'] = {
        'text': '\n'.join(header_texts).strip(),
        'alignment': None,
        'font_family': header_font_counts.most_common(1)[0][0] if header_font_counts else None,
        'font_size': header_size_counts.most_common(1)[0][0] if header_size_counts else None,
        'text_color': header_color_counts.most_common(1)[0][0] if header_color_counts else None,
    }
    extracted['page_footer'] = {
        'text': '\n'.join(footer_texts).strip(),
        'alignment': None,
        'font_family': footer_font_counts.most_common(1)[0][0] if footer_font_counts else None,
        'font_size': footer_size_counts.most_common(1)[0][0] if footer_size_counts else None,
        'text_color': footer_color_counts.most_common(1)[0][0] if footer_color_counts else None,
    }
    extracted['contact_info'] = extract_contact_info_from_extracted(extracted)
    return extracted


def build_profile(extracted):
    profile = deepcopy(DEFAULT_PROFILE)

    layout = extracted.get('layout') or {}
    if layout.get('page_size'):
        profile['layout']['page_size'] = layout['page_size']
    if layout.get('orientation'):
        profile['layout']['orientation'] = layout['orientation']
    if layout.get('margins_mm'):
        profile['layout']['margins_mm'] = layout['margins_mm']

    body = dict(extracted.get('body') or {})
    colors_used = extracted.get('colors_used') or set()
    fallback_font, fallback_size = guess_from_fonts_used(extracted.get('fonts_used') or {})
    if body.get('font_family') is None and fallback_font:
        body['font_family'] = fallback_font
    if body.get('font_size') is None and fallback_size:
        body['font_size'] = fallback_size
    if body.get('text_color') is None and colors_used:
        body['text_color'] = sorted(colors_used)[0]

    font_family, font_weight = split_font_family_weight(body.get('font_family'))
    if font_family:
        body['font_family'] = font_family
    if body.get('font_weight') is None and font_weight:
        body['font_weight'] = font_weight
    if body.get('font_weight') is None and body.get('font_family'):
        body['font_weight'] = 'Regular'
    if body.get('font_family'):
        profile['typography']['body']['font_family'] = body['font_family']
        profile['typography']['lists']['font_family'] = body['font_family']
        profile['typography']['quote']['font_family'] = body['font_family']
        profile['typography']['table']['font_family'] = body['font_family']
    if body.get('font_weight'):
        profile['typography']['body']['font_weight'] = body['font_weight']
        profile['typography']['lists']['font_weight'] = body['font_weight']
        profile['typography']['quote']['font_weight'] = body['font_weight']
        profile['typography']['table']['font_weight'] = body['font_weight']
    if body.get('font_size'):
        profile['typography']['body']['font_size'] = body['font_size']
        profile['typography']['lists']['font_size'] = body['font_size']
        profile['typography']['quote']['font_size'] = body['font_size']
        profile['typography']['table']['font_size'] = body['font_size']
    if body.get('text_color'):
        profile['typography']['body']['text_color'] = body['text_color']
        profile['typography']['lists']['bullet_color'] = body['text_color']
        profile['typography']['quote']['text_color'] = body['text_color']
        profile['typography']['table']['text_color'] = body['text_color']
    if body.get('line_spacing'):
        profile['typography']['body']['line_spacing'] = body['line_spacing']
        profile['typography']['lists']['line_spacing'] = body['line_spacing']
        profile['typography']['quote']['line_spacing'] = body['line_spacing']
        profile['typography']['table']['line_spacing'] = body['line_spacing']
    if body.get('spacing_before') is not None:
        profile['typography']['body']['paragraph_spacing']['before'] = body['spacing_before']
    if body.get('spacing_after') is not None:
        profile['typography']['body']['paragraph_spacing']['after'] = body['spacing_after']
    if body.get('alignment'):
        profile['typography']['body']['alignment'] = body['alignment']

    headings = extracted.get('headings') or {}
    for key, value in (headings.get('sizes') or {}).items():
        profile['typography']['headings']['sizes'][key] = value
    if headings.get('font_family'):
        profile['typography']['headings']['font_family'] = headings['font_family']
    elif body.get('font_family'):
        profile['typography']['headings']['font_family'] = body['font_family']
    if headings.get('font_weight'):
        profile['typography']['headings']['font_weight'] = headings['font_weight']
    elif body.get('font_weight'):
        profile['typography']['headings']['font_weight'] = body['font_weight']
    if headings.get('color'):
        profile['typography']['headings']['color'] = headings['color']
    elif body.get('text_color'):
        profile['typography']['headings']['color'] = body['text_color']
    for key, value in (headings.get('spacing_before') or {}).items():
        profile['typography']['headings']['spacing_before'][key] = value
    for key, value in (headings.get('spacing_after') or {}).items():
        profile['typography']['headings']['spacing_after'][key] = value
    for key, value in (headings.get('line_spacing') or {}).items():
        profile['typography']['headings']['line_spacing'][key] = value

    header = extracted.get('page_header') or {}
    if header.get('text'):
        profile['page_header']['text'] = header['text']
    if header.get('alignment'):
        profile['page_header']['alignment'] = header['alignment']
    if header.get('font_family'):
        profile['page_header']['font_family'] = header['font_family']
    if header.get('font_size'):
        profile['page_header']['font_size'] = header['font_size']
    if header.get('text_color'):
        profile['page_header']['text_color'] = header['text_color']

    footer = extracted.get('page_footer') or {}
    if footer.get('text'):
        profile['page_footer']['text'] = footer['text']
    if footer.get('alignment'):
        profile['page_footer']['alignment'] = footer['alignment']
    if footer.get('font_family'):
        profile['page_footer']['font_family'] = footer['font_family']
    if footer.get('font_size'):
        profile['page_footer']['font_size'] = footer['font_size']
    if footer.get('text_color'):
        profile['page_footer']['text_color'] = footer['text_color']

    contact = extracted.get('contact_info') or {}
    contact_fields = contact.get('fields') or []
    profile['contact_info']['fields'] = contact_fields
    profile['contact_info']['show'] = bool(contact_fields)
    contact_format = contact.get('format') or {}
    if contact_format.get('alignment'):
        profile['contact_info']['alignment'] = contact_format['alignment']
    if contact_format.get('font_family'):
        profile['contact_info']['font_family'] = contact_format['font_family']
    elif body.get('font_family'):
        profile['contact_info']['font_family'] = body['font_family']
    if contact_format.get('font_size'):
        profile['contact_info']['font_size'] = contact_format['font_size']
    elif body.get('font_size'):
        profile['contact_info']['font_size'] = body['font_size']
    if contact_format.get('text_color'):
        profile['contact_info']['text_color'] = contact_format['text_color']
    elif body.get('text_color'):
        profile['contact_info']['text_color'] = body['text_color']

    fonts_used = extracted.get('fonts_used') or {}
    if isinstance(fonts_used, dict):
        profile['extras']['fonts_used'] = [
            {'name': font, 'sizes': sorted(size for size in sizes if size is not None)}
            for font, sizes in sorted(fonts_used.items())
        ]
    if colors_used:
        profile['extras']['colors_used'] = sorted(colors_used)
    assets = extracted.get('assets') or []
    if assets:
        profile['extras']['assets'] = assets
    logo_files = extracted.get('logo_files') or []
    if logo_files:
        profile['extras']['logo_files'] = logo_files
        profile['page_header']['logo']['show'] = True

    return profile


def flatten(obj, prefix=''):
    rows = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_prefix = '%s.%s' % (prefix, key) if prefix else key
            rows.extend(flatten(value, next_prefix))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            next_prefix = '%s[%d]' % (prefix, idx)
            rows.extend(flatten(value, next_prefix))
    else:
        rows.append((prefix, obj))
    return rows


def write_output(profile, output_path, fmt):
    if fmt == 'json':
        with open(output_path, 'w', encoding='utf-8') as handle:
            json.dump(profile, handle, indent=2, ensure_ascii=True)
        return
    if fmt == 'xlsx':
        try:
            import openpyxl
        except ImportError:
            raise SystemExit('openpyxl is required for xlsx output. Install with: pip install openpyxl')
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'branding_profile'
        ws.append(['key', 'value'])
        for key, value in flatten(profile):
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=True)
            ws.append([key, value])
        wb.save(output_path)
        return
    raise SystemExit('Unsupported format: %s' % fmt)


def main():
    parser = argparse.ArgumentParser(description='Extract branding profile from DOCX or PDF.')
    parser.add_argument('input_path', help='Path to .docx or .pdf')
    parser.add_argument('--output', help='Output filename (extension set by --format).')
    parser.add_argument('--format', default='json', choices=['json', 'xlsx'], help='Output format')
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.exists():
        raise SystemExit('Input file not found: %s' % input_path)

    fmt = args.format
    results_dir = Path('results')
    results_dir.mkdir(parents=True, exist_ok=True)
    if args.output:
        output_stem = Path(args.output).stem
    else:
        output_stem = input_path.stem + '.branding'
    output_path = results_dir / (output_stem + '.' + fmt)

    suffix = input_path.suffix.lower()
    if suffix == '.docx':
        extracted = build_extracted_from_docx(str(input_path), results_dir=results_dir)
    elif suffix == '.pdf':
        extracted = build_extracted_from_pdf(str(input_path))
    else:
        raise SystemExit('Unsupported input type: %s' % suffix)

    profile = build_profile(extracted)
    write_output(profile, str(output_path), fmt)
    print('Wrote %s' % output_path)


if __name__ == '__main__':
    main()
