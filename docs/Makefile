# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

gh-action_multiversion:
	pip install -r requirements.txt --quiet
	set -x; DIR=$$(pwd); \
	cd /home/${USER}/.local/lib/python3.*/site-packages/sphinxcontrib/..; \
	if ! git apply -R --check $$DIR/.patch/sphinx-versioning.patch; then \
	     git apply $$DIR/.patch/sphinx-versioning.patch; \
	fi

	sphinx-versioning --version

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
