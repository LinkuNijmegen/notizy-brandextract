import { useState, useCallback, useEffect } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { oneDark } from '@codemirror/theme-one-dark'
import './App.css'

const STORAGE_KEY = 'docx-extract-last-result'

// ── Utilities ─────────────────────────────────────────────────────────────────

function setDeep(obj, path, value) {
  if (path.length === 0) return value
  const [head, ...rest] = path
  if (Array.isArray(obj)) {
    const idx = parseInt(head, 10)
    const next = [...obj]
    next[idx] = rest.length === 0 ? value : setDeep(next[idx] || {}, rest, value)
    return next
  }
  return {
    ...obj,
    [head]: rest.length === 0 ? value : setDeep(obj?.[head] ?? {}, rest, value),
  }
}

const ALIGNMENTS = ['left', 'center', 'right', 'justify', 'both']
const H_ALIGNS = ['left', 'center', 'right']
const FONT_WEIGHTS = ['Thin', 'ExtraLight', 'Light', 'Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold', 'Black']
const LEVELS = ['h1', 'h2', 'h3', 'h4']

// ── Field primitives ──────────────────────────────────────────────────────────

function SectionTitle({ children }) {
  return <h4 className="form-section-title">{children}</h4>
}

function Field({ label, value, onChange, type = 'text', options, placeholder }) {
  if (type === 'checkbox') {
    return (
      <div className="field-row">
        <label className="field-label">{label}</label>
        <label className="field-toggle">
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span className="toggle-track" />
          <span className="toggle-hint">{value ? 'Aan' : 'Uit'}</span>
        </label>
      </div>
    )
  }

  if (type === 'color') {
    const display = value || ''
    const pickerVal = /^#[0-9a-fA-F]{6}$/i.test(display) ? display : '#000000'
    return (
      <div className="field-row">
        <label className="field-label">{label}</label>
        <div className="field-color">
          <input
            type="color"
            value={pickerVal}
            onChange={(e) => onChange(e.target.value)}
            className="field-color-picker"
          />
          <input
            type="text"
            value={display}
            onChange={(e) => onChange(e.target.value || null)}
            className="field-input field-color-text"
            placeholder="null"
          />
        </div>
      </div>
    )
  }

  if (type === 'select') {
    return (
      <div className="field-row">
        <label className="field-label">{label}</label>
        <select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
          className="field-input"
        >
          {options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </div>
    )
  }

  if (type === 'textarea') {
    return (
      <div className="field-row field-row--top">
        <label className="field-label">{label}</label>
        <textarea
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
          className="field-input field-textarea"
          rows={3}
          placeholder={placeholder}
        />
      </div>
    )
  }

  return (
    <div className="field-row">
      <label className="field-label">{label}</label>
      <input
        type={type}
        value={value ?? ''}
        onChange={(e) =>
          onChange(
            type === 'number'
              ? e.target.value === '' ? null : parseFloat(e.target.value)
              : e.target.value
          )
        }
        className="field-input"
        step={type === 'number' ? 'any' : undefined}
        placeholder={placeholder}
      />
    </div>
  )
}

// Per-level grid: h1 / h2 / h3 / h4 in one row per key
function PerLevelField({ label, value, onChange, type = 'number' }) {
  const obj = value || {}
  const set = (key) => (val) => onChange({ ...obj, [key]: val })

  return (
    <div className="field-row per-level-row">
      <label className="field-label">{label}</label>
      <div className="per-level-grid">
        {LEVELS.map((k) => (
          <div key={k} className="per-level-cell">
            <span className="per-level-key">{k.toUpperCase()}</span>
            {type === 'color' ? (
              <input
                type="color"
                value={/^#[0-9a-fA-F]{6}$/i.test(obj[k] || '') ? obj[k] : '#000000'}
                onChange={(e) => set(k)(e.target.value)}
                className="per-level-color"
                title={obj[k] || ''}
              />
            ) : (
              <input
                type="number"
                value={obj[k] ?? ''}
                onChange={(e) => set(k)(e.target.value === '' ? null : parseFloat(e.target.value))}
                className="per-level-input"
                step="any"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Editable list of {label, value} objects (cover_page.meta)
function MetaItemsField({ value, onChange }) {
  const items = value || []
  const setItem = (i, key) => (val) => {
    const next = items.map((item, idx) => (idx === i ? { ...item, [key]: val } : item))
    onChange(next)
  }
  const addItem = () => onChange([...items, { label: '', value: '' }])
  const removeItem = (i) => onChange(items.filter((_, idx) => idx !== i))

  return (
    <div className="meta-items">
      {items.map((item, i) => (
        <div key={i} className="meta-item-row">
          <input
            className="field-input"
            value={item.label || ''}
            onChange={(e) => setItem(i, 'label')(e.target.value)}
            placeholder="Label"
          />
          <input
            className="field-input"
            value={item.value || ''}
            onChange={(e) => setItem(i, 'value')(e.target.value)}
            placeholder="Waarde"
          />
          <button type="button" className="btn-remove" onClick={() => removeItem(i)} title="Verwijder">×</button>
        </div>
      ))}
      <button type="button" className="btn-add-item" onClick={addItem}>+ Rij toevoegen</button>
    </div>
  )
}

// Editable list of strings (contact_info.fields)
function StringListField({ label, value, onChange }) {
  return (
    <div className="field-row field-row--top">
      <label className="field-label">{label}</label>
      <textarea
        className="field-input field-textarea"
        value={(value || []).join('\n')}
        onChange={(e) =>
          onChange(e.target.value ? e.target.value.split('\n') : [])
        }
        rows={5}
        placeholder="Één item per regel"
      />
    </div>
  )
}

// Readonly color swatches
function ColorSwatches({ colors }) {
  if (!colors?.length) return <p className="empty">Geen kleuren</p>
  return (
    <div className="swatch-grid">
      {colors.map((c) => (
        <div key={c} className="color-swatch" title={c}>
          <div className="swatch-block" style={{ background: c }} />
          <span className="swatch-label">{c}</span>
        </div>
      ))}
    </div>
  )
}

// Readonly font badges
function FontBadges({ fonts }) {
  if (!fonts?.length) return <p className="empty">Geen lettertypen</p>
  return (
    <div className="font-grid">
      {fonts.map((f) => (
        <div key={f.name} className="font-badge">
          <span className="font-name">{f.name}</span>
          {f.sizes?.length > 0 && (
            <span className="font-sizes">{f.sizes.join(', ')} pt</span>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Tab components ────────────────────────────────────────────────────────────

function TypografieTab({ profile, update }) {
  const body = profile?.typography?.body || {}
  const lists = profile?.typography?.lists || {}
  const quote = profile?.typography?.quote || {}
  const table = profile?.typography?.table || {}

  return (
    <div className="form-tab-content">
      <SectionTitle>Body</SectionTitle>
      <Field label="Font" value={body.font_family} onChange={update('typography', 'body', 'font_family')} />
      <Field label="Gewicht" value={body.font_weight} onChange={update('typography', 'body', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Grootte (pt)" value={body.font_size} onChange={update('typography', 'body', 'font_size')} type="number" />
      <Field label="Kleur" value={body.text_color} onChange={update('typography', 'body', 'text_color')} type="color" />
      <Field label="Regelafstand" value={body.line_spacing} onChange={update('typography', 'body', 'line_spacing')} type="number" />
      <Field label="Uitlijning" value={body.alignment} onChange={update('typography', 'body', 'alignment')} type="select" options={ALIGNMENTS} />
      <Field label="Alinea vóór (pt)" value={body.paragraph_spacing?.before} onChange={update('typography', 'body', 'paragraph_spacing', 'before')} type="number" />
      <Field label="Alinea na (pt)" value={body.paragraph_spacing?.after} onChange={update('typography', 'body', 'paragraph_spacing', 'after')} type="number" />

      <SectionTitle>Lijsten</SectionTitle>
      <Field label="Font" value={lists.font_family} onChange={update('typography', 'lists', 'font_family')} />
      <Field label="Gewicht" value={lists.font_weight} onChange={update('typography', 'lists', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Grootte (pt)" value={lists.font_size} onChange={update('typography', 'lists', 'font_size')} type="number" />
      <Field label="Bullet kleur" value={lists.bullet_color} onChange={update('typography', 'lists', 'bullet_color')} type="color" />
      <Field label="Inspringing (mm)" value={lists.indent_mm} onChange={update('typography', 'lists', 'indent_mm')} type="number" />
      <Field label="Bullet inspring (mm)" value={lists.bullet_indent_adjust_mm} onChange={update('typography', 'lists', 'bullet_indent_adjust_mm')} type="number" />
      <Field label="Regelafstand" value={lists.line_spacing} onChange={update('typography', 'lists', 'line_spacing')} type="number" />
      <Field label="Ruimte tussen items" value={lists.spacing_between_items} onChange={update('typography', 'lists', 'spacing_between_items')} type="number" />

      <SectionTitle>Citaat</SectionTitle>
      <Field label="Font" value={quote.font_family} onChange={update('typography', 'quote', 'font_family')} />
      <Field label="Gewicht" value={quote.font_weight} onChange={update('typography', 'quote', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Grootte (pt)" value={quote.font_size} onChange={update('typography', 'quote', 'font_size')} type="number" />
      <Field label="Tekstkleur" value={quote.text_color} onChange={update('typography', 'quote', 'text_color')} type="color" />
      <Field label="Randkleur" value={quote.border_color} onChange={update('typography', 'quote', 'border_color')} type="color" />
      <Field label="Achtergrond" value={quote.background_color} onChange={update('typography', 'quote', 'background_color')} type="color" />
      <Field label="Opvulling (mm)" value={quote.padding_mm} onChange={update('typography', 'quote', 'padding_mm')} type="number" />
      <Field label="Regelafstand" value={quote.line_spacing} onChange={update('typography', 'quote', 'line_spacing')} type="number" />

      <SectionTitle>Tabel</SectionTitle>
      <Field label="Font" value={table.font_family} onChange={update('typography', 'table', 'font_family')} />
      <Field label="Gewicht" value={table.font_weight} onChange={update('typography', 'table', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Grootte (pt)" value={table.font_size} onChange={update('typography', 'table', 'font_size')} type="number" />
      <Field label="Tekstkleur" value={table.text_color} onChange={update('typography', 'table', 'text_color')} type="color" />
      <Field label="Randkleur" value={table.border_color} onChange={update('typography', 'table', 'border_color')} type="color" />
      <Field label="Randbreedte (pt)" value={table.border_width} onChange={update('typography', 'table', 'border_width')} type="number" />
      <Field label="Celopvulling (mm)" value={table.cell_padding_mm} onChange={update('typography', 'table', 'cell_padding_mm')} type="number" />
      <Field label="Regelafstand" value={table.line_spacing} onChange={update('typography', 'table', 'line_spacing')} type="number" />
      <Field label="Koptekstkleur" value={table.header_text_color} onChange={update('typography', 'table', 'header_text_color')} type="color" />
      <Field label="Koptekst gewicht" value={table.header_font_weight} onChange={update('typography', 'table', 'header_font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Koptekst achtergrond" value={table.header_background_color} onChange={update('typography', 'table', 'header_background_color')} type="color" />
      <Field label="Afwiss. rij kleur" value={table.alternate_row_color} onChange={update('typography', 'table', 'alternate_row_color')} type="color" />
    </div>
  )
}

function KoppenTab({ profile, update }) {
  const h = profile?.typography?.headings || {}

  return (
    <div className="form-tab-content">
      <SectionTitle>Algemeen</SectionTitle>
      <Field label="Font" value={h.font_family} onChange={update('typography', 'headings', 'font_family')} />
      <Field label="Gewicht" value={h.font_weight} onChange={update('typography', 'headings', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Kleur" value={h.color} onChange={update('typography', 'headings', 'color')} type="color" />
      <Field label="Opvulling (mm)" value={h.padding_mm} onChange={update('typography', 'headings', 'padding_mm')} type="number" />
      <Field label="Scheidingslijn kleur" value={h.divider_color} onChange={update('typography', 'headings', 'divider_color')} type="color" />
      <Field label="Lijn bij H1" value={h.show_divider_for_h1} onChange={update('typography', 'headings', 'show_divider_for_h1')} type="checkbox" />

      <SectionTitle>Per niveau</SectionTitle>
      <PerLevelField label="Grootte (pt)" value={h.sizes} onChange={update('typography', 'headings', 'sizes')} type="number" />
      <PerLevelField label="Regelafstand" value={h.line_spacing} onChange={update('typography', 'headings', 'line_spacing')} type="number" />
      <PerLevelField label="Ruimte voor (pt)" value={h.spacing_before} onChange={update('typography', 'headings', 'spacing_before')} type="number" />
      <PerLevelField label="Ruimte na (pt)" value={h.spacing_after} onChange={update('typography', 'headings', 'spacing_after')} type="number" />
      <PerLevelField label="Kleur" value={h.colors} onChange={update('typography', 'headings', 'colors')} type="color" />
    </div>
  )
}

function OpmaakTab({ profile, update }) {
  const layout = profile?.layout || {}
  const margins = layout.margins_mm || {}

  return (
    <div className="form-tab-content">
      <SectionTitle>Pagina</SectionTitle>
      <Field label="Formaat" value={layout.page_size} onChange={update('layout', 'page_size')} type="select" options={['A4', 'A3', 'A5', 'Letter', 'Legal']} />
      <Field label="Oriëntatie" value={layout.orientation} onChange={update('layout', 'orientation')} type="select" options={['portrait', 'landscape']} />

      <SectionTitle>Marges (mm)</SectionTitle>
      <Field label="Boven" value={margins.top} onChange={update('layout', 'margins_mm', 'top')} type="number" />
      <Field label="Onder" value={margins.bottom} onChange={update('layout', 'margins_mm', 'bottom')} type="number" />
      <Field label="Links" value={margins.left} onChange={update('layout', 'margins_mm', 'left')} type="number" />
      <Field label="Rechts" value={margins.right} onChange={update('layout', 'margins_mm', 'right')} type="number" />
    </div>
  )
}

function OmslagpaginaTab({ profile, update }) {
  const cp = profile?.cover_page || {}
  const divider = cp.divider || {}
  const spacing = cp.spacing || {}

  return (
    <div className="form-tab-content">
      <SectionTitle>Algemeen</SectionTitle>
      <Field label="Ingeschakeld" value={cp.enabled} onChange={update('cover_page', 'enabled')} type="checkbox" />
      <Field label="Logo tonen" value={cp.show_logo} onChange={update('cover_page', 'show_logo')} type="checkbox" />
      <Field label="Uitlijning" value={cp.alignment} onChange={update('cover_page', 'alignment')} type="select" options={ALIGNMENTS} />
      <Field label="Achtergrond" value={cp.background_color} onChange={update('cover_page', 'background_color')} type="color" />

      <SectionTitle>Titel</SectionTitle>
      <Field label="Tekst" value={cp.title} onChange={update('cover_page', 'title')} placeholder="{{document_title}}" />
      <Field label="Kleur" value={cp.title_color} onChange={update('cover_page', 'title_color')} type="color" />
      <Field label="Grootte (pt)" value={cp.title_font_size} onChange={update('cover_page', 'title_font_size')} type="number" />

      <SectionTitle>Subtitel</SectionTitle>
      <Field label="Tekst" value={cp.subtitle} onChange={update('cover_page', 'subtitle')} placeholder="{{organization_name}}" />
      <Field label="Kleur" value={cp.subtitle_color} onChange={update('cover_page', 'subtitle_color')} type="color" />
      <Field label="Grootte (pt)" value={cp.subtitle_font_size} onChange={update('cover_page', 'subtitle_font_size')} type="number" />

      <SectionTitle>Meta</SectionTitle>
      <Field label="Kleur" value={cp.meta_color} onChange={update('cover_page', 'meta_color')} type="color" />
      <Field label="Grootte (pt)" value={cp.meta_font_size} onChange={update('cover_page', 'meta_font_size')} type="number" />
      <div className="field-label-standalone">Items</div>
      <MetaItemsField value={cp.meta} onChange={update('cover_page', 'meta')} />

      <SectionTitle>Scheidingslijn</SectionTitle>
      <Field label="Tonen" value={divider.show} onChange={update('cover_page', 'divider', 'show')} type="checkbox" />
      <Field label="Kleur" value={divider.color} onChange={update('cover_page', 'divider', 'color')} type="color" />
      <Field label="Dikte (pt)" value={divider.thickness} onChange={update('cover_page', 'divider', 'thickness')} type="number" />
      <Field label="Breedte ratio" value={divider.width_ratio} onChange={update('cover_page', 'divider', 'width_ratio')} type="number" />

      <SectionTitle>Ruimte (pt)</SectionTitle>
      <Field label="Voor titel" value={spacing.before_title} onChange={update('cover_page', 'spacing', 'before_title')} type="number" />
      <Field label="Na titel" value={spacing.after_title} onChange={update('cover_page', 'spacing', 'after_title')} type="number" />
      <Field label="Na subtitel" value={spacing.after_subtitle} onChange={update('cover_page', 'spacing', 'after_subtitle')} type="number" />
      <Field label="Na meta" value={spacing.after_meta} onChange={update('cover_page', 'spacing', 'after_meta')} type="number" />
    </div>
  )
}

function HeaderFooterTab({ profile, update }) {
  const header = profile?.page_header || {}
  const logo = header.logo || {}
  const footer = profile?.page_footer || {}

  return (
    <div className="form-tab-content">
      <SectionTitle>Header</SectionTitle>
      <Field label="Tekst" value={header.text} onChange={update('page_header', 'text')} />
      <Field label="Font" value={header.font_family} onChange={update('page_header', 'font_family')} />
      <Field label="Gewicht" value={header.font_weight} onChange={update('page_header', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Grootte (pt)" value={header.font_size} onChange={update('page_header', 'font_size')} type="number" />
      <Field label="Kleur" value={header.text_color} onChange={update('page_header', 'text_color')} type="color" />
      <Field label="Uitlijning" value={header.alignment} onChange={update('page_header', 'alignment')} type="select" options={H_ALIGNS} />
      <Field label="Tonen op omslag" value={header.show_on_cover} onChange={update('page_header', 'show_on_cover')} type="checkbox" />

      <SectionTitle>Logo</SectionTitle>
      <Field label="Tonen" value={logo.show} onChange={update('page_header', 'logo', 'show')} type="checkbox" />
      <Field label="Positie" value={logo.position} onChange={update('page_header', 'logo', 'position')} type="select" options={H_ALIGNS} />
      <Field label="Max breedte (mm)" value={logo.max_width_mm} onChange={update('page_header', 'logo', 'max_width_mm')} type="number" />
      <Field label="Max hoogte (mm)" value={logo.max_height_mm} onChange={update('page_header', 'logo', 'max_height_mm')} type="number" />

      <SectionTitle>Footer</SectionTitle>
      <Field label="Tekst" value={footer.text} onChange={update('page_footer', 'text')} />
      <Field label="Font" value={footer.font_family} onChange={update('page_footer', 'font_family')} />
      <Field label="Gewicht" value={footer.font_weight} onChange={update('page_footer', 'font_weight')} type="select" options={FONT_WEIGHTS} />
      <Field label="Grootte (pt)" value={footer.font_size} onChange={update('page_footer', 'font_size')} type="number" />
      <Field label="Kleur" value={footer.text_color} onChange={update('page_footer', 'text_color')} type="color" />
      <Field label="Uitlijning" value={footer.alignment} onChange={update('page_footer', 'alignment')} type="select" options={H_ALIGNS} />
      <Field label="Tonen op omslag" value={footer.show_on_cover} onChange={update('page_footer', 'show_on_cover')} type="checkbox" />
      <Field label="Paginanummers" value={footer.show_page_numbers} onChange={update('page_footer', 'show_page_numbers')} type="checkbox" />
    </div>
  )
}

function ContactTab({ profile, update }) {
  const ci = profile?.contact_info || {}

  return (
    <div className="form-tab-content">
      <Field label="Tonen" value={ci.show} onChange={update('contact_info', 'show')} type="checkbox" />
      <Field label="Positie" value={ci.position} onChange={update('contact_info', 'position')} type="select" options={['top_left', 'top_right', 'bottom_left', 'bottom_right']} />
      <Field label="Uitlijning" value={ci.alignment} onChange={update('contact_info', 'alignment')} type="select" options={H_ALIGNS} />
      <Field label="Font" value={ci.font_family} onChange={update('contact_info', 'font_family')} />
      <Field label="Grootte (pt)" value={ci.font_size} onChange={update('contact_info', 'font_size')} type="number" />
      <Field label="Kleur" value={ci.text_color} onChange={update('contact_info', 'text_color')} type="color" />
      <Field label="Regelafstand" value={ci.line_spacing} onChange={update('contact_info', 'line_spacing')} type="number" />
      <StringListField label="Regels" value={ci.fields} onChange={update('contact_info', 'fields')} />
    </div>
  )
}

function ExtrasTab({ profile, update }) {
  const extras = profile?.extras || {}
  const disclaimer = extras.disclaimer || {}

  return (
    <div className="form-tab-content">
      <SectionTitle>Disclaimer</SectionTitle>
      <Field label="Ingeschakeld" value={disclaimer.enabled} onChange={update('extras', 'disclaimer', 'enabled')} type="checkbox" />
      <Field label="Tekst" value={disclaimer.text} onChange={update('extras', 'disclaimer', 'text')} type="textarea" />
      <Field label="Uitlijning" value={disclaimer.alignment} onChange={update('extras', 'disclaimer', 'alignment')} type="select" options={ALIGNMENTS} />

      <SectionTitle>Kleuren gebruikt</SectionTitle>
      <ColorSwatches colors={extras.colors_used} />

      <SectionTitle>Lettertypen gebruikt</SectionTitle>
      <FontBadges fonts={extras.fonts_used} />
    </div>
  )
}

function AssetsTab({ profile, update }) {
  const assets = profile?.extras?.assets || []
  const templateSlug = profile?.template_file?.asset_slug ?? ''
  const isImage = (f) => /\.(png|jpg|jpeg|gif|svg|webp|emf|wmf)$/i.test(f)

  return (
    <div className="form-tab-content">
      <SectionTitle>Template bestand</SectionTitle>
      <Field
        label="Asset slug"
        value={templateSlug}
        onChange={(val) => update('template_file', 'asset_slug')(val || null)}
        placeholder="template-file"
      />

      <SectionTitle>Assets ({assets.length})</SectionTitle>
      {assets.length === 0 ? (
        <p className="empty">Geen assets gevonden</p>
      ) : (
        <div className="asset-grid">
          {assets.map((asset) => (
            <div key={asset.slug} className="asset-card">
              <div className="asset-file-icon">
                {isImage(asset.filename) ? '🖼️' : '📄'}
              </div>
              <div className="asset-info">
                <span className="asset-slug">{asset.slug}</span>
                <span className="asset-filename">{asset.filename}</span>
                <span className="asset-source">{(asset.sources || []).join(', ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Profile form (right panel) ────────────────────────────────────────────────

const TABS = [
  { key: 'typografie', label: 'Typografie' },
  { key: 'koppen', label: 'Koppen' },
  { key: 'opmaak', label: 'Opmaak' },
  { key: 'omslagpagina', label: 'Omslagpagina' },
  { key: 'header-footer', label: 'Header/Footer' },
  { key: 'contact', label: 'Contact' },
  { key: 'extras', label: 'Extras' },
  { key: 'assets', label: 'Assets' },
]

function ProfileForm({ profile, onChange }) {
  const [tab, setTab] = useState('typografie')
  const update = (...path) => (value) => onChange(setDeep(profile, path, value))

  return (
    <div className="form-panel">
      <div className="panel-header">
        <div className="form-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`form-tab ${tab === t.key ? 'active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div className="form-scroll">
        {tab === 'typografie'    && <TypografieTab    profile={profile} update={update} />}
        {tab === 'koppen'        && <KoppenTab        profile={profile} update={update} />}
        {tab === 'opmaak'        && <OpmaakTab        profile={profile} update={update} />}
        {tab === 'omslagpagina'  && <OmslagpaginaTab  profile={profile} update={update} />}
        {tab === 'header-footer' && <HeaderFooterTab  profile={profile} update={update} />}
        {tab === 'contact'       && <ContactTab       profile={profile} update={update} />}
        {tab === 'extras'        && <ExtrasTab        profile={profile} update={update} />}
        {tab === 'assets'        && <AssetsTab        profile={profile} update={update} />}
      </div>
    </div>
  )
}

// ── Profile viewer (split layout) ────────────────────────────────────────────

function ProfileViewer({ result, onReset }) {
  const [profile, setProfile] = useState(result.profile)
  const [jsonText, setJsonText] = useState(JSON.stringify(result.profile, null, 2))
  const [jsonError, setJsonError] = useState(null)
  const documentFilename = result.document_filename || 'document.docx'
  const warnings = result.warnings || []

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ profile, document_filename: documentFilename }))
    } catch {}
  }, [profile])

  const handleFormChange = useCallback((newProfile) => {
    setProfile(newProfile)
    setJsonText(JSON.stringify(newProfile, null, 2))
    setJsonError(null)
  }, [])

  const handleJsonChange = useCallback((text) => {
    setJsonText(text)
    try {
      const parsed = JSON.parse(text)
      setProfile(parsed)
      setJsonError(null)
    } catch (e) {
      setJsonError(e.message)
    }
  }, [])

  const [copied, setCopied] = useState(false)

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(profile, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="viewer">
      <div className="viewer-header">
        <h2>Branding profiel</h2>
        <div className="viewer-actions">
          <button className="btn-secondary" onClick={onReset}>
            Nieuwe extractie
          </button>
          <button className="btn-primary" onClick={copyJson}>
            {copied ? 'Gekopieerd!' : 'Kopieer JSON'}
          </button>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="viewer-warnings">
          {warnings.map((w, i) => <span key={i}>⚠ {w}</span>)}
        </div>
      )}

      <div className="split-view">
        <div className="split-left">
          <div className="panel-header panel-header--dark">JSON</div>
          <CodeMirror
            className="json-editor"
            value={jsonText}
            onChange={handleJsonChange}
            extensions={[json()]}
            theme={oneDark}
            height="100%"
            basicSetup={{
              lineNumbers: false,
              foldGutter: true,
              highlightActiveLine: false,
              highlightActiveLineGutter: false,
            }}
          />
          {jsonError && <div className="json-parse-error">{jsonError}</div>}
        </div>

        <ProfileForm profile={profile} onChange={handleFormChange} />
      </div>
    </div>
  )
}

// ── Upload ────────────────────────────────────────────────────────────────────

function UploadForm({ onResult }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [docFile, setDocFile] = useState(null)
  const [tmplFile, setTmplFile] = useState(null)
  const [tmplError, setTmplError] = useState(null)
  const [tmplChecking, setTmplChecking] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [tmplDragging, setTmplDragging] = useState(false)

  const checkTemplate = async (file) => {
    if (!file) { setTmplFile(null); setTmplError(null); return }
    setTmplChecking(true)
    setTmplError(null)
    const fd = new FormData()
    fd.append('template_docx', file)
    try {
      const res = await fetch('/check-template', { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setTmplError(err.detail || 'Template validatie mislukt, voeg {content} en {{ document_title }} toe.')
        setTmplFile(null)
      } else {
        setTmplFile(file)
      }
    } catch {
      setTmplError('Template validatie mislukt, voeg {content} en {{ document_title }} toe.')
      setTmplFile(null)
    } finally {
      setTmplChecking(false)
    }
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) setDocFile(file)
  }, [])

  const handleTmplDrop = useCallback((e) => {
    e.preventDefault()
    setTmplDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) checkTemplate(file)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!docFile) return
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('document', docFile)
    if (tmplFile) formData.append('template_docx', tmplFile)

    try {
      const res = await fetch('/extract', { method: 'POST', body: formData })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Extractie mislukt')
      }
      onResult(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="upload-container">
      <div className="upload-card">
        <h1>Branding Extractor</h1>
        <p className="subtitle">Upload een DOCX of PDF om branding te extraheren</p>

        <form onSubmit={handleSubmit}>
          <div
            className={`dropzone${dragging ? ' dragging' : ''}${docFile ? ' has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => document.getElementById('doc-input').click()}
          >
            <input
              id="doc-input"
              type="file"
              accept=".docx,.pdf"
              style={{ display: 'none' }}
              onChange={(e) => setDocFile(e.target.files[0])}
            />
            {docFile
              ? <span className="file-name">📄 {docFile.name}</span>
              : <span className="dropzone-hint">Sleep hier een DOCX of PDF<br /><small>of klik om te bladeren</small></span>
            }
          </div>

          <div className="optional-field">
            <label>Template DOCX (optioneel)</label>
            <div
              className={`dropzone dropzone--small${tmplDragging ? ' dragging' : ''}${tmplFile ? ' has-file' : ''}${tmplError ? ' has-error' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setTmplDragging(true) }}
              onDragLeave={() => setTmplDragging(false)}
              onDrop={handleTmplDrop}
              onClick={() => document.getElementById('tmpl-input').click()}
            >
              <input
                id="tmpl-input"
                type="file"
                accept=".docx"
                style={{ display: 'none' }}
                onChange={(e) => checkTemplate(e.target.files[0] || null)}
              />
              {tmplChecking
                ? <span className="dropzone-hint">Controleren…</span>
                : tmplFile
                  ? <span className="file-name">📄 {tmplFile.name}</span>
                  : <span className="dropzone-hint">Sleep DOCX hier of klik<br /><small>optioneel</small></span>
              }
            </div>
          </div>

          {tmplError && <div className="error">{tmplError}</div>}
          {error && <div className="error">{error}</div>}

          <button className="btn-primary btn-full" type="submit" disabled={!docFile || loading || !!tmplError || tmplChecking}>
            {loading ? 'Bezig met extraheren…' : 'Extraheer branding'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [result, setResult] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  const handleResult = (data) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)) } catch {}
    setResult(data)
  }

  const handleReset = () => {
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
    setResult(null)
  }

  return result
    ? <ProfileViewer result={result} onReset={handleReset} />
    : <UploadForm onResult={handleResult} />
}
