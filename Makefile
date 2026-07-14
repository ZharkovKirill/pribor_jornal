IMAGE ?= latex-to-ntv:local
INPUT ?= template/article.tex
OUTPUT ?= build/article.docx

.PHONY: all docker-build docx pdf validate clean

all: docx

docker-build:
	docker build --tag "$(IMAGE)" .

docx:
	@mkdir -p "$(dir $(OUTPUT))"
	docker run --rm \
		--user "$$(id -u):$$(id -g)" \
		--volume "$(CURDIR):/work" \
		"$(IMAGE)" "$(INPUT)" "$(OUTPUT)"

pdf:
	@mkdir -p build
	docker run --rm \
		--user "$$(id -u):$$(id -g)" \
		--volume "$(CURDIR):$(CURDIR)" \
		--env INPUT_FILE="$(CURDIR)/$(INPUT)" \
		--entrypoint sh \
		"$(IMAGE)" -c 'latexmk -xelatex -synctex=1 -file-line-error -interaction=nonstopmode -halt-on-error -cd -outdir="$(CURDIR)/build" "$$INPUT_FILE"'

validate: docx
	docker run --rm \
		--user "$$(id -u):$$(id -g)" \
		--volume "$(CURDIR):/work" \
		--entrypoint sh \
		"$(IMAGE)" -c 'unzip -t "/work/$(OUTPUT)" >/dev/null && mkdir -p /tmp/lo /tmp/lo-profile && libreoffice -env:UserInstallation=file:///tmp/lo-profile --headless --convert-to pdf --outdir /tmp/lo "/work/$(OUTPUT)" >/tmp/libreoffice.log 2>&1 && pdfinfo "/tmp/lo/$$(basename "$(OUTPUT)" .docx).pdf" | sed -n "1,12p"'

clean:
	rm -rf build
