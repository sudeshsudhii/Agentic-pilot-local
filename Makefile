.PHONY: reproduce-paper test-unit test-integration test-all lint format backend dev start stop eval run

run:
	python main.py

start:
	python main.py

stop:
	python main.py --stop

eval:
	python main.py --eval

test-unit:
	pytest tests/ -v --ignore=tests/integration

test-integration:
	INTEGRATION_TESTS=1 pytest tests/integration/ -v -s

test-all:
	pytest tests/ -v

lint:
	ruff check backend/

format:
	ruff format backend/

backend:
	python backend/main.py

dev:
	cd frontend && npm run dev

# Regenerate every reported table and the paper from committed data, then check nothing changed.
# Needs the packages in requirements-paper.lock (simulate_v2 imports the recovery engine) and TeX Live.
reproduce-paper:
	python -m benchmarks.simulation.simulate_v2
	python -m benchmarks.simulation.make_tables
	python artifacts/experiments/gate_stats.py > artifacts/results/gate_stats.txt
	python benchmarks/e2e/egress/summarize_egress.py artifacts/results/e2e_smoke_stub
	sh paper/build.sh
	git diff --stat --exit-code -- benchmarks/simulation/out paper/tables artifacts/results
