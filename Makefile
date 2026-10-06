PYTHON ?= python3
CLANG ?= clang

.PHONY: all check test sanitize demo clean
all: build/json2dir build/json2dir.ll

build/json2dir: src/json2dir.bimbo compiler/bimboc.py runtime/glitter.c
	$(PYTHON) compiler/bimboc.py build $< --clang $(CLANG) -o $@

build/json2dir.ll: src/json2dir.bimbo compiler/bimboc.py
	$(PYTHON) compiler/bimboc.py emit $< -o $@

check:
	$(PYTHON) compiler/bimboc.py check src/json2dir.bimbo
	$(PYTHON) compiler/bimboc.py check examples/hello.bimbo

test: all
	$(PYTHON) -m unittest discover -s tests -v

sanitize: build/json2dir.ll
	$(PYTHON) compiler/bimboc.py build src/json2dir.bimbo --clang $(CLANG) --sanitize -O 1 -o build/json2dir-sanitize
	BIMBO_BINARY=$(CURDIR)/build/json2dir-sanitize $(PYTHON) -m unittest discover -s tests -v

demo: build/json2dir
	$(PYTHON) tests/demo.py

clean:
	rm -rf build
