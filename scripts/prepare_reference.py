#!/usr/bin/env python3
"""Create the NTV Pandoc reference DOCX without an external Word template.

Pandoc's built-in reference document supplies the standard package parts. This
script replaces its body, styles, page setup, and footer with the NTV settings.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NS}}}"
ET.register_namespace("w", WORD_NS)

RELATIONSHIP_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
OFFICE_RELATIONSHIP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("r", OFFICE_RELATIONSHIP_NS)
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
ET.register_namespace("m", MATH_NS)

FOOTER_RELATIONSHIP_ID = "rIdNTVFooter"
FOOTER_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
)


def q(name: str) -> str:
    return W + name


def child(parent: ET.Element, name: str, **attributes: str) -> ET.Element:
    element = ET.SubElement(parent, q(name))
    for key, value in attributes.items():
        element.set(q(key), value)
    return element


def style_name(style: ET.Element) -> str:
    name = style.find(q("name"))
    return "" if name is None else name.get(q("val"), "")


def find_style(styles: ET.Element, name: str) -> ET.Element | None:
    wanted = name.casefold()
    for style in styles.findall(q("style")):
        if style_name(style).casefold() == wanted:
            return style
    return None


def remove_properties(style: ET.Element) -> None:
    for tag in ("pPr", "rPr"):
        element = style.find(q(tag))
        if element is not None:
            style.remove(element)


def paragraph_properties(
    *,
    alignment: str = "both",
    first_line: int = 708,
    line: int = 360,
    before: int = 0,
    after: int = 0,
    keep_next: bool = False,
    keep_lines: bool = False,
) -> ET.Element:
    properties = ET.Element(q("pPr"))
    if keep_next:
        child(properties, "keepNext")
    if keep_lines:
        child(properties, "keepLines")
    child(
        properties,
        "spacing",
        before=str(before),
        after=str(after),
        line=str(line),
        lineRule="auto",
    )
    child(properties, "ind", firstLine=str(first_line))
    child(properties, "jc", val=alignment)
    return properties


def run_properties(*, bold: bool = False, italic: bool = False, size: int = 28) -> ET.Element:
    properties = ET.Element(q("rPr"))
    child(
        properties,
        "rFonts",
        ascii="Times New Roman",
        eastAsia="Times New Roman",
        hAnsi="Times New Roman",
        cs="Times New Roman",
    )
    if bold:
        child(properties, "b")
        child(properties, "bCs")
    if italic:
        child(properties, "i")
        child(properties, "iCs")
    child(properties, "color", val="000000")
    child(properties, "sz", val=str(size))
    child(properties, "szCs", val=str(size))
    child(properties, "lang", val="ru-RU", eastAsia="ru-RU")
    return properties


def configure_style(
    style: ET.Element,
    *,
    alignment: str = "both",
    first_line: int = 708,
    line: int = 360,
    bold: bool = False,
    italic: bool = False,
    size: int = 28,
    before: int = 0,
    after: int = 0,
    keep_next: bool = False,
    keep_lines: bool = False,
) -> None:
    remove_properties(style)
    style.append(
        paragraph_properties(
            alignment=alignment,
            first_line=first_line,
            line=line,
            before=before,
            after=after,
            keep_next=keep_next,
            keep_lines=keep_lines,
        )
    )
    style.append(run_properties(bold=bold, italic=italic, size=size))


def add_custom_style(
    styles: ET.Element,
    *,
    style_id: str,
    name: str,
    based_on: str,
    alignment: str = "both",
    first_line: int = 708,
    line: int = 360,
    bold: bool = False,
    italic: bool = False,
    size: int = 28,
    before: int = 0,
    after: int = 0,
    keep_next: bool = False,
    keep_lines: bool = False,
) -> ET.Element:
    existing = find_style(styles, name)
    if existing is not None:
        style = existing
    else:
        style = ET.SubElement(
            styles,
            q("style"),
            {q("type"): "paragraph", q("customStyle"): "1", q("styleId"): style_id},
        )
        child(style, "name", val=name)
        child(style, "basedOn", val=based_on)
        child(style, "next", val=based_on)
        child(style, "qFormat")
    configure_style(
        style,
        alignment=alignment,
        first_line=first_line,
        line=line,
        bold=bold,
        italic=italic,
        size=size,
        before=before,
        after=after,
        keep_next=keep_next,
        keep_lines=keep_lines,
    )
    return style


def patch_styles(xml: bytes) -> bytes:
    root = ET.fromstring(xml)
    normal = find_style(root, "Normal")
    if normal is None:
        raise RuntimeError("The reference document has no Normal paragraph style")
    normal_id = normal.get(q("styleId"), "Normal")

    configure_style(normal)

    builtins = {
        "Title": dict(
            alignment="center",
            first_line=0,
            bold=True,
            before=360,
            after=360,
            keep_next=True,
            keep_lines=True,
        ),
        "Subtitle": dict(alignment="center", first_line=0, keep_next=True, keep_lines=True),
        "Author": dict(alignment="center", first_line=0, line=240),
        "Date": dict(alignment="center", first_line=0, line=240),
        "heading 1": dict(alignment="center", first_line=0, bold=True, keep_next=True, keep_lines=True),
        "heading 2": dict(alignment="left", first_line=0, bold=True, keep_next=True, keep_lines=True),
        "heading 3": dict(alignment="left", first_line=0, bold=True, keep_next=True, keep_lines=True),
        "caption": dict(alignment="center", first_line=0, keep_next=True, keep_lines=True),
        "List Paragraph": dict(alignment="both", first_line=0),
        "footer": dict(alignment="center", first_line=0, line=240),
    }
    for name, values in builtins.items():
        style = find_style(root, name)
        if style is not None:
            configure_style(style, **values)

    custom_styles = (
        ("NTVBody", "NTV Body", dict()),
        ("BodyText", "Body Text", dict()),
        ("FirstParagraph", "First Paragraph", dict()),
        ("Compact", "Compact", dict(alignment="center", first_line=0, line=240)),
        ("Author", "Author", dict(alignment="center", first_line=0, line=240)),
        ("Date", "Date", dict(alignment="center", first_line=0, line=240)),
        ("CaptionedFigure", "Captioned Figure", dict(alignment="center", first_line=0, line=240)),
        ("ImageCaption", "Image Caption", dict(alignment="center", first_line=0, keep_next=True, keep_lines=True)),
        ("TableCaption", "Table Caption", dict(alignment="center", first_line=0, keep_next=True, keep_lines=True)),
        ("FigureCaption", "Figure Caption", dict(alignment="center", first_line=0, keep_next=True, keep_lines=True)),
        ("NTVNoIndent", "NTV No Indent", dict(first_line=0)),
        ("NTVCenter", "NTV Center", dict(alignment="center", first_line=0, line=240)),
        ("NTVAbstract", "NTV Abstract", dict()),
        ("NTVKeywords", "NTV Keywords", dict(first_line=0)),
        ("NTVHeading", "NTV Heading", dict(alignment="center", first_line=0, bold=True, keep_next=True, keep_lines=True)),
        ("NTVCaption", "NTV Caption", dict(alignment="center", first_line=0, keep_next=True, keep_lines=True)),
        ("NTVUDC", "NTV UDC", dict(alignment="left", first_line=0)),
        ("NTVBibliography", "NTV Bibliography", dict(first_line=567)),
        ("NTVEquation", "NTV Equation", dict(alignment="center", first_line=0)),
    )
    for style_id, name, values in custom_styles:
        add_custom_style(root, style_id=style_id, name=name, based_on=normal_id, **values)

    table_style = find_style(root, "Table")
    if table_style is None:
        table_grid = find_style(root, "Table Grid")
        if table_grid is not None:
            table_style = deepcopy(table_grid)
            table_style.set(q("styleId"), "Table")
            table_style.set(q("customStyle"), "1")
            name = table_style.find(q("name"))
            if name is not None:
                name.set(q("val"), "Table")
            root.append(table_style)
        else:
            table_style = ET.SubElement(
                root,
                q("style"),
                {q("type"): "table", q("customStyle"): "1", q("styleId"): "Table"},
            )
            child(table_style, "name", val="Table")

    old_ppr = table_style.find(q("pPr"))
    if old_ppr is not None:
        table_style.remove(old_ppr)
    table_style.append(paragraph_properties(alignment="center", first_line=0, line=240))

    table_properties = table_style.find(q("tblPr"))
    if table_properties is None:
        table_properties = child(table_style, "tblPr")
    table_alignment = table_properties.find(q("jc"))
    if table_alignment is None:
        table_alignment = child(table_properties, "jc")
    table_alignment.set(q("val"), "center")
    old_borders = table_properties.find(q("tblBorders"))
    if old_borders is not None:
        table_properties.remove(old_borders)
    borders = child(table_properties, "tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        child(borders, edge, val="single", sz="4", space="0", color="auto")

    defaults = root.find(q("docDefaults"))
    if defaults is not None:
        run_default = defaults.find(f"{q('rPrDefault')}/{q('rPr')}")
        if run_default is not None:
            defaults.find(q("rPrDefault")).remove(run_default)  # type: ignore[union-attr]
            defaults.find(q("rPrDefault")).append(run_properties())  # type: ignore[union-attr]
        paragraph_default = defaults.find(f"{q('pPrDefault')}/{q('pPr')}")
        if paragraph_default is not None:
            defaults.find(q("pPrDefault")).remove(paragraph_default)  # type: ignore[union-attr]
            defaults.find(q("pPrDefault")).append(  # type: ignore[union-attr]
                paragraph_properties()
            )

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_settings(xml: bytes) -> bytes:
    root = ET.fromstring(xml)
    update_fields = root.find(q("updateFields"))
    if update_fields is None:
        update_fields = child(root, "updateFields")
    update_fields.set(q("val"), "true")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_document(xml: bytes) -> bytes:
    """Remove sample content and install the complete NTV page setup."""
    root = ET.fromstring(xml)
    body = root.find(q("body"))
    if body is None:
        raise RuntimeError("The reference document has no body")
    section = body.find(q("sectPr"))
    if section is None:
        raise RuntimeError("The reference document has no final section properties")
    section.clear()
    footer_reference = ET.SubElement(section, q("footerReference"))
    footer_reference.set(q("type"), "default")
    footer_reference.set(f"{{{OFFICE_RELATIONSHIP_NS}}}id", FOOTER_RELATIONSHIP_ID)
    child(section, "pgSz", w="11906", h="16838")
    child(
        section,
        "pgMar",
        top="1418",
        right="567",
        bottom="1134",
        left="1418",
        header="720",
        footer="720",
        gutter="0",
    )
    child(section, "cols", space="720")
    child(section, "docGrid", linePitch="360")
    retained_section = deepcopy(section)
    body.clear()
    body.append(retained_section)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_document_relationships(xml: bytes) -> bytes:
    root = ET.fromstring(xml)
    for relationship in list(root):
        relationship_type = relationship.get("Type", "").rsplit("/", 1)[-1]
        if relationship_type in {"footer", "hyperlink"}:
            root.remove(relationship)
    ET.SubElement(
        root,
        f"{{{RELATIONSHIP_NS}}}Relationship",
        {
            "Id": FOOTER_RELATIONSHIP_ID,
            "Type": f"{OFFICE_RELATIONSHIP_NS}/footer",
            "Target": "footer1.xml",
        },
    )
    ET.register_namespace("", RELATIONSHIP_NS)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def patch_content_types(xml: bytes) -> bytes:
    root = ET.fromstring(xml)
    for element in list(root):
        if element.get("PartName") == "/word/footer1.xml":
            root.remove(element)
    ET.SubElement(
        root,
        f"{{{CONTENT_TYPES_NS}}}Override",
        {"PartName": "/word/footer1.xml", "ContentType": FOOTER_CONTENT_TYPE},
    )
    ET.register_namespace("", CONTENT_TYPES_NS)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def create_footer() -> bytes:
    root = ET.Element(q("ftr"))
    paragraph = child(root, "p")
    properties = child(paragraph, "pPr")
    child(properties, "pStyle", val="Footer")
    child(properties, "jc", val="center")

    def field_run(field_type: str) -> None:
        run = child(paragraph, "r")
        run.append(run_properties())
        child(run, "fldChar", fldCharType=field_type)

    field_run("begin")
    instruction_run = child(paragraph, "r")
    instruction_run.append(run_properties())
    instruction = child(instruction_run, "instrText")
    instruction.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    instruction.text = " PAGE "
    field_run("separate")
    result_run = child(paragraph, "r")
    result_run.append(run_properties())
    result = child(result_run, "t")
    result.text = "1"
    field_run("end")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def create_reference(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reference-", dir=destination.parent) as directory:
        temporary_directory = Path(directory)
        source = temporary_directory / "pandoc-reference.docx"
        temporary_path = temporary_directory / "ntv-reference.docx"
        with source.open("wb") as stream:
            subprocess.run(
                ["pandoc", "--print-default-data-file", "reference.docx"],
                check=True,
                stdout=stream,
            )

        with zipfile.ZipFile(source, "r") as source_zip, zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as destination_zip:
            for info in source_zip.infolist():
                if info.filename == "word/footer1.xml":
                    continue
                data = source_zip.read(info.filename)
                if info.filename == "[Content_Types].xml":
                    data = patch_content_types(data)
                elif info.filename == "word/document.xml":
                    data = patch_document(data)
                elif info.filename == "word/_rels/document.xml.rels":
                    data = patch_document_relationships(data)
                elif info.filename == "word/styles.xml":
                    data = patch_styles(data)
                elif info.filename == "word/settings.xml":
                    data = patch_settings(data)
                cloned = deepcopy(info)
                destination_zip.writestr(cloned, data)
            destination_zip.writestr("word/footer1.xml", create_footer())
        os.replace(temporary_path, destination)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: prepare_reference.py DESTINATION.docx", file=sys.stderr)
        return 2
    create_reference(Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
