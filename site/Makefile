# taijios.net: the browser build of TaijiOS and its website.
#
#   make -C site          build the web emulator and the site in build/site
#   make -C site test     build, then boot it in private headless Chromium
#   make -C site deploy   test, then upload build/site to the Cloudflare Pages
#                         project behind taijios.net (needs a wrangler login or
#                         CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID)
#   make -C site live     check the deployed site against build/site and boot it
#
# Needs emcc (Emscripten), mk and limbo from Linux/386/bin, ziran, chromium
# and tesseract. The Ziran runtime is compiled to wasm32 from the Ziran
# checkout into its own build directory there.

ROOT := $(abspath ..)
ZIRAN_ROOT ?= $(abspath $(ROOT)/../../ziranlang/ziran)
EMSDK ?= $(HOME)/emsdk
CHROMIUM ?= chromium
URL ?= https://taijios.net/
PAGES_PROJECT ?= taiji
WRANGLER ?= npx --yes wrangler@4.152.0
JOBS ?= 8

export PATH := $(EMSDK)/upstream/emscripten:$(ROOT)/Linux/386/bin:$(PATH)

BUILD := $(ROOT)/build/web
TOOLS := $(BUILD)/tools
ZIRAN_HOST := build/taijios-web-host
ZIRAN_WASM := build/taijios-web-wasm
ZX_ARCHIVE := $(ZIRAN_ROOT)/$(ZIRAN_WASM)/libziran.a
ZX_CFLAGS := -O2 -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm -DZIRAN_COMPACT_EXEC_PLAN \
	-DZIRAN_EXEC_FRAME_RESERVE_BYTES=6291456 -DZIRAN_EXEC_FRAME_RESERVE_MIN=1048576

.PHONY: site emu ziran-wasm tools test deploy live clean

site: emu $(TOOLS)/sitebuild/sitebuild
	cd $(ROOT) && $(TOOLS)/sitebuild/sitebuild build/site $(BUILD)/emu --preinstall lib/preinstall.list

emu: ziran-wasm $(TOOLS)/mkweb/mkweb
	cd $(ROOT) && $(TOOLS)/mkweb/mkweb $(BUILD)/emu $(ZIRAN_ROOT)/include $(ZX_ARCHIVE) $(JOBS)

ziran-wasm:
	$(MAKE) -C $(ZIRAN_ROOT) BUILD_DIR=$(ZIRAN_HOST) $(ZIRAN_HOST)/bin/zi2c
	$(MAKE) -C $(ZIRAN_ROOT) -j$(JOBS) BUILD_DIR=$(ZIRAN_WASM) NATIVE_HOST_ENABLED=0 CC=emcc AR=emar \
		OBJCOPY=true CFLAGS='$(ZX_CFLAGS)' GEN_ZI2C=$(ZIRAN_ROOT)/$(ZIRAN_HOST)/bin/zi2c $(ZIRAN_WASM)/libziran.a

tools: $(TOOLS)/mkweb/mkweb $(TOOLS)/sitebuild/sitebuild $(TOOLS)/sitetest/sitetest

$(TOOLS)/mkweb/mkweb: $(ROOT)/emu/Web/mkweb.zi $(ROOT)/emu/Web/jobs.zi
	cd $(ROOT) && ziran build --target=c --exe --entry mkweb:main --root emu/Web -o build/web/tools/mkweb emu/Web/mkweb.zi

$(TOOLS)/sitebuild/sitebuild: tools/sitebuild.zi tools/rootpack.zi tools/rootlist.zi tools/retired.zi
	cd $(ROOT) && ziran build --target=c --exe --entry sitebuild:main --root site/tools -o build/web/tools/sitebuild site/tools/sitebuild.zi

$(TOOLS)/sitetest/sitetest: tools/sitetest.zi tools/browser.zi tools/ocr.zi tools/serve.zi tools/retired.zi tools/live.zi tools/firefox.zi
	cd $(ROOT) && ziran build --target=c --exe --entry sitetest:main --root site/tools -o build/web/tools/sitetest site/tools/sitetest.zi

test: site $(TOOLS)/sitetest/sitetest
	cd $(ROOT) && $(TOOLS)/sitetest/sitetest build/site $(CHROMIUM)

deploy: test
	cd $(ROOT) && WRANGLER_SEND_METRICS=false $(WRANGLER) pages deploy build/site \
		--project-name=$(PAGES_PROJECT) --branch=master --commit-hash=$$(git rev-parse HEAD) --commit-dirty=true

live: $(TOOLS)/sitetest/sitetest
	cd $(ROOT) && $(TOOLS)/sitetest/sitetest build/site $(CHROMIUM) $(URL)

clean:
	rm -rf $(BUILD) $(ROOT)/build/site $(ROOT)/build/site-test
