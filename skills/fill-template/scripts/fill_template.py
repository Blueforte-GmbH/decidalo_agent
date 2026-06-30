#!/usr/bin/env python3
"""
Fill Decidalo Word mailmerge templates with JSON profile data.

Block-based range engine: clones entire w:p and w:tbl blocks between range
markers, so table structures (including nested project-box tables) are fully
preserved. Handles:
- RangeStart/RangeEnd repetition for all list sections
- Single-paragraph ranges (Start + content + End in one w:p)
- Start paragraphs that also carry content fields (e.g. RangeStart:X + JobTitle)
- fldSimple-encoded RangeEnd markers (Decidalo quirk on Projects)
- Nested inner ranges (Skills list inside Projects table)
- Case-insensitive field name matching (template 'Name' vs JSON 'name')
"""

import base64
import json
import mimetypes
import re
import sys
import zipfile
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

try:
    import click
    from lxml import etree
    import requests
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RELNS = "http://schemas.openxmlformats.org/package/2006/relationships"
CTNS = "http://schemas.openxmlformats.org/package/2006/content-types"
WPNS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PICNS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

CANDIDATE_PICTURE_PLACEHOLDER = "@@CandidatePicture@@"
CANDIDATE_PICTURE_KEYS = (
    "CandidatePicture",
    "CandidatePictureUrl",
    "CandidatePictureSignedUrl",
    "ProfilePicture",
    "ProfilePictureUrl",
    "ProfilePictureSignedUrl",
    "profilePicture",
    "profilePictureUrl",
    "profilePictureSignedUrl",
    "pictureUrl",
    "pictureSignedUrl",
    "photoUrl",
    "photoSignedUrl",
    "signedUrl",
    "signed_url",
)
DEFAULT_CANDIDATE_PICTURE_EMU = 2160000


def w(tag: str) -> str:
    return f"{{{WNS}}}{tag}"


def r(tag: str) -> str:
    return f"{{{RNS}}}{tag}"


def rel(tag: str) -> str:
    return f"{{{RELNS}}}{tag}"


def ct(tag: str) -> str:
    return f"{{{CTNS}}}{tag}"


# ---------------------------------------------------------------------------
# Basic utilities
# ---------------------------------------------------------------------------

_SKIP_TOKENS = {"MERGEFORMAT", "hideDatesInFuture"}


def parse_field_name(instr: str) -> str | None:
    """Extract field name from a MERGEFIELD instruction string."""
    m = re.search(r"MERGEFIELD(.+)", instr, re.DOTALL)
    if not m:
        return None
    rest = m.group(1)
    rest = re.sub(r"\\[\w]+(?:\s+\"[^\"]*\")?", " ", rest)
    tokens = [t for t in re.findall(r"[\w:]+", rest) if t not in _SKIP_TOKENS]
    return tokens[0] if tokens else None


def ci_get(data: dict, key: str):
    """Case-insensitive dict lookup. Returns (value, found_key) or (None, None)."""
    if key in data:
        return data[key], key
    key_lower = key.lower()
    for k, v in data.items():
        if k.lower() == key_lower:
            return v, k
    return None, None


# ---------------------------------------------------------------------------
# Candidate picture support
# ---------------------------------------------------------------------------

def _direct_paragraph_text(paragraph: etree._Element) -> str:
    """Return visible text that belongs to this paragraph, excluding nested text boxes."""
    parts: list[str] = []
    for text_node in paragraph.iter(w("t")):
        parent = text_node.getparent()
        owner_p = None
        while parent is not None:
            if parent.tag == w("p"):
                owner_p = parent
                break
            parent = parent.getparent()
        if owner_p is paragraph:
            parts.append(text_node.text or "")
    return "".join(parts)


def count_picture_placeholders(doc_xml: bytes) -> int:
    root = etree.fromstring(doc_xml)
    return sum(
        1
        for paragraph in root.iter(w("p"))
        if CANDIDATE_PICTURE_PLACEHOLDER in _direct_paragraph_text(paragraph)
    )


def find_candidate_picture_source(data: dict) -> str | None:
    """Find a signed image URL or local path in mapped or raw-ish profile data."""
    for key in CANDIDATE_PICTURE_KEYS:
        value, _ = ci_get(data, key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    cv_items, _ = ci_get(data, "CV")
    if isinstance(cv_items, list) and cv_items and isinstance(cv_items[0], dict):
        for key in CANDIDATE_PICTURE_KEYS:
            value, _ = ci_get(cv_items[0], key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _image_format_from_bytes(image_bytes: bytes, content_type: str | None, source: str) -> tuple[str, str]:
    content_type = (content_type or "").split(";")[0].strip().lower()
    content_type_map = {
        "image/jpeg": ("jpeg", "image/jpeg"),
        "image/jpg": ("jpeg", "image/jpeg"),
        "image/png": ("png", "image/png"),
        "image/gif": ("gif", "image/gif"),
    }
    if content_type in content_type_map:
        return content_type_map[content_type]

    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg", "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "gif", "image/gif"

    guessed_type, _ = mimetypes.guess_type(source)
    if guessed_type in content_type_map:
        return content_type_map[guessed_type]

    raise ValueError("CandidatePicture must be a JPEG, PNG, or GIF image")


def load_image_source(source: str) -> tuple[bytes, str, str]:
    """Load an image from a signed URL, data URL, or local file path."""
    if source.startswith("data:image/"):
        header, encoded = source.split(",", 1)
        content_type = header[5:].split(";")[0]
        image_bytes = base64.b64decode(encoded)
        ext, normalized_type = _image_format_from_bytes(image_bytes, content_type, source)
        return image_bytes, ext, normalized_type

    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        response = requests.get(source, timeout=20)
        response.raise_for_status()
        image_bytes = response.content
        ext, content_type = _image_format_from_bytes(
            image_bytes,
            response.headers.get("content-type"),
            source,
        )
        return image_bytes, ext, content_type

    path = Path(source).expanduser()
    if not path.exists():
        raise ValueError(f"CandidatePicture source not found: {source}")
    image_bytes = path.read_bytes()
    ext, content_type = _image_format_from_bytes(image_bytes, None, str(path))
    return image_bytes, ext, content_type


def next_media_name(existing_names: set[str], ext: str) -> str:
    index = 1
    while f"word/media/candidate_picture{index}.{ext}" in existing_names:
        index += 1
    return f"candidate_picture{index}.{ext}"


def add_image_relationship(rels_xml: bytes, media_name: str) -> tuple[bytes, str]:
    root = etree.fromstring(rels_xml)
    used_ids = {elem.get("Id", "") for elem in root.findall(rel("Relationship"))}
    used_numbers = [
        int(match.group(1))
        for rel_id in used_ids
        if (match := re.fullmatch(r"rId(\d+)", rel_id))
    ]
    next_id = max(used_numbers, default=0) + 1
    rel_id = f"rId{next_id}"
    while rel_id in used_ids:
        next_id += 1
        rel_id = f"rId{next_id}"

    relationship = etree.SubElement(root, rel("Relationship"))
    relationship.set("Id", rel_id)
    relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
    relationship.set("Target", f"media/{media_name}")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), rel_id


def ensure_content_type(content_types_xml: bytes, ext: str, content_type: str) -> bytes:
    root = etree.fromstring(content_types_xml)
    for elem in root.findall(ct("Default")):
        if (elem.get("Extension") or "").lower() == ext.lower():
            return content_types_xml

    default = etree.SubElement(root, ct("Default"))
    default.set("Extension", ext)
    default.set("ContentType", content_type)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def build_picture_run(rel_id: str, cx: int = DEFAULT_CANDIDATE_PICTURE_EMU, cy: int = DEFAULT_CANDIDATE_PICTURE_EMU) -> etree._Element:
    doc_pr_id = 900000 + int(re.sub(r"\D", "", rel_id) or "1")
    xml = f"""
    <w:r xmlns:w="{WNS}" xmlns:r="{RNS}" xmlns:wp="{WPNS}" xmlns:a="{ANS}" xmlns:pic="{PICNS}">
      <w:rPr><w:noProof/></w:rPr>
      <w:drawing>
        <wp:inline distT="0" distB="0" distL="0" distR="0">
          <wp:extent cx="{cx}" cy="{cy}"/>
          <wp:effectExtent l="0" t="0" r="0" b="0"/>
          <wp:docPr id="{doc_pr_id}" name="Candidate Picture"/>
          <wp:cNvGraphicFramePr>
            <a:graphicFrameLocks noChangeAspect="1"/>
          </wp:cNvGraphicFramePr>
          <a:graphic>
            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:pic>
                <pic:nvPicPr>
                  <pic:cNvPr id="{doc_pr_id}" name="Candidate Picture"/>
                  <pic:cNvPicPr>
                    <a:picLocks noChangeAspect="1"/>
                  </pic:cNvPicPr>
                </pic:nvPicPr>
                <pic:blipFill>
                  <a:blip r:embed="{rel_id}"/>
                  <a:stretch><a:fillRect/></a:stretch>
                </pic:blipFill>
                <pic:spPr>
                  <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="{cx}" cy="{cy}"/>
                  </a:xfrm>
                  <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                </pic:spPr>
              </pic:pic>
            </a:graphicData>
          </a:graphic>
        </wp:inline>
      </w:drawing>
    </w:r>
    """
    return etree.fromstring(xml)


def replace_picture_placeholders(doc_xml: bytes, rel_id: str) -> tuple[bytes, int]:
    root = etree.fromstring(doc_xml)
    replaced = 0

    for paragraph in root.iter(w("p")):
        if CANDIDATE_PICTURE_PLACEHOLDER not in _direct_paragraph_text(paragraph):
            continue

        for child in list(paragraph):
            if child.tag != w("pPr"):
                paragraph.remove(child)
        paragraph.append(build_picture_run(rel_id))
        replaced += 1

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), replaced


# ---------------------------------------------------------------------------
# Paragraph-level field operations
# ---------------------------------------------------------------------------

def _collect_field_groups(paragraph: etree._Element) -> list:
    """
    Return list of (field_name, begin_run, sep_run, display_runs) for every
    complex MERGEFIELD in the paragraph. Handles multiple fields per paragraph
    and fragmented instrText across runs.
    """
    groups = []
    state = "outside"
    parts: list[str] = []
    begin_run = sep_run = None
    display_runs: list[etree._Element] = []

    for elem in paragraph.iter(w("r")):
        fc = elem.find(w("fldChar"))
        if fc is not None:
            ft = fc.get(w("fldCharType"))
            if ft == "begin":
                state = "in_instr"
                begin_run = elem
                parts = []
                sep_run = None
                display_runs = []
            elif ft == "separate" and state == "in_instr":
                state = "in_display"
                sep_run = elem
            elif ft == "end" and state in ("in_instr", "in_display"):
                name = parse_field_name("".join(parts))
                if name:
                    groups.append((name, begin_run, sep_run, list(display_runs)))
                state = "outside"
                parts = []
                display_runs = []
        elif state == "in_instr":
            for it in elem.iter(w("instrText")):
                parts.append(it.text or "")
        elif state == "in_display":
            display_runs.append(elem)

    return groups


def get_all_field_names(paragraph: etree._Element) -> list[str]:
    """Return all MERGEFIELD names in a paragraph (complex + fldSimple)."""
    names = [name for name, *_ in _collect_field_groups(paragraph)]
    for fs in paragraph.iter(w("fldSimple")):
        name = parse_field_name(fs.get(w("instr"), ""))
        if name:
            names.append(name)
    return names


def _set_run_value(run: etree._Element, value: str) -> None:
    """Populate a run's text content, turning '\\n' into Word line breaks (<w:br/>).

    A literal newline inside a single <w:t> is collapsed by Word, so multi-line
    values (e.g. bullet-point descriptions) must be split into alternating
    <w:t>/<w:br/> children. Run properties (rPr) are preserved; only existing
    text/break nodes are removed before repopulating."""
    for child in list(run):
        if child.tag in (w("t"), w("br"), w("cr")):
            run.remove(child)
    for i, line in enumerate(value.split("\n")):
        if i > 0:
            etree.SubElement(run, w("br"))
        t_elem = etree.SubElement(run, w("t"))
        t_elem.text = line
        t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _write_display(
    begin_run: etree._Element,
    sep_run: etree._Element | None,
    display_runs: list[etree._Element],
    value: str,
) -> None:
    """Write value into the display portion of a complex MERGEFIELD."""
    if not display_runs and begin_run is not None and sep_run is not None:
        new_run = deepcopy(begin_run)
        for fc in list(new_run.findall(w("fldChar"))):
            new_run.remove(fc)
        for instr in list(new_run.findall(w("instrText"))):
            new_run.remove(instr)
        _set_run_value(new_run, value)
        parent = sep_run.getparent()
        if parent is not None:
            parent.insert(list(parent).index(sep_run) + 1, new_run)
    elif display_runs:
        first = display_runs[0]
        _set_run_value(first, value)
        for extra in display_runs[1:]:
            p = extra.getparent()
            if p is not None:
                p.remove(extra)


def set_fld_simple_value(paragraph: etree._Element, field_name: str, value: str) -> None:
    """Set display value of a w:fldSimple MERGEFIELD (case-insensitive match)."""
    for elem in paragraph.iter(w("fldSimple")):
        fname = parse_field_name(elem.get(w("instr"), ""))
        if fname and fname.lower() == field_name.lower():
            for child in list(elem):
                elem.remove(child)
            new_run = etree.SubElement(elem, w("r"))
            _set_run_value(new_run, value)


def fill_paragraph(paragraph: etree._Element, data: dict) -> None:
    """Fill ALL MERGEFIELD and fldSimple fields in a paragraph (case-insensitive)."""
    for fname, begin_run, sep_run, display_runs in _collect_field_groups(paragraph):
        val, _ = ci_get(data, fname)
        if val is not None and not isinstance(val, list):
            _write_display(begin_run, sep_run, display_runs, str(val))
    for field_name, value in data.items():
        if not isinstance(value, list):
            set_fld_simple_value(paragraph, field_name, str(value))


# ---------------------------------------------------------------------------
# Block-based range expansion
# ---------------------------------------------------------------------------

def _block_contains_field(block: etree._Element, field_name: str) -> bool:
    """Return True if block (w:p, w:tbl, or any element) contains the named field."""
    for p in block.iter(w("p")):
        if field_name in get_all_field_names(p):
            return True
    return False


def find_range_location(search_root: etree._Element, range_name: str):
    """
    Walk search_root's element tree to find (parent, start_idx, end_idx) where
    parent's direct children contain RangeStart:name and RangeEnd:name.

    When both markers are in the same w:p (single-paragraph range),
    start_idx == end_idx. Returns (None, -1, -1) if not found.
    """
    start_marker = f"RangeStart:{range_name}"
    end_marker = f"RangeEnd:{range_name}"

    for parent in search_root.iter():
        children = list(parent)
        if not children:
            continue

        start_idx = end_idx = -1
        for i, child in enumerate(children):
            if start_idx == -1 and _block_contains_field(child, start_marker):
                start_idx = i
            if _block_contains_field(child, end_marker):
                end_idx = i

        if start_idx == -1 or end_idx == -1:
            continue

        if start_idx == end_idx:
            # Both markers in the same child — only valid if it is a w:p.
            # If it is a w:tbl or w:tc the markers are buried deeper; keep searching.
            if etree.QName(children[start_idx].tag).localname != "p":
                continue

        return parent, start_idx, end_idx

    return None, -1, -1


def expand_range(search_root: etree._Element, range_name: str, items: list[dict]) -> None:
    """
    Clone blocks (w:p and/or w:tbl) between range markers, once per item.
    Entire w:tbl structures are cloned intact, preserving table formatting.
    Nested inner ranges are expanded recursively before field filling.
    """
    parent, start_idx, end_idx = find_range_location(search_root, range_name)
    if parent is None:
        return

    children = list(parent)
    start_block = children[start_idx]

    if start_idx == end_idx:
        # Single-paragraph range: join all items comma-separated on one line
        if items:
            seen_f: set[str] = set()
            all_fields: list[str] = []
            for item in items:
                for k, v in item.items():
                    if not isinstance(v, list) and k not in seen_f:
                        seen_f.add(k)
                        all_fields.append(k)
            joined: dict = {}
            for field in all_fields:
                vals = [str(ci_get(item, field)[0]) for item in items if ci_get(item, field)[0] is not None]
                joined[field] = ", ".join(vals)
            cloned = deepcopy(start_block)
            fill_paragraph(cloned, joined)
            parent.insert(list(parent).index(start_block), cloned)
        parent.remove(start_block)
        return
    else:
        # If start_block is a paragraph that also carries content fields, include it
        # in the template (e.g. RangeStart:ProfessionalExperience + JobTitle in one row).
        if etree.QName(start_block.tag).localname == "p":
            content_fields = [
                n for n in get_all_field_names(start_block)
                if not n.startswith("RangeStart:") and not n.startswith("RangeEnd:")
            ]
        else:
            content_fields = []

        if content_fields:
            template_blocks = children[start_idx:end_idx]       # includes start_block
        else:
            template_blocks = children[start_idx + 1:end_idx]   # excludes start_block

        blocks_to_remove = children[start_idx:end_idx + 1]      # start through end inclusive

    if not template_blocks:
        seen: set[int] = set()
        for block in blocks_to_remove:
            if id(block) not in seen:
                seen.add(id(block))
                p = block.getparent()
                if p is not None:
                    p.remove(block)
        return

    # Collect inner range names from the template
    inner_range_names: list[str] = []
    for block in template_blocks:
        for p in block.iter(w("p")):
            for name in get_all_field_names(p):
                if name.startswith("RangeStart:"):
                    inner = name[len("RangeStart:"):]
                    if inner not in inner_range_names:
                        inner_range_names.append(inner)

    # Build expanded blocks for every item
    expanded: list[etree._Element] = []
    for item in items:
        cloned = [deepcopy(b) for b in template_blocks]

        # Expand nested inner ranges within the clones
        for inner_name in inner_range_names:
            val, _ = ci_get(item, inner_name)
            if isinstance(val, list) and val:
                temp = etree.Element("temp")
                for b in cloned:
                    temp.append(b)
                expand_range(temp, inner_name, val)
                cloned = list(temp)

        # Fill scalar fields in every paragraph of the cloned blocks
        scalar_item = {k: v for k, v in item.items() if not isinstance(v, list)}
        for block in cloned:
            for p in block.iter(w("p")):
                fill_paragraph(p, scalar_item)

        expanded.extend(cloned)

    # Insert expanded blocks before start_block
    ref_idx = list(parent).index(start_block)
    for block in reversed(expanded):
        parent.insert(ref_idx, block)

    # Remove original blocks (deduplicated)
    seen: set[int] = set()
    for block in blocks_to_remove:
        if id(block) not in seen:
            seen.add(id(block))
            p = block.getparent()
            if p is not None:
                p.remove(block)


# ---------------------------------------------------------------------------
# Field discovery (for --list-fields)
# ---------------------------------------------------------------------------

def collect_fields(doc_xml: bytes) -> list[str]:
    """Return sorted list of all MERGEFIELD names in the document."""
    root = etree.fromstring(doc_xml)
    seen: set[str] = set()
    fields: list[str] = []
    state = False
    parts: list[str] = []

    for elem in root.iter():
        local = etree.QName(elem.tag).localname if elem.tag else ""
        if local == "fldChar":
            ft = elem.get(w("fldCharType"))
            if ft == "begin":
                state = True
                parts = []
            elif ft in ("separate", "end") and state:
                name = parse_field_name("".join(parts))
                if name and name not in seen:
                    seen.add(name)
                    fields.append(name)
                state = False
                parts = []
        elif local == "instrText" and state:
            parts.append(elem.text or "")

    for elem in root.iter(w("fldSimple")):
        name = parse_field_name(elem.get(w("instr"), ""))
        if name and name not in seen:
            seen.add(name)
            fields.append(name)

    return sorted(fields)


# ---------------------------------------------------------------------------
# Main merge
# ---------------------------------------------------------------------------

def merge(doc_xml: bytes, data: dict) -> bytes:
    """Apply all MERGEFIELD replacements to the document XML."""
    root = etree.fromstring(doc_xml)
    body = root.find(w("body"))
    if body is None:
        return doc_xml

    # Expand list ranges (outermost first so inner markers are present when needed)
    for key in (k for k in data if isinstance(data[k], list)):
        expand_range(body, key, data[key])

    # Fill remaining scalar fields across all paragraphs in the document
    scalar_data = {k: v for k, v in data.items() if not isinstance(v, list)}
    for para in body.iter(w("p")):
        fill_paragraph(para, scalar_data)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--template", "-t", required=True, help="Path to the .docx template file")
@click.option("--profile", "-p", default=None, help="Path to the JSON profile file")
@click.option("--output", "-o", default=None, help="Output path for the filled .docx")
@click.option(
    "--candidate-picture",
    default=None,
    help="Signed image URL or local image path for @@CandidatePicture@@ (overrides JSON CandidatePicture)",
)
@click.option("--list-fields", is_flag=True, help="List all MERGEFIELD names in the template and exit")
def main(template: str, profile: str, output: str, candidate_picture: str, list_fields: bool) -> None:
    """Fill a Decidalo Word mailmerge template with profile JSON data."""
    template_path = Path(template)
    if not template_path.exists():
        click.echo(f"ERROR: Template not found: {template}", err=True)
        sys.exit(1)

    with zipfile.ZipFile(template_path) as z:
        doc_xml = z.read("word/document.xml")

    if list_fields:
        fields = collect_fields(doc_xml)
        click.echo(f"MERGEFIELD names in '{template_path.name}':")
        for f in fields:
            click.echo(f"  {f}")
        return

    if not profile:
        click.echo("ERROR: --profile is required", err=True)
        sys.exit(1)

    profile_path = Path(profile)
    if not profile_path.exists():
        click.echo(f"ERROR: Profile file not found: {profile}", err=True)
        sys.exit(1)

    with open(profile_path, encoding="utf-8") as f:
        data: dict = json.load(f)

    if not output:
        output = str(template_path.parent.parent / "output" / f"{profile_path.stem}_filled.docx")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filled_xml = merge(doc_xml, data)
    picture_source = candidate_picture or find_candidate_picture_source(data)
    picture_placeholder_count = count_picture_placeholders(filled_xml)
    picture_replacements = 0
    picture_media_path: str | None = None
    updated_rels_xml: bytes | None = None
    updated_content_types_xml: bytes | None = None
    picture_bytes: bytes | None = None

    if picture_placeholder_count and picture_source:
        try:
            with zipfile.ZipFile(template_path) as src:
                existing_names = set(src.namelist())
                picture_bytes, picture_ext, picture_content_type = load_image_source(picture_source)
                picture_media_name = next_media_name(existing_names, picture_ext)
                picture_media_path = f"word/media/{picture_media_name}"
                updated_rels_xml, picture_rel_id = add_image_relationship(
                    src.read("word/_rels/document.xml.rels"),
                    picture_media_name,
                )
                updated_content_types_xml = ensure_content_type(
                    src.read("[Content_Types].xml"),
                    picture_ext,
                    picture_content_type,
                )
            filled_xml, picture_replacements = replace_picture_placeholders(filled_xml, picture_rel_id)
        except (OSError, ValueError, requests.RequestException, zipfile.BadZipFile) as exc:
            click.echo(f"ERROR: Could not load CandidatePicture image: {exc}", err=True)
            sys.exit(1)

    with zipfile.ZipFile(template_path) as src, zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename == "word/document.xml":
                dst.writestr(item, filled_xml)
            elif item.filename == "word/_rels/document.xml.rels" and updated_rels_xml is not None:
                dst.writestr(item, updated_rels_xml)
            elif item.filename == "[Content_Types].xml" and updated_content_types_xml is not None:
                dst.writestr(item, updated_content_types_xml)
            else:
                dst.writestr(item, src.read(item.filename))
        if picture_media_path and picture_bytes is not None:
            dst.writestr(picture_media_path, picture_bytes)

    # Report
    all_range_keys = {k for k in data if isinstance(data[k], list)}
    inner_keys: set[str] = set()
    for k in all_range_keys:
        for item in data[k]:
            if isinstance(item, dict):
                inner_keys.update(item.keys())

    fields = collect_fields(doc_xml)
    range_fields = {f for f in fields if f.startswith("RangeStart:") or f.startswith("RangeEnd:")}
    simple_fields = [f for f in fields if f not in range_fields]
    top_level_simple = [f for f in simple_fields if f not in inner_keys]

    filled = [f for f in top_level_simple if ci_get(data, f)[0] is not None]
    missing = [f for f in top_level_simple if ci_get(data, f)[0] is None and f not in inner_keys]
    if picture_placeholder_count and not picture_source:
        missing.append("CandidatePicture")
    ranges_expanded = [k for k in all_range_keys if f"RangeStart:{k}" in range_fields]

    click.echo(f"Generated: {output_path}")
    click.echo(f"Simple fields: {len(filled)}/{len(top_level_simple)} filled")
    if picture_replacements:
        click.echo(f"Candidate picture: replaced {picture_replacements} placeholder(s)")
    if ranges_expanded:
        click.echo(f"Ranges expanded: {', '.join(ranges_expanded)}")
    if missing:
        click.echo("Missing data for:")
        for m in missing:
            click.echo(f"  - {m}")


if __name__ == "__main__":
    main()
