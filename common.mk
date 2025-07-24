.PHONY: clean-input clean-output clean-venv input-dir output-dir set-permissions set-timestamps

clean-input:
	rm -fr input

clean-output:
	rm -fr output

clean-venv:
	rm -fr .venv

input-dir:
	mkdir -p input

output-dir:
	mkdir -p output

set-permissions:
	find . -type d -exec chmod 755 {} +
	find . -type f -exec chmod 644 {} +
	find . \
		-path './.git' -prune -o \
		\( -name 'append-c-and-p' -o -name 'filter-between-rows' \) \
		-type f \
		-exec chmod 755 {} +

set-timestamps:
	find . -path './.git' -prune -o -exec touch {} +
