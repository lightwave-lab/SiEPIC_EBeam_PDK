# When running this, your environment should have a variable KLAYOUT_BATCH_MODE


default: from_klayout

from_klayout: main_klayout.py
	( \
		klayout -e -z -r main_klayout.py; \
	)

from_klayout_batch_mode: main_klayout.py
	( \
		klayout -e -zz -r main_klayout.py; \
	)

from_python: main_python.py
	( \
		python main_python.py; \
	)

.PHONY: default from_klayout from_klayout_batch_mode from_python
