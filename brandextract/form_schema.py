"""Declarative description of the branding profile editor.

One entry per field. The template renders these generically and `app.js` binds
each input to the profile via its `data-path`, so adding a field is a one-liner.
"""

ALIGNMENTS = ['left', 'center', 'right', 'justify', 'both']
H_ALIGNS = ['left', 'center', 'right']
FONT_WEIGHTS = ['Thin', 'ExtraLight', 'Light', 'Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold', 'Black']
PAGE_SIZES = ['A4', 'A3', 'A5', 'Letter', 'Legal']
ORIENTATIONS = ['portrait', 'landscape']
CONTACT_POSITIONS = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
LEVELS = ['h1', 'h2', 'h3', 'h4']


def _text(path, label, **kwargs):
    return dict(path=path, label=label, type='text', **kwargs)


def _number(path, label, **kwargs):
    return dict(path=path, label=label, type='number', **kwargs)


def _color(path, label, **kwargs):
    return dict(path=path, label=label, type='color', **kwargs)


def _checkbox(path, label, **kwargs):
    return dict(path=path, label=label, type='checkbox', **kwargs)


def _select(path, label, options, **kwargs):
    return dict(path=path, label=label, type='select', options=options, **kwargs)


def _per_level(path, label, value_type='number'):
    return dict(path=path, label=label, type='per_level', value_type=value_type, levels=LEVELS)


TABS = [
    {
        'key': 'typografie',
        'label': 'Typografie',
        'sections': [
            {
                'title': 'Body',
                'fields': [
                    _text('typography.body.font_family', 'Font'),
                    _select('typography.body.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _number('typography.body.font_size', 'Grootte (pt)'),
                    _color('typography.body.text_color', 'Kleur'),
                    _number('typography.body.line_spacing', 'Regelafstand'),
                    _select('typography.body.alignment', 'Uitlijning', ALIGNMENTS),
                    _number('typography.body.paragraph_spacing.before', 'Alinea vóór (pt)'),
                    _number('typography.body.paragraph_spacing.after', 'Alinea na (pt)'),
                ],
            },
            {
                'title': 'Lijsten',
                'fields': [
                    _text('typography.lists.font_family', 'Font'),
                    _select('typography.lists.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _number('typography.lists.font_size', 'Grootte (pt)'),
                    _color('typography.lists.bullet_color', 'Bullet kleur'),
                    _number('typography.lists.indent_mm', 'Inspringing (mm)'),
                    _number('typography.lists.bullet_indent_adjust_mm', 'Bullet inspring (mm)'),
                    _number('typography.lists.line_spacing', 'Regelafstand'),
                    _number('typography.lists.spacing_between_items', 'Ruimte tussen items'),
                ],
            },
            {
                'title': 'Citaat',
                'fields': [
                    _text('typography.quote.font_family', 'Font'),
                    _select('typography.quote.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _number('typography.quote.font_size', 'Grootte (pt)'),
                    _color('typography.quote.text_color', 'Tekstkleur'),
                    _color('typography.quote.border_color', 'Randkleur'),
                    _color('typography.quote.background_color', 'Achtergrond'),
                    _number('typography.quote.padding_mm', 'Opvulling (mm)'),
                    _number('typography.quote.line_spacing', 'Regelafstand'),
                ],
            },
            {
                'title': 'Tabel',
                'fields': [
                    _text('typography.table.font_family', 'Font'),
                    _select('typography.table.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _number('typography.table.font_size', 'Grootte (pt)'),
                    _color('typography.table.text_color', 'Tekstkleur'),
                    _color('typography.table.border_color', 'Randkleur'),
                    _number('typography.table.border_width', 'Randbreedte (pt)'),
                    _number('typography.table.cell_padding_mm', 'Celopvulling (mm)'),
                    _number('typography.table.line_spacing', 'Regelafstand'),
                    _color('typography.table.header_text_color', 'Koptekstkleur'),
                    _select('typography.table.header_font_weight', 'Koptekst gewicht', FONT_WEIGHTS),
                    _color('typography.table.header_background_color', 'Koptekst achtergrond'),
                    _color('typography.table.alternate_row_color', 'Afwiss. rij kleur'),
                ],
            },
        ],
    },
    {
        'key': 'koppen',
        'label': 'Koppen',
        'sections': [
            {
                'title': 'Algemeen',
                'fields': [
                    _text('typography.headings.font_family', 'Font'),
                    _select('typography.headings.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _color('typography.headings.color', 'Kleur'),
                    _number('typography.headings.padding_mm', 'Opvulling (mm)'),
                    _color('typography.headings.divider_color', 'Scheidingslijn kleur'),
                    _checkbox('typography.headings.show_divider_for_h1', 'Lijn bij H1'),
                ],
            },
            {
                'title': 'Per niveau',
                'fields': [
                    _per_level('typography.headings.sizes', 'Grootte (pt)'),
                    _per_level('typography.headings.line_spacing', 'Regelafstand'),
                    _per_level('typography.headings.spacing_before', 'Ruimte voor (pt)'),
                    _per_level('typography.headings.spacing_after', 'Ruimte na (pt)'),
                    _per_level('typography.headings.colors', 'Kleur', value_type='color'),
                ],
            },
        ],
    },
    {
        'key': 'opmaak',
        'label': 'Opmaak',
        'sections': [
            {
                'title': 'Pagina',
                'fields': [
                    _select('layout.page_size', 'Formaat', PAGE_SIZES),
                    _select('layout.orientation', 'Oriëntatie', ORIENTATIONS),
                ],
            },
            {
                'title': 'Marges (mm)',
                'fields': [
                    _number('layout.margins_mm.top', 'Boven'),
                    _number('layout.margins_mm.bottom', 'Onder'),
                    _number('layout.margins_mm.left', 'Links'),
                    _number('layout.margins_mm.right', 'Rechts'),
                ],
            },
        ],
    },
    {
        'key': 'omslagpagina',
        'label': 'Omslagpagina',
        'sections': [
            {
                'title': 'Algemeen',
                'fields': [
                    _checkbox('cover_page.enabled', 'Ingeschakeld'),
                    _checkbox('cover_page.show_logo', 'Logo tonen'),
                    _select('cover_page.alignment', 'Uitlijning', ALIGNMENTS),
                    _color('cover_page.background_color', 'Achtergrond'),
                ],
            },
            {
                'title': 'Titel',
                'fields': [
                    _text('cover_page.title', 'Tekst', placeholder='{{document_title}}'),
                    _color('cover_page.title_color', 'Kleur'),
                    _number('cover_page.title_font_size', 'Grootte (pt)'),
                ],
            },
            {
                'title': 'Subtitel',
                'fields': [
                    _text('cover_page.subtitle', 'Tekst', placeholder='{{organization_name}}'),
                    _color('cover_page.subtitle_color', 'Kleur'),
                    _number('cover_page.subtitle_font_size', 'Grootte (pt)'),
                ],
            },
            {
                'title': 'Meta',
                'fields': [
                    _color('cover_page.meta_color', 'Kleur'),
                    _number('cover_page.meta_font_size', 'Grootte (pt)'),
                    {'path': 'cover_page.meta', 'label': 'Items', 'type': 'meta_items'},
                ],
            },
            {
                'title': 'Scheidingslijn',
                'fields': [
                    _checkbox('cover_page.divider.show', 'Tonen'),
                    _color('cover_page.divider.color', 'Kleur'),
                    _number('cover_page.divider.thickness', 'Dikte (pt)'),
                    _number('cover_page.divider.width_ratio', 'Breedte ratio'),
                ],
            },
            {
                'title': 'Ruimte (pt)',
                'fields': [
                    _number('cover_page.spacing.before_title', 'Voor titel'),
                    _number('cover_page.spacing.after_title', 'Na titel'),
                    _number('cover_page.spacing.after_subtitle', 'Na subtitel'),
                    _number('cover_page.spacing.after_meta', 'Na meta'),
                ],
            },
        ],
    },
    {
        'key': 'header-footer',
        'label': 'Header/Footer',
        'sections': [
            {
                'title': 'Header',
                'fields': [
                    _text('page_header.text', 'Tekst'),
                    _text('page_header.font_family', 'Font'),
                    _select('page_header.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _number('page_header.font_size', 'Grootte (pt)'),
                    _color('page_header.text_color', 'Kleur'),
                    _select('page_header.alignment', 'Uitlijning', H_ALIGNS),
                    _checkbox('page_header.show_on_cover', 'Tonen op omslag'),
                ],
            },
            {
                'title': 'Logo',
                'fields': [
                    _checkbox('page_header.logo.show', 'Tonen'),
                    _select('page_header.logo.position', 'Positie', H_ALIGNS),
                    _number('page_header.logo.max_width_mm', 'Max breedte (mm)'),
                    _number('page_header.logo.max_height_mm', 'Max hoogte (mm)'),
                ],
            },
            {
                'title': 'Footer',
                'fields': [
                    _text('page_footer.text', 'Tekst'),
                    _text('page_footer.font_family', 'Font'),
                    _select('page_footer.font_weight', 'Gewicht', FONT_WEIGHTS),
                    _number('page_footer.font_size', 'Grootte (pt)'),
                    _color('page_footer.text_color', 'Kleur'),
                    _select('page_footer.alignment', 'Uitlijning', H_ALIGNS),
                    _checkbox('page_footer.show_on_cover', 'Tonen op omslag'),
                    _checkbox('page_footer.show_page_numbers', 'Paginanummers'),
                ],
            },
        ],
    },
    {
        'key': 'contact',
        'label': 'Contact',
        'sections': [
            {
                'title': None,
                'fields': [
                    _checkbox('contact_info.show', 'Tonen'),
                    _select('contact_info.position', 'Positie', CONTACT_POSITIONS),
                    _select('contact_info.alignment', 'Uitlijning', H_ALIGNS),
                    _text('contact_info.font_family', 'Font'),
                    _number('contact_info.font_size', 'Grootte (pt)'),
                    _color('contact_info.text_color', 'Kleur'),
                    _number('contact_info.line_spacing', 'Regelafstand'),
                    {
                        'path': 'contact_info.fields',
                        'label': 'Regels',
                        'type': 'string_list',
                        'placeholder': 'Één item per regel',
                    },
                ],
            },
        ],
    },
    {
        'key': 'extras',
        'label': 'Extras',
        'sections': [
            {
                'title': 'Disclaimer',
                'fields': [
                    _checkbox('extras.disclaimer.enabled', 'Ingeschakeld'),
                    dict(path='extras.disclaimer.text', label='Tekst', type='textarea'),
                    _select('extras.disclaimer.alignment', 'Uitlijning', ALIGNMENTS),
                ],
            },
            {
                'title': 'Kleuren gebruikt',
                'fields': [
                    {'path': 'extras.colors_used', 'type': 'swatches'},
                ],
            },
            {
                'title': 'Lettertypen gebruikt',
                'fields': [
                    {'path': 'extras.fonts_used', 'type': 'fonts'},
                ],
            },
        ],
    },
    {
        'key': 'assets',
        'label': 'Assets',
        'sections': [
            {
                'title': 'Template bestand',
                'fields': [
                    _text('template_file.asset_slug', 'Asset slug', placeholder='template-file'),
                ],
            },
            {
                'title': 'Assets',
                'count_path': 'extras.assets',
                'fields': [
                    {'path': 'extras.assets', 'type': 'assets'},
                ],
            },
        ],
    },
]
