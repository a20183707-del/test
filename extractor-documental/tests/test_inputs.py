import io
import zipfile

import pytest

from bsg_extractor.inputs import (DOCX_MIME, MAX_DOCUMENT_BYTES, document_parts,
                                  from_text, read_document)


def docx(xml, media=False):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
        if media:
            archive.writestr("word/media/image1.png", b"unused")
    return output.getvalue()


def test_text_source_is_preserved_and_metadata_is_not_prompt():
    source = read_document(b"Documento: muestra", "entrada.txt", metadata={"expected": "no incluir"})
    assert source.text == "Documento: muestra"
    assert len(source.sha256) == 64
    assert "no incluir" not in str(document_parts(source))
    assert from_text("\n Texto \n").text == "\n Texto \n"


def test_docx_paragraphs_and_tables_with_image_warning():
    xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Contrato</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>42</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
    source = read_document(docx(xml, True), "documento.docx")
    assert source.mime == DOCX_MIME
    assert source.text == "Contrato\n42"
    assert any("imágenes" in warning for warning in source.warnings)
    assert "inlineData" not in document_parts(source)[0]


def test_docx_entities_and_compression_bomb_rejected():
    with pytest.raises(ValueError, match="XML"):
        read_document(docx('<!DOCTYPE a [<!ENTITY b "x">]><a/>'), "documento.docx")
    with pytest.raises(ValueError, match="descomprimidos"):
        read_document(docx("x" * (25 * 1024 * 1024)), "documento.docx")


@pytest.mark.parametrize("data,name", [(b"", "x.txt"), (b"\x00abc", "x.txt"), (b"abc", "x.pdf"),
                                     (b"%PDF-1.7", "x.html"), (b"PK\x03\x04bad", "x.docx")])
def test_rejects_invalid_or_mismatched_files(data, name):
    with pytest.raises(ValueError):
        read_document(data, name)


def test_size_is_bounded():
    with pytest.raises(ValueError, match="12 MiB"):
        read_document(b"x" * (MAX_DOCUMENT_BYTES + 1), "x.txt")

