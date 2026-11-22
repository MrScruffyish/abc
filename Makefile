# abc - small computer algebra system on top of bcl (bc's math library)
# Copyright (C) 2026 Gunnar Lindholm
# SPDX-License-Identifier: GPL-3.0-or-later

# Location of the bc source tree (https://github.com/gavinhoward/bc): the
# first of ../bc and ../ExternalRepos/bc that exists, unless given.
BC_DIR ?= $(or $(patsubst %/configure.sh,%,$(firstword $(wildcard ../bc/configure.sh ../ExternalRepos/bc/configure.sh))),../bc)
BUILD  ?= build

CXX      ?= c++
CXXFLAGS ?= -O2 -g
# _XOPEN_SOURCE makes LONG_BIT visible, so bcl.h agrees with the library
# on the size of BclBigDig.
WARN     := -std=c++17 -D_XOPEN_SOURCE=700 -Wall -Wextra -Wpedantic
SAN      := -fsanitize=address,undefined -fno-omit-frame-pointer

BC_ABS  := $(abspath $(BC_DIR))
BCL_DIR := $(BUILD)/bcl
BCL_LIB := $(BCL_DIR)/bin/libbcl.a

# Line editing (arrow keys, history) when typing at a terminal, with GNU
# readline (or libedit's compatible version) if it is available.
# make READLINE=no  builds without it.
READLINE ?= $(shell printf '\043include <cstdio>\n\043include <readline/readline.h>\nint main(){return readline("")!=0;}\n' \
              | $(CXX) -x c++ - -lreadline -o /dev/null 2>/dev/null && echo yes || echo no)
ifeq ($(READLINE),yes)
  RL_FLAGS := -DXYZ_READLINE
  RL_LIBS  := -lreadline
endif

SRCS := $(wildcard src/*.cpp)
HDRS := $(wildcard src/*.hpp)
OBJS := $(SRCS:src/%.cpp=$(BUILD)/obj/%.o)
ASAN_OBJS := $(SRCS:src/%.cpp=$(BUILD)/asan/%.o)

EXAMPLES    := $(wildcard examples/*.abc)
EXAMPLE_DIR := $(BUILD)/examples
WORK_LEVEL  ?= methods

# Only the board executable lives outside the build tree; its input and
# the rendered movies are written to build/examples/ with the LaTeX files.
BOARD ?= ../Black-Bored-By-Numbers/board

# ONLY=algebra (or ONLY="algebra sums") selects which examples to build.
ifeq ($(strip $(ONLY)),)
RUN_EXAMPLES := $(EXAMPLES)
else
RUN_EXAMPLES := $(foreach n,$(strip $(ONLY)),$(filter examples/$(n).abc,$(EXAMPLES)))
endif

.PHONY: all help examples movies everything test test-asan clean distclean

all: abc

help:
	@printf '%s\n' \
	  'make                 build abc (default)' \
	  'make help            show this list' \
	  'make examples        LaTeX + board input for every example, in build/examples/' \
	  'make movies          render that input to .mp4 in build/examples/ (slow)' \
	  'make everything      examples + movies' \
	  'make test            golden, CLI and random tests' \
	  'make test-asan       the tests under AddressSanitizer + UBSan' \
	  'make clean           remove abc and build/ (including movies)' \
	  '' \
	  'Add ONLY=name to examples, movies or everything to build one example,' \
	  'e.g. make movies ONLY=numbers. Names: $(patsubst examples/%.abc,%,$(EXAMPLES)).' \
	  'WORK_LEVEL=top|methods|all sets the trace detail (default $(WORK_LEVEL)).' \
	  'BOARD=path/to/board selects the board executable (default $(BOARD)).'

# Build bcl out-of-tree so the bc checkout is never modified.
$(BCL_LIB):
	@test -f $(BC_ABS)/configure.sh || \
	  { echo "bc sources not found in $(BC_ABS); use make BC_DIR=..."; exit 1; }
	mkdir -p $(BCL_DIR)
	cd $(BCL_DIR) && env -u CFLAGS $(BC_ABS)/configure.sh -a -O2 >/dev/null
	$(MAKE) -C $(BCL_DIR)

$(BUILD)/obj/%.o: src/%.cpp $(HDRS) $(BCL_LIB) Makefile
	@mkdir -p $(dir $@)
	$(CXX) $(WARN) $(CXXFLAGS) $(RL_FLAGS) -I$(BC_ABS)/include -c -o $@ $<

$(BUILD)/asan/%.o: src/%.cpp $(HDRS) $(BCL_LIB) Makefile
	@mkdir -p $(dir $@)
	$(CXX) $(WARN) -O1 -g $(SAN) $(RL_FLAGS) -I$(BC_ABS)/include -c -o $@ $<

# rebuild main.o when READLINE changes
RL_STAMP := $(BUILD)/readline-$(READLINE)
$(RL_STAMP):
	@mkdir -p $(BUILD) && rm -f $(BUILD)/readline-* && touch $@
$(BUILD)/obj/main.o $(BUILD)/asan/main.o: $(RL_STAMP)

abc: $(OBJS) $(BCL_LIB)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJS) $(BCL_LIB) $(RL_LIBS)

# Generate all example artifacts into build/examples/: a LaTeX work document
# (and its stdout trace) and board input. With pdflatex installed, the
# documents are also compiled to PDF. The recipes always run and print every
# path written, so "make examples" never looks as if it did nothing.
examples: abc
	@test -n "$(strip $(RUN_EXAMPLES))" || \
	  { echo "no example matches ONLY=$(ONLY)"; exit 1; }
	@mkdir -p $(EXAMPLE_DIR)
	@set -e; for f in $(RUN_EXAMPLES); do \
	  n=$$(basename "$$f" .abc); \
	  ./abc --show-your-work --work-level=$(WORK_LEVEL) \
	    --work-file=$(EXAMPLE_DIR)/$$n.tex "$$f" > $(EXAMPLE_DIR)/$$n.stdout.tex; \
	  echo "wrote $(EXAMPLE_DIR)/$$n.tex"; \
	  ./abc --board-file=$(EXAMPLE_DIR)/abc-$$n.txt \
	    --work-level=$(WORK_LEVEL) "$$f"; \
	  echo "wrote $(EXAMPLE_DIR)/abc-$$n.txt"; \
	done
	@if command -v pdflatex >/dev/null 2>&1; then \
	  set -e; for f in $(RUN_EXAMPLES); do \
	    n=$$(basename "$$f" .abc); \
	    pdflatex -interaction=nonstopmode -halt-on-error \
	      -output-directory=$(EXAMPLE_DIR) $(EXAMPLE_DIR)/$$n.tex >/dev/null; \
	    echo "wrote $(EXAMPLE_DIR)/$$n.pdf"; \
	  done; \
	else \
	  echo "pdflatex not found; skipped PDF compilation"; \
	fi

# Render the board input produced by "examples" into build/examples/.
# This is the slow step; BOARD points at the board executable.
movies: examples
	@test -x $(BOARD) || \
	  { echo "board not found at $(BOARD); use make BOARD=path/to/board"; exit 1; }
	@set -e; for f in $(RUN_EXAMPLES); do \
	  n=$$(basename "$$f" .abc); \
	  $(BOARD) $(EXAMPLE_DIR)/abc-$$n.txt $(EXAMPLE_DIR)/abc-$$n.mp4 \
	    --auto-speed 0 --max-scene-seconds 0 >/dev/null; \
	done

# One command for everything; kept as a separate name for discoverability.
everything: movies

$(BUILD)/abc-asan: $(ASAN_OBJS) $(BCL_LIB)
	$(CXX) $(SAN) -o $@ $(ASAN_OBJS) $(BCL_LIB) $(RL_LIBS)

test: abc
	python3 tests/run_tests.py ./abc
	python3 tests/cli_tests.py ./abc
	python3 tests/random_tests.py ./abc

test-asan: $(BUILD)/abc-asan
	python3 tests/run_tests.py $(BUILD)/abc-asan
	python3 tests/cli_tests.py $(BUILD)/abc-asan
	python3 tests/random_tests.py $(BUILD)/abc-asan --count 60

clean:
	rm -rf abc $(BUILD)/obj $(BUILD)/asan $(BUILD)/abc-asan $(EXAMPLE_DIR)

distclean: clean
	rm -rf $(BUILD)
