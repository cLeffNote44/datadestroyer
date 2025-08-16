param(
  [ValidateSet('dev','up','up-prod','up-prod-tls','down','seed','test','lint')]
  [string]$Task = 'dev'
)

function Run-Dev { docker compose up --build }
function Up { docker compose up --build -d }
function Up-Prod { docker compose -f docker-compose.prod.yml up --build -d }
function Up-ProdTls { docker compose -f docker-compose.prod.tls.yml up --build -d }
function Down {
  docker compose down -v 2>$null
  docker compose -f docker-compose.prod.yml down -v 2>$null
  docker compose -f docker-compose.prod.tls.yml down -v 2>$null
}
function Seed {
  docker compose exec web python manage.py seed_initial --username admin --email admin@example.com --password 'ChangeMeNow!'
}
function Test { .\.venv\Scripts\python.exe -m pytest -q }
function Lint { .\.venv\Scripts\python.exe -m pre_commit run --all-files }

switch ($Task) {
  'dev' { Run-Dev }
  'up' { Up }
  'up-prod' { Up-Prod }
  'up-prod-tls' { Up-ProdTls }
  'down' { Down }
  'seed' { Seed }
  'test' { Test }
  'lint' { Lint }
}
