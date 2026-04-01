.PHONY: run check validate-cfg validate-ambientes smoke-busqueda smoke-checkout \
        smoke-tsts smoke-stage ai-bootstrap context-digest

run:
	./run.sh

# Verifica compilación Python + contrato mínimo de flags CLI
check:
	python3 -m py_compile test_sky.py cli.py gui.py
	venv/bin/python -c "from cli import aplicar_args, parse_args; import sys; sys.argv=['t','--market','PE']; cfg=aplicar_args(parse_args()); assert cfg['market']=='PE' and cfg['ambiente']=='qa'"
	venv/bin/python -c "\
from config.pago import MEDIO_PAGO_POR_MARKET, TARJETA_POR_MARKET; \
from config.rutas import LIMPIAR_EVIDENCIAS_ANTIGUAS, SEMANAS_RETENCION_EVIDENCIAS; \
tarjeta_cl=TARJETA_POR_MARKET['CL']; \
assert MEDIO_PAGO_POR_MARKET['CL'] == 'Webpay'; \
assert tarjeta_cl['tipo'] == 'Crédito'; \
assert tarjeta_cl['numero'] == '4051885600446623'; \
assert tarjeta_cl['cvv'] == '123'; \
assert tarjeta_cl['rut'] == '11.111.111-1'; \
assert tarjeta_cl['clave'] == '123'; \
assert LIMPIAR_EVIDENCIAS_ANTIGUAS is True; \
assert SEMANAS_RETENCION_EVIDENCIAS == 2; \
print('CL Webpay defaults OK')"
	@echo "✅ check OK"

# Verifica que los 3 ambientes generan URLs distintas (no requiere browser)
validate-ambientes:
	venv/bin/python -c "\
from config.pago import get_urls_por_market; \
qa=get_urls_por_market('qa')['PE']; \
tsts=get_urls_por_market('tsts')['PE']; \
stage=get_urls_por_market('stage')['PE']; \
assert 'initial-sale-qa' in qa; \
assert 'initial-sale-tsts' in tsts; \
assert 'initial-sale-stage' in stage; \
print('QA   :', qa); print('TSTS :', tsts); print('Stage:', stage); print('✅ OK')"

smoke-busqueda:
	venv/bin/python -u test_sky.py --market PE --ambiente qa --tipo-viaje ONE_WAY --headless --slow-mo 0 --checkpoint BUSQUEDA

smoke-checkout:
	venv/bin/python -u test_sky.py --market PE --ambiente qa --tipo-viaje ONE_WAY --headless --slow-mo 0 --checkpoint CHECKOUT

# Smoke ligero para validar que el ambiente TSTS resuelve URL correcta (no navega)
smoke-tsts:
	venv/bin/python -c "\
import sys; sys.argv=['t','--market','PE','--ambiente','tsts']; \
from cli import aplicar_args, parse_args; cfg=aplicar_args(parse_args()); \
assert 'initial-sale-tsts' in cfg['url'], cfg['url']; \
print('TSTS URL OK:', cfg['url'])"

smoke-stage:
	venv/bin/python -c "\
import sys; sys.argv=['t','--market','PE','--ambiente','stage']; \
from cli import aplicar_args, parse_args; cfg=aplicar_args(parse_args()); \
assert 'initial-sale-stage' in cfg['url'], cfg['url']; \
print('Stage URL OK:', cfg['url'])"

ai-bootstrap:
	./scripts/agent_bootstrap.sh

context-digest:
	./scripts/context_digest.sh
