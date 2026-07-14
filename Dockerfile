FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HOME=/tmp

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        biber \
        ca-certificates \
        default-jre-headless \
        fontconfig \
        fonts-liberation2 \
        ghostscript \
        latexmk \
        libreoffice-writer \
        make \
        pandoc \
        poppler-utils \
        python3 \
        texlive-bibtex-extra \
        texlive-fonts-recommended \
        texlive-lang-cyrillic \
        texlive-latex-extra \
        texlive-pictures \
        texlive-science \
        texlive-xetex \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/latex-to-docx /usr/local/bin/latex-to-docx
COPY scripts/prepare_reference.py /opt/latex-to-docx/prepare_reference.py
COPY filters/ntv.lua /opt/latex-to-docx/ntv.lua
COPY filters/references.lua /opt/latex-to-docx/references.lua
COPY filters/no-links.lua /opt/latex-to-docx/no-links.lua
COPY template/numeric.csl /opt/latex-to-docx/numeric.csl

RUN chmod 0755 /usr/local/bin/latex-to-docx /opt/latex-to-docx/prepare_reference.py

ENV NTV_FILTER=/opt/latex-to-docx/ntv.lua \
    NTV_REFERENCE_FILTER=/opt/latex-to-docx/references.lua \
    NTV_NO_LINKS_FILTER=/opt/latex-to-docx/no-links.lua \
    NTV_CSL=/opt/latex-to-docx/numeric.csl \
    NTV_REFERENCE_PREPARER=/opt/latex-to-docx/prepare_reference.py

WORKDIR /work
ENTRYPOINT ["latex-to-docx"]
