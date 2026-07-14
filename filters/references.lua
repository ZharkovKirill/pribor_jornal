-- Prepare standard LaTeX citations and cross-references for Pandoc citeproc.

local figure_numbers = {}
local table_numbers = {}

local function starts_with(text, prefix)
  return text:sub(1, #prefix) == prefix
end

local function collect_targets(document)
  local figure_number = 0
  local table_number = 0

  document:walk({
    Image = function(image)
      if image.identifier ~= nil and starts_with(image.identifier, "fig:")
          and figure_numbers[image.identifier] == nil then
        figure_number = figure_number + 1
        figure_numbers[image.identifier] = figure_number
      end
      return nil
    end,
    Div = function(div)
      if div.identifier ~= nil and starts_with(div.identifier, "tab:")
          and table_numbers[div.identifier] == nil then
        table_number = table_number + 1
        table_numbers[div.identifier] = table_number
      end
      return nil
    end,
  })
end

local function replace_reference(inline)
  if inline.format ~= "tex" and inline.format ~= "latex" then
    return nil
  end

  local label = inline.text:match("^\\ref%s*{([^{}]+)}$")
  if label == nil then
    return nil
  end

  local number = figure_numbers[label] or table_numbers[label]
  if number == nil then
    return pandoc.Str("??")
  end

  return pandoc.Link(
    {pandoc.Str(tostring(number))},
    "#" .. label
  )
end

local function replace_bibliography_marker(block)
  if (block.format == "tex" or block.format == "latex")
      and block.text:match("^%s*\\printbibliography") then
    return pandoc.Div({}, pandoc.Attr("refs", {"references"}, {}))
  end
  return nil
end

function Pandoc(document)
  figure_numbers = {}
  table_numbers = {}
  collect_targets(document)
  return document:walk({
    RawInline = replace_reference,
    RawBlock = replace_bibliography_marker,
  })
end
