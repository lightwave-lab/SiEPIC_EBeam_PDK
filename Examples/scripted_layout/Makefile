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

from_python: main_python.py clear
	@echo "Don't forget to export PYTHONPATH='/path/to/SiEPIC-Tools/klayout_dot_config/python'"
	( \
		python main_python.py; \
	)

test:
	( \
		pytest test_klayout.py; \
		klayout -e -z -r launch_python_test.py; \
	)

clear:
	rm cache/* || true


.PHONY: default from_klayout from_klayout_batch_mode from_python clear
