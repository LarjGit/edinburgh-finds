#!/usr/bin/env bash
set -euo pipefail

OUT="docgen/_evidence"
rm -rf "$OUT"
mkdir -p "$OUT" "$OUT/manifests"

git rev-parse --show-toplevel > "$OUT/repo_root.txt"
git status --porcelain > "$OUT/git_status.txt" || true
git ls-files > "$OUT/git_ls_files.txt"

( command -v tree >/dev/null && tree -L 5 ) > "$OUT/tree.txt" || (ls -R | head -n 8000) > "$OUT/tree.txt"

CANDIDATES=(
  package.json pnpm-lock.yaml yarn.lock bun.lockb package-lock.json
  tsconfig.json jsconfig.json next.config.js next.config.ts vite.config.* webpack.config.*
  pyproject.toml poetry.lock requirements.txt Pipfile Pipfile.lock setup.py setup.cfg
  go.mod go.sum
  Cargo.toml Cargo.lock
  pom.xml build.gradle build.gradle.kts gradle.properties
  composer.json composer.lock
  Gemfile Gemfile.lock
  mix.exs
  Dockerfile docker-compose.yml compose.yml
  Makefile
  .env.example .env.sample .env.template .env.defaults
  prisma/schema.prisma
  supabase/config.toml
  README.md ARCHITECTURE.md
)
for f in "${CANDIDATES[@]}"; do
  if [ -f "$f" ]; then
    cp "$f" "$OUT/manifests/$(echo "$f" | tr '/' '__')"
  fi
done

rg -n --hidden --no-ignore -S \
  "(^|[^A-Z0-9_])(DATABASE_URL|DIRECT_URL|REDIS_URL|API_KEY|SECRET|TOKEN|SENTRY_DSN|SUPABASE_|AWS_|GCP_|AZURE_)([^A-Z0-9_]|$)" . \
  > "$OUT/rg_env_like.txt" || true

rg -n --hidden --no-ignore -S \
  "localhost:|127\.0\.0\.1|http(s)?://|ws(s)?://" . \
  > "$OUT/rg_urls.txt" || true

rg -n --hidden --no-ignore -S \
  "listen\(|createServer|app\.get|app\.post|router|route|endpoint|grpc|GraphQL|FastAPI|Flask|Django|SpringBoot|express\(|gin\.|chi\." . \
  > "$OUT/rg_interfaces.txt" || true

rg -n --hidden --no-ignore -S \
  "migrate|migration|schema|prisma|typeorm|sequelize|knex|alembic|flyway|liquibase|sqlx|gorm" . \
  > "$OUT/rg_db_schema_migrations.txt" || true

rg -n --hidden --no-ignore -S \
  "cron|schedule|worker|queue|bull|celery|sidekiq|rq|temporal|agenda|hangfire" . \
  > "$OUT/rg_jobs_queues.txt" || true

rg -n --hidden --no-ignore -S \
  "docker|compose|k8s|kubectl|helm|terraform|pulumi|vercel|netlify|render|fly\.io|systemd|nginx" . \
  > "$OUT/rg_ops_deploy.txt" || true

rg -n --hidden --no-ignore -S \
  "log(ger)?|winston|pino|zap|structlog|sentry|opentelemetry|prometheus|grafana|datadog" . \
  > "$OUT/rg_observability.txt" || true

rg -n --hidden --no-ignore -S \
  "if __name__ == .__main__.|def main\(|public static void main|func main\(|int main\(|#!/usr/bin/env|bin/|cmd/" . \
  > "$OUT/rg_entrypoints.txt" || true

echo "Universal evidence bundle written to $OUT/"
