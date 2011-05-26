SOURCES = contract.py

test:
	$(foreach file,$(SOURCES),python -m doctest $(file))
