(function () {
  'use strict'

  var STORAGE_KEY = 'docx-extract-last-result'
  var HEX_RE = /^#[0-9a-fA-F]{6}$/
  var IMAGE_RE = /\.(png|jpg|jpeg|gif|svg|webp|emf|wmf)$/i

  var profile = null
  var documentFilename = 'document.docx'
  var editor = null
  var syncing = false
  var docFile = null
  var tmplFile = null

  // ── State helpers ───────────────────────────────────────────────────────────

  function getDeep(obj, path) {
    var parts = path.split('.')
    var cur = obj
    for (var i = 0; i < parts.length; i++) {
      if (cur === null || typeof cur !== 'object') return undefined
      cur = cur[parts[i]]
    }
    return cur
  }

  function setDeep(obj, path, value) {
    var parts = path.split('.')
    var cur = obj
    for (var i = 0; i < parts.length - 1; i++) {
      if (cur[parts[i]] === null || typeof cur[parts[i]] !== 'object') cur[parts[i]] = {}
      cur = cur[parts[i]]
    }
    cur[parts[parts.length - 1]] = value
  }

  function profileJson() {
    return JSON.stringify(profile, null, 2)
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        profile: profile,
        document_filename: documentFilename,
      }))
    } catch (e) {}
  }

  // ── Form → state ────────────────────────────────────────────────────────────

  function readInput(el) {
    var type = el.dataset.type
    if (type === 'checkbox') return el.checked
    if (type === 'number') return el.value === '' ? null : parseFloat(el.value)
    if (type === 'string_list') return el.value ? el.value.split('\n') : []
    if (type === 'color') return el.value || null
    return el.value
  }

  function onFormInput(e) {
    var el = e.target
    if (!el.dataset || !el.dataset.path || syncing) return

    var path = el.dataset.path
    var type = el.dataset.type

    if (type === 'color-picker') {
      setDeep(profile, path, el.value)
      var text = document.querySelector('[data-type="color"][data-path="' + path + '"]')
      if (text) text.value = el.value
    } else {
      setDeep(profile, path, readInput(el))
      if (type === 'color') {
        var picker = document.querySelector('[data-type="color-picker"][data-path="' + path + '"]')
        if (picker && HEX_RE.test(el.value)) picker.value = el.value
      }
      if (type === 'checkbox') {
        var hint = el.parentNode.querySelector('.toggle-hint')
        if (hint) hint.textContent = el.checked ? 'Aan' : 'Uit'
      }
    }

    syncEditorFromState()
    persist()
  }

  function syncEditorFromState() {
    syncing = true
    var cursor = editor.getCursor()
    editor.setValue(profileJson())
    editor.setCursor(cursor)
    syncing = false
    setError(null)
  }

  // ── State → form ────────────────────────────────────────────────────────────

  function renderForm() {
    syncing = true

    document.querySelectorAll('[data-path]').forEach(function (el) {
      var type = el.dataset.type
      var value = getDeep(profile, el.dataset.path)

      if (type === 'checkbox') {
        el.checked = !!value
        var hint = el.parentNode.querySelector('.toggle-hint')
        if (hint) hint.textContent = el.checked ? 'Aan' : 'Uit'
      } else if (type === 'color-picker') {
        el.value = HEX_RE.test(value || '') ? value : '#000000'
        el.title = value || ''
      } else if (type === 'string_list') {
        el.value = (value || []).join('\n')
      } else if (type === 'meta_items') {
        renderMetaItems(el, value || [])
      } else if (type === 'swatches') {
        renderSwatches(el, value || [])
      } else if (type === 'fonts') {
        renderFonts(el, value || [])
      } else if (type === 'assets') {
        renderAssets(el, value || [])
      } else {
        el.value = value === null || value === undefined ? '' : value
      }
    })

    document.querySelectorAll('[data-count-path]').forEach(function (el) {
      var value = getDeep(profile, el.dataset.countPath)
      el.textContent = (value || []).length
    })

    syncing = false
  }

  // ── Repeatable / readonly widgets ───────────────────────────────────────────

  function renderMetaItems(container, items) {
    container.textContent = ''

    items.forEach(function (item, index) {
      var row = document.createElement('div')
      row.className = 'meta-item-row'

      ;['label', 'value'].forEach(function (key) {
        var input = document.createElement('input')
        input.className = 'field-input'
        input.value = item[key] || ''
        input.placeholder = key === 'label' ? 'Label' : 'Waarde'
        input.addEventListener('input', function () {
          getDeep(profile, container.dataset.path)[index][key] = input.value
          syncEditorFromState()
          persist()
        })
        row.appendChild(input)
      })

      var remove = document.createElement('button')
      remove.type = 'button'
      remove.className = 'btn-remove'
      remove.title = 'Verwijder'
      remove.textContent = '×'
      remove.addEventListener('click', function () {
        var list = getDeep(profile, container.dataset.path)
        list.splice(index, 1)
        renderMetaItems(container, list)
        syncEditorFromState()
        persist()
      })
      row.appendChild(remove)

      container.appendChild(row)
    })

    var add = document.createElement('button')
    add.type = 'button'
    add.className = 'btn-add-item'
    add.textContent = '+ Rij toevoegen'
    add.addEventListener('click', function () {
      var list = getDeep(profile, container.dataset.path)
      if (!Array.isArray(list)) {
        list = []
        setDeep(profile, container.dataset.path, list)
      }
      list.push({ label: '', value: '' })
      renderMetaItems(container, list)
      syncEditorFromState()
      persist()
    })
    container.appendChild(add)
  }

  function empty(text) {
    var p = document.createElement('p')
    p.className = 'empty'
    p.textContent = text
    return p
  }

  function renderSwatches(container, colors) {
    container.textContent = ''
    if (!colors.length) {
      container.appendChild(empty('Geen kleuren'))
      return
    }

    var grid = document.createElement('div')
    grid.className = 'swatch-grid'
    colors.forEach(function (color) {
      var cell = document.createElement('div')
      cell.className = 'color-swatch'
      cell.title = color

      var block = document.createElement('div')
      block.className = 'swatch-block'
      block.style.background = color

      var label = document.createElement('span')
      label.className = 'swatch-label'
      label.textContent = color

      cell.appendChild(block)
      cell.appendChild(label)
      grid.appendChild(cell)
    })
    container.appendChild(grid)
  }

  function renderFonts(container, fonts) {
    container.textContent = ''
    if (!fonts.length) {
      container.appendChild(empty('Geen lettertypen'))
      return
    }

    var grid = document.createElement('div')
    grid.className = 'font-grid'
    fonts.forEach(function (font) {
      var badge = document.createElement('div')
      badge.className = 'font-badge'

      var name = document.createElement('span')
      name.className = 'font-name'
      name.textContent = font.name
      badge.appendChild(name)

      if (font.sizes && font.sizes.length) {
        var sizes = document.createElement('span')
        sizes.className = 'font-sizes'
        sizes.textContent = font.sizes.join(', ') + ' pt'
        badge.appendChild(sizes)
      }

      grid.appendChild(badge)
    })
    container.appendChild(grid)
  }

  function renderAssets(container, assets) {
    container.textContent = ''
    if (!assets.length) {
      container.appendChild(empty('Geen assets gevonden'))
      return
    }

    var grid = document.createElement('div')
    grid.className = 'asset-grid'
    assets.forEach(function (asset) {
      var card = document.createElement('div')
      card.className = 'asset-card'

      var icon = document.createElement('div')
      icon.className = 'asset-file-icon'
      icon.textContent = IMAGE_RE.test(asset.filename || '') ? '🖼️' : '📄'
      card.appendChild(icon)

      var info = document.createElement('div')
      info.className = 'asset-info'

      var slug = document.createElement('span')
      slug.className = 'asset-slug'
      slug.textContent = asset.slug

      var filename = document.createElement('span')
      filename.className = 'asset-filename'
      filename.textContent = asset.filename

      var source = document.createElement('span')
      source.className = 'asset-source'
      source.textContent = (asset.sources || []).join(', ')

      info.appendChild(slug)
      info.appendChild(filename)
      info.appendChild(source)
      card.appendChild(info)

      grid.appendChild(card)
    })
    container.appendChild(grid)
  }

  // ── JSON editor ─────────────────────────────────────────────────────────────

  function setError(message) {
    var box = document.getElementById('json-parse-error')
    box.textContent = message || ''
    box.hidden = !message
  }

  function initEditor() {
    editor = CodeMirror.fromTextArea(document.getElementById('json-editor'), {
      mode: 'application/json',
      theme: 'material-darker',
      lineNumbers: false,
      foldGutter: true,
      gutters: ['CodeMirror-foldgutter'],
    })

    editor.on('change', function () {
      if (syncing) return
      try {
        profile = JSON.parse(editor.getValue())
        setError(null)
        renderForm()
        persist()
      } catch (e) {
        setError(e.message)
      }
    })
  }

  // ── Tabs ────────────────────────────────────────────────────────────────────

  function initTabs() {
    document.querySelectorAll('.form-tab').forEach(function (button) {
      button.addEventListener('click', function () {
        document.querySelectorAll('.form-tab').forEach(function (other) {
          other.classList.toggle('active', other === button)
        })
        document.querySelectorAll('[data-tab-panel]').forEach(function (panel) {
          panel.hidden = panel.dataset.tabPanel !== button.dataset.tab
        })
      })
    })
  }

  // ── Upload ──────────────────────────────────────────────────────────────────

  function setDropzoneFile(zone, file, fallbackHtml) {
    zone.classList.toggle('has-file', !!file)
    var label = zone.querySelector('.dropzone-hint, .file-name')
    if (file) {
      label.className = 'file-name'
      label.textContent = '📄 ' + file.name
    } else {
      label.className = 'dropzone-hint'
      label.innerHTML = fallbackHtml
    }
  }

  function initDropzone(zoneId, inputId, onFile) {
    var zone = document.getElementById(zoneId)
    var input = document.getElementById(inputId)
    var fallbackHtml = zone.querySelector('.dropzone-hint').innerHTML

    zone.addEventListener('click', function () { input.click() })
    zone.addEventListener('dragover', function (e) {
      e.preventDefault()
      zone.classList.add('dragging')
    })
    zone.addEventListener('dragleave', function () { zone.classList.remove('dragging') })
    zone.addEventListener('drop', function (e) {
      e.preventDefault()
      zone.classList.remove('dragging')
      var file = e.dataTransfer.files[0]
      if (file) {
        onFile(file)
        setDropzoneFile(zone, file, fallbackHtml)
      }
    })
    input.addEventListener('change', function () {
      var file = input.files[0] || null
      onFile(file)
      setDropzoneFile(zone, file, fallbackHtml)
    })
  }

  function csrfToken() {
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]')
    return input ? input.value : ''
  }

  function showUploadError(message) {
    var box = document.getElementById('upload-error')
    box.textContent = message || ''
    box.hidden = !message
  }

  function initUpload() {
    var submit = document.getElementById('submit-btn')

    initDropzone('doc-dropzone', 'doc-input', function (file) {
      docFile = file
      submit.disabled = !docFile
    })
    initDropzone('tmpl-dropzone', 'tmpl-input', function (file) {
      tmplFile = file
    })

    document.getElementById('upload-form').addEventListener('submit', function (e) {
      e.preventDefault()
      if (!docFile) return

      submit.disabled = true
      submit.textContent = 'Bezig met extraheren…'
      showUploadError(null)

      var body = new FormData()
      body.append('document', docFile)
      if (tmplFile) body.append('template_docx', tmplFile)

      fetch('/api/extract/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken() },
        body: body,
      })
        .then(function (response) {
          // Sessie verlopen: herladen zet de gebruiker terug op de Google-login.
          if (response.status === 401) {
            window.location.reload()
            throw new Error('Sessie verlopen, opnieuw inloggen…')
          }
          return response.json().catch(function () { return {} }).then(function (data) {
            if (!response.ok) throw new Error(data.detail || 'Extractie mislukt')
            return data
          })
        })
        .then(function (data) {
          showResult(data)
          persist()
        })
        .catch(function (error) {
          showUploadError(error.message)
        })
        .finally(function () {
          submit.disabled = !docFile
          submit.textContent = 'Extraheer branding'
        })
    })
  }

  // ── Views ───────────────────────────────────────────────────────────────────

  function showResult(result) {
    profile = result.profile
    documentFilename = result.document_filename || 'document.docx'

    var warnings = result.warnings || []
    var box = document.getElementById('viewer-warnings')
    box.textContent = ''
    box.hidden = !warnings.length
    warnings.forEach(function (warning) {
      var span = document.createElement('span')
      span.textContent = '⚠ ' + warning
      box.appendChild(span)
    })

    document.getElementById('upload-view').hidden = true
    document.getElementById('viewer-view').hidden = false

    syncing = true
    editor.setValue(profileJson())
    syncing = false
    setError(null)
    editor.refresh()
    renderForm()
  }

  function initViewerActions() {
    document.getElementById('reset-btn').addEventListener('click', function () {
      try { localStorage.removeItem(STORAGE_KEY) } catch (e) {}
      window.location.reload()
    })

    var copy = document.getElementById('copy-btn')
    copy.addEventListener('click', function () {
      navigator.clipboard.writeText(profileJson())
      copy.textContent = 'Gekopieerd!'
      setTimeout(function () { copy.textContent = 'Kopieer JSON' }, 2000)
    })
  }

  // ── Boot ────────────────────────────────────────────────────────────────────

  initEditor()
  initTabs()
  initUpload()
  initViewerActions()
  document.getElementById('form-scroll').addEventListener('input', onFormInput)

  var saved = null
  try {
    saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
  } catch (e) {}
  if (saved && saved.profile) showResult(saved)
})()
