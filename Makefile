.PHONY: run check smoke-busqueda smoke-checkout ai-bootstrap context-digest

run:
	./run.sh

check:
	python3 -m py_compile test_sky.py cli.py gui.py

smoke-busqueda:
	venv/bin/python -u test_sky.py --market PE --tipo-viaje ONE_WAY --headless --slow-mo 0 --checkpoint BUSQUEDA

smoke-checkout:
	venv/bin/python -u test_sky.py --market PE --tipo-viaje ONE_WAY --headless --slow-mo 0 --checkpoint CHECKOUT

ai-bootstrap:
	./scripts/agent_bootstrap.sh

context-digest:
	./scripts/context_digest.sh
