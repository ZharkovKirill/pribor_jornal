-- Keep link text in DOCX, but remove every internal and external hyperlink.

function Link(link)
  return link.content
end
