PYTEST ?= pytest

.PHONY: test test-unit test-integration
test: test-unit test-integration

test-unit:
	$(PYTEST) -q -m "not integration"

test-integration:
	$(PYTEST) -q -m integration
