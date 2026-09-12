#!/usr/bin/env bash
#
# scripts/ci/filtered-install-check.sh — build each app exactly as its image does.
#
# WHY THIS EXISTS (the #244 class)
# --------------------------------
# `ci.yml` installs the WHOLE monorepo (`npm ci --legacy-peer-deps` at the root).
# The app Dockerfiles do not: each one installs a FILTERED subset of workspaces,
# e.g. admin's is
#
#     npm ci --legacy-peer-deps --workspace=apps/admin \
#            --workspace=packages/ui --workspace=packages/lib
#
# — no `apps/web`. On the root install, npm hoists every workspace's deps into
# the root `node_modules/`, so a package that only `apps/web` declares is still
# resolvable from `apps/admin`. On the filtered install it is simply absent.
#
# That is exactly what broke in #244: `@testing-library/react@16`'s
# `export * from '@testing-library/dom'` resolved to nothing because only
# `apps/web` declared the `@testing-library/dom` peer, `next build` type-checks
# `__tests__/**`, and every `screen` / `waitFor` / `fireEvent` import failed with
# TS2305. CI was green for four days while the admin IMAGE would not build, and
# production kept serving the previous digest.
#
# Any workspace can lean on a sibling's hoisted dependency by accident. The only
# way to see it before a deploy does is to perform the same filtered install the
# image performs, and then the same build — which is what this script does.
#
# HOW IT STAYS IN SYNC WITH THE DOCKERFILES
# -----------------------------------------
# Nothing here is hard-coded. For each app the script READS `<app>/Dockerfile`
# and lifts, verbatim:
#
#   * the `RUN … npm ci … --workspace=…` command  (the workspace filter, the
#     `--legacy-peer-deps` / `--omit=…` flags — whatever is actually written)
#   * the `RUN … npm run build --workspace=…` command
#   * the node major from the builder stage's `FROM node:<major>`
#   * the builder stage's `ARG` / `ENV` names, so the build sees the same
#     variables the image build sees (dummy values — no secrets, and the deploy
#     workflows pass the real ones only to `docker build`)
#
# Edit a Dockerfile and this check follows it on the next run. There is no second
# copy of the workspace list to forget.
#
# It runs in a CLEAN temporary copy of the repo (tracked files only, exported
# from the working tree) so it can never be rescued by a `node_modules/` that the
# image would not have, and never touches the checkout it was invoked from.
#
# USAGE
#   scripts/ci/filtered-install-check.sh admin web   # check these apps
#   scripts/ci/filtered-install-check.sh --list      # apps with a filtered install
#   scripts/ci/filtered-install-check.sh --list-json # the same, as a CI matrix
#   scripts/ci/filtered-install-check.sh --node-major admin
#   scripts/ci/filtered-install-check.sh --node-spec  admin  # for setup-node
#   scripts/ci/filtered-install-check.sh --print admin  # show what was parsed
#   FILTERED_INSTALL_KEEP=1 …                        # keep the temp dir
#
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Dummy values for builder-stage ARGs the Dockerfile declares without a default.
# `ci.yml`'s own "Build web" / "Build admin" steps set none of these at all, so
# anything non-fatal is fine; a URL-shaped placeholder is friendlier than the
# empty string to code that does `new URL(...)`.
DUMMY_URL="https://filtered-install-check.invalid/api/v1"
DUMMY_VALUE="filtered-install-check-dummy"

die() { printf '%s\n' "$*" >&2; exit 1; }

# ── Dockerfile parsing ───────────────────────────────────────────────────────
# Fold `\`-continuations into one logical line and drop comment-only lines,
# exactly as the Docker builder does, so a multi-line RUN reads as one command.
fold_dockerfile() {
  awk '
    { sub(/\r$/, "") }
    /^[ \t]*#/ { next }
    {
      line = $0
      if (buf != "") sub(/^[ \t]+/, "", line)
      if (line ~ /\\[ \t]*$/) {
        sub(/\\[ \t]*$/, "", line)
        buf = buf line
        next
      }
      print buf line
      buf = ""
    }
    END { if (buf != "") print buf }
  ' "$1"
}

# Strip `RUN`, any `--mount=…` / `--network=…` flags, and squeeze whitespace,
# leaving the shell command the image actually executes.
run_command_of() {
  sed -E 's/^[[:space:]]*RUN[[:space:]]+//' \
    | sed -E 's/^(--[a-z-]+=[^[:space:]]+[[:space:]]+)+//' \
    | tr -s ' \t' ' ' \
    | sed -E 's/^ +| +$//g'
}

dockerfile_for() {
  local app="$1" candidate
  for candidate in "$REPO_ROOT/$app/Dockerfile" \
                   "$REPO_ROOT/apps/$app/Dockerfile" \
                   "$REPO_ROOT/packages/$app/Dockerfile"; do
    [ -f "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
  done
  die "no Dockerfile found for '$app' (looked in apps/ and packages/)"
}

has_filtered_install() {
  fold_dockerfile "$1" | grep -Eq '^[[:space:]]*RUN[[:space:]].*npm ci .*--workspace='
}

install_command_of() {
  fold_dockerfile "$1" \
    | grep -E '^[[:space:]]*RUN[[:space:]].*npm ci .*--workspace=' \
    | head -1 | run_command_of
}

build_command_of() {
  fold_dockerfile "$1" \
    | grep -E '^[[:space:]]*RUN[[:space:]].*npm run build .*--workspace=' \
    | head -1 | run_command_of
}

# The builder stage = from the FROM immediately preceding the `npm run build`
# RUN, up to that RUN. Derived positionally, so it does not depend on the stage
# being *named* `builder`.
builder_stage_of() {
  fold_dockerfile "$1" | awk '
    /^[[:space:]]*FROM[[:space:]]/ { n = 0; delete stage }
    { stage[++n] = $0 }
    /^[[:space:]]*RUN[[:space:]].*npm run build .*--workspace=/ {
      for (i = 1; i <= n; i++) print stage[i]
      exit
    }
  '
}

node_major_of() {
  local major
  major="$(builder_stage_of "$1" | sed -nE 's/^[[:space:]]*FROM[[:space:]]+node:([0-9]+).*/\1/p' | head -1)"
  [ -n "$major" ] || die "could not read a node major from the builder stage of $1"
  printf '%s\n' "$major"
}

# The version range to hand `actions/setup-node`. It is `<major+1>`, i.e. "the
# node major the image uses, or the newest older one the runners actually have".
#
# The preference matters because `actions/node-versions` does not build every
# line: today the Dockerfiles say `node:25-alpine` and the runner manifest has
# 20 / 22 / 24 / 26 and no 25 at all, so a literal `25` would fail the job on day
# one and a `>=25` would jump to 26. `<26.0.0` resolves to 25.x the moment the
# runners gain it and to 24.x until then — and 24 ships npm 11, the same npm
# MAJOR as the image's node 25 (npm 11.12.1), which is what governs how
# `npm ci --workspace=…` filters and hoists. That is the part this check is
# about; it is not a substitute for the image build itself.
node_spec_of() {
  printf '<%s.0.0\n' "$(( $(node_major_of "$1") + 1 ))"
}

# Emit `export NAME=value` lines replicating the builder stage's ARG/ENV, in
# Dockerfile order, so `ENV X=$Y` expands against the ARG declared above it —
# the same way the builder resolves it.
build_env_exports_of() {
  builder_stage_of "$1" | awk -v dummy_url="$DUMMY_URL" -v dummy="$DUMMY_VALUE" '
    function emit(name, value) {
      gsub(/"/, "\\\"", value)
      printf "export %s=\"%s\"\n", name, value
    }
    /^[[:space:]]*ARG[[:space:]]/ {
      decl = $0
      sub(/^[[:space:]]*ARG[[:space:]]+/, "", decl)
      eq = index(decl, "=")
      if (eq > 0) {
        emit(substr(decl, 1, eq - 1), substr(decl, eq + 1))
      } else {
        sub(/[[:space:]]+$/, "", decl)
        emit(decl, decl ~ /_URL$/ ? dummy_url : dummy)
      }
      next
    }
    /^[[:space:]]*ENV[[:space:]]/ {
      decl = $0
      sub(/^[[:space:]]*ENV[[:space:]]+/, "", decl)
      n = split(decl, tok, /[[:space:]]+/)
      for (i = 1; i <= n; i++) {
        eq = index(tok[i], "=")
        if (eq <= 0) continue
        name = substr(tok[i], 1, eq - 1)
        value = substr(tok[i], eq + 1)
        gsub(/^"|"$/, "", value)
        emit(name, value)
      }
      next
    }
  '
}

# ── Discovery ────────────────────────────────────────────────────────────────
# Every app/package whose Dockerfile performs a workspace-FILTERED npm install,
# i.e. every image that can be broken by a sibling's hoisted dependency. The CI
# matrix is built from this, so a new such app is guarded the day it lands.
discover_apps() {
  local dockerfile dir
  for dockerfile in "$REPO_ROOT"/apps/*/Dockerfile "$REPO_ROOT"/packages/*/Dockerfile; do
    [ -f "$dockerfile" ] || continue
    has_filtered_install "$dockerfile" || continue
    dir="$(dirname "$dockerfile")"
    basename "$dir"
  done | sort -u
}

# ── The check ────────────────────────────────────────────────────────────────
check_app() {
  local app="$1" dockerfile install_cmd build_cmd env_exports workdir rc=0
  dockerfile="$(dockerfile_for "$app")"
  local rel_dockerfile="${dockerfile#"$REPO_ROOT"/}"

  has_filtered_install "$dockerfile" \
    || die "$rel_dockerfile has no workspace-filtered 'npm ci' — nothing to guard"

  install_cmd="$(install_command_of "$dockerfile")"
  build_cmd="$(build_command_of "$dockerfile")"
  [ -n "$build_cmd" ] \
    || die "$rel_dockerfile has a filtered 'npm ci' but no 'npm run build --workspace=…'"
  env_exports="$(build_env_exports_of "$dockerfile")"

  echo "═══════════════════════════════════════════════════════════════════════"
  echo "  $app — building exactly as $rel_dockerfile does"
  echo "═══════════════════════════════════════════════════════════════════════"
  echo "  install: $install_cmd"
  echo "  build:   $build_cmd"
  if [ -n "$env_exports" ]; then
    echo "  env (names from the builder stage, dummy values):"
    printf '%s\n' "$env_exports" | sed 's/^export /    /'
  fi
  echo

  workdir="$(mktemp -d "${TMPDIR:-/tmp}/filtered-install-$app.XXXXXX")"
  if [ "${FILTERED_INSTALL_KEEP:-0}" = "1" ]; then
    echo "  temp copy: $workdir (kept: FILTERED_INSTALL_KEEP=1)"
  else
    trap 'rm -rf "$workdir"' RETURN
  fi

  # Clean copy: tracked files, read from the WORKING TREE (so a local edit is
  # what gets tested), with no node_modules, no build output, no stray untracked
  # file that the image would never receive.
  ( cd "$REPO_ROOT" && git ls-files -z | tar -c --null -T - -f - ) \
    | ( cd "$workdir" && tar -xf - )

  echo "──→ $install_cmd"
  ( cd "$workdir" && eval "$env_exports" && eval "$install_cmd" ) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo
    echo "FAIL($app): the filtered install itself failed (exit $rc)." >&2
    return "$rc"
  fi

  echo
  echo "──→ $build_cmd"
  ( cd "$workdir" && eval "$env_exports" && eval "$build_cmd" ) || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo
    echo "FAIL($app): '$build_cmd' failed (exit $rc) on the install $rel_dockerfile" >&2
    echo "  performs, while the root install CI uses would have hidden it." >&2
    echo "  Usual cause: a package this workspace imports is declared only in a" >&2
    echo "  SIBLING workspace's package.json and reaches it by hoisting. Declare" >&2
    echo "  it in apps/$app/package.json (that was #244) and commit the" >&2
    echo "  package-lock.json line it produces." >&2
    return "$rc"
  fi

  echo
  echo "OK($app): the image's filtered install builds."
  return 0
}

# ── Entry point ──────────────────────────────────────────────────────────────
case "${1:---help}" in
  --list)
    discover_apps
    exit 0
    ;;
  --list-json)
    discover_apps | awk 'BEGIN { printf "[" } { printf "%s\"%s\"", (NR > 1 ? "," : ""), $0 } END { print "]" }'
    exit 0
    ;;
  --node-major)
    [ $# -eq 2 ] || die "usage: $0 --node-major <app>"
    node_major_of "$(dockerfile_for "$2")"
    exit 0
    ;;
  --node-spec)
    [ $# -eq 2 ] || die "usage: $0 --node-spec <app>"
    node_spec_of "$(dockerfile_for "$2")"
    exit 0
    ;;
  --print)
    [ $# -eq 2 ] || die "usage: $0 --print <app>"
    dockerfile="$(dockerfile_for "$2")"
    echo "dockerfile:  ${dockerfile#"$REPO_ROOT"/}"
    echo "node major:  $(node_major_of "$dockerfile")"
    echo "setup-node:  $(node_spec_of "$dockerfile")"
    echo "install:     $(install_command_of "$dockerfile")"
    echo "build:       $(build_command_of "$dockerfile")"
    echo "build env:"
    build_env_exports_of "$dockerfile" | sed 's/^/  /'
    exit 0
    ;;
  --help|-h)
    sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'
    exit 0
    ;;
esac

failed=()
for app in "$@"; do
  check_app "$app" || failed+=("$app")
  echo
done

if [ ${#failed[@]} -gt 0 ]; then
  echo "FAILED: ${failed[*]}" >&2
  exit 1
fi
echo "All checked apps build on the filtered install their Dockerfile performs."
