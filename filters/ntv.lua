-- Pandoc adjustments for the NTV journal DOCX template.
--
-- The LaTeX source stays conventional.  This filter only maps semantic blocks
-- to the paragraph styles added by prepare_reference.py and preserves explicit
-- LaTeX page breaks in Word.

local function styled(blocks, style_name)
  if blocks.t ~= nil then
    blocks = {blocks}
  end
  return pandoc.Div(blocks, pandoc.Attr("", {}, { ["custom-style"] = style_name }))
end

local title_blocks = {}
local title_was_emitted = false
local figure_number = 0
local table_number = 0

local function has_class(div, wanted)
  for _, class_name in ipairs(div.classes) do
    if class_name == wanted then
      return true
    end
  end
  return false
end

local function is_raw_tex(block, pattern)
  return block.t == "RawBlock"
    and (block.format == "tex" or block.format == "latex")
    and block.text:match(pattern) ~= nil
end

local function is_page_break(block)
  return is_raw_tex(block, "^%s*\\newpage%s*$")
    or is_raw_tex(block, "^%s*\\clearpage%s*$")
    or is_raw_tex(block, "^%s*\\pagebreak%s*$")
end

local function word_page_break()
  return pandoc.RawBlock(
    "openxml",
    '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
  )
end

local function starts_with(text, prefix)
  return text:sub(1, #prefix) == prefix
end

local function paragraph_style(block, in_bibliography)
  local text = pandoc.utils.stringify(block)
  if starts_with(text, "УДК") or starts_with(text, "UDC") then
    return "NTV UDC"
  end
  if starts_with(text, "Аннотация.") or starts_with(text, "Abstract.") then
    return "NTV Abstract"
  end
  if starts_with(text, "Ключевые слова:") or starts_with(text, "Keywords:") then
    return "NTV Keywords"
  end
  if in_bibliography then
    return "NTV Bibliography"
  end
  return nil
end

local function append_inlines(target, source)
  for _, inline in ipairs(source) do
    table.insert(target, inline)
  end
end

local function make_title_blocks(metadata)
  local result = {}
  if metadata.title ~= nil and pandoc.utils.stringify(metadata.title) ~= "" then
    table.insert(result, styled(pandoc.Para(metadata.title), "Title"))
  end
  if metadata.author ~= nil then
    local authors = {}
    for index, author in ipairs(metadata.author) do
      if index > 1 then
        table.insert(authors, pandoc.Str(","))
        table.insert(authors, pandoc.Space())
      end
      append_inlines(authors, author)
    end
    if #authors > 0 then
      table.insert(result, styled(pandoc.Para(authors), "Author"))
    end
  end
  if metadata.date ~= nil and pandoc.utils.stringify(metadata.date) ~= "" then
    table.insert(result, styled(pandoc.Para(metadata.date), "Date"))
  end
  return result
end

local function run_in_heading(header, paragraph)
  local heading = {}
  for _, inline in ipairs(header.content) do
    table.insert(heading, inline)
  end
  table.insert(heading, pandoc.Str("."))

  local content = {pandoc.Strong(heading), pandoc.Space()}
  for _, inline in ipairs(paragraph.content) do
    table.insert(content, inline)
  end
  return pandoc.Para(content)
end

local process_blocks

local function process_div(div, in_bibliography)
  local bibliography = in_bibliography or div.identifier == "refs"
  local content = process_blocks(div.content, bibliography)
  if has_class(div, "center") then
    return styled(content, "NTV Center")
  end
  if has_class(div, "flushleft") or has_class(div, "flushright") then
    return styled(content, "NTV No Indent")
  end
  if has_class(div, "abstract") then
    return styled(content, "NTV Abstract")
  end
  div.content = content
  return div
end

process_blocks = function(blocks, initial_in_bibliography)
  local output = {}
  local index = 1
  local in_bibliography = initial_in_bibliography or false
  local environment = nil
  local environment_blocks = {}

  local function emit(block)
    if environment ~= nil then
      table.insert(environment_blocks, block)
    else
      table.insert(output, block)
    end
  end

  local function close_environment()
    local style_name = environment == "center" and "NTV Center" or "NTV No Indent"
    table.insert(output, styled(environment_blocks, style_name))
    environment = nil
    environment_blocks = {}
  end

  while index <= #blocks do
    local block = blocks[index]

    if is_raw_tex(block, "^%s*\\maketitle%s*$") then
      for _, title_block in ipairs(title_blocks) do
        emit(title_block)
      end
      title_was_emitted = true
    elseif is_raw_tex(block, "^%s*\\begin%s*{%s*center%s*}%s*$") then
      environment = "center"
      environment_blocks = {}
    elseif is_raw_tex(block, "^%s*\\begin%s*{%s*flushleft%s*}%s*$") then
      environment = "flushleft"
      environment_blocks = {}
    elseif is_raw_tex(block, "^%s*\\end%s*{%s*center%s*}%s*$")
        or is_raw_tex(block, "^%s*\\end%s*{%s*flushleft%s*}%s*$") then
      close_environment()
    elseif is_page_break(block) then
      emit(word_page_break())
    elseif block.t == "Div" then
      emit(process_div(block, in_bibliography))
    elseif block.t == "Header" then
      local heading_text = pandoc.utils.stringify(block)
      if heading_text == "Список литературы" or heading_text == "References" then
        in_bibliography = true
        emit(styled(pandoc.Para({pandoc.Strong(block.content)}), "NTV Heading"))
      elseif heading_text == "СВЕДЕНИЯ ОБ АВТОРАХ" or heading_text == "AUTHOR INFORMATION" then
        in_bibliography = false
        emit(styled(pandoc.Para({pandoc.Strong(block.content)}), "NTV Heading"))
      elseif block.level >= 4 and index < #blocks
          and (blocks[index + 1].t == "Para" or blocks[index + 1].t == "Plain") then
        emit(run_in_heading(block, blocks[index + 1]))
        index = index + 1
      else
        emit(block)
      end
    elseif block.t == "Para" or block.t == "Plain" then
      local style_name = paragraph_style(block, in_bibliography)
      if style_name ~= nil then
        emit(styled(block, style_name))
      else
        emit(block)
      end
    else
      emit(block)
    end
    index = index + 1
  end

  if environment ~= nil then
    close_environment()
  end
  return output
end

function Pandoc(document)
  title_blocks = make_title_blocks(document.meta)
  title_was_emitted = false
  document.blocks = process_blocks(document.blocks)
  if not title_was_emitted and #title_blocks > 0 then
    local combined = {}
    for _, block in ipairs(title_blocks) do
      table.insert(combined, block)
    end
    for _, block in ipairs(document.blocks) do
      table.insert(combined, block)
    end
    document.blocks = combined
  end
  document.meta.title = nil
  document.meta.author = nil
  document.meta.date = nil
  return document
end

function RawInline(inline)
  if inline.format ~= "tex" and inline.format ~= "latex" then
    return nil
  end
  local remainder = inline.text:match("^\\noindent%s*(.*)$")
  if remainder == nil then
    return nil
  end
  if remainder == "" then
    return {}
  end
  return pandoc.Str(remainder)
end

function RawBlock(block)
  if (block.format == "tex" or block.format == "latex")
      and block.text:match("^%s*\\centering%s*$") then
    return {}
  end
  return nil
end

function Math(math)
  if math.mathtype ~= "DisplayMath" then
    return nil
  end
  local expression, number = math.text:match("^(.-)%s*\\tag%s*{([^{}]+)}%s*$")
  if expression == nil then
    return nil
  end
  math.text = expression .. " \\qquad \\text{(" .. number .. ")}"
  return math
end

function Para(para)
  if #para.content ~= 1 or para.content[1].t ~= "Image" then
    return nil
  end

  local image = para.content[1]
  if image.title == nil or not starts_with(image.title, "fig:") then
    return nil
  end

  local existing = pandoc.utils.stringify(image.caption)
  if starts_with(existing, "Рисунок ") or starts_with(existing, "Figure ") then
    return nil
  end

  figure_number = figure_number + 1
  local content = {
    pandoc.Str("Рисунок"),
    pandoc.Space(),
    pandoc.Str(tostring(figure_number)),
    pandoc.Space(),
    pandoc.Str("–"),
    pandoc.Space(),
  }
  append_inlines(content, image.caption)
  image.caption = content
  para.content[1] = image
  return para
end

function Table(table_block)
  if table_block.caption == nil or table_block.caption.long == nil
      or #table_block.caption.long == 0 then
    return nil
  end
  local first = table_block.caption.long[1]
  if first.t ~= "Plain" and first.t ~= "Para" then
    return nil
  end
  local existing = pandoc.utils.stringify(first)
  if starts_with(existing, "Таблица ") or starts_with(existing, "Table ") then
    return nil
  end
  table_number = table_number + 1
  local content = {
    pandoc.Str("Таблица"),
    pandoc.Space(),
    pandoc.Str(tostring(table_number)),
    pandoc.Space(),
    pandoc.Str("–"),
    pandoc.Space(),
  }
  append_inlines(content, first.content)
  first.content = content
  table_block.caption.long[1] = first
  return table_block
end
