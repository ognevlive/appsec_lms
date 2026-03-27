#!/usr/bin/env bash
#
# deploy-labs.sh — Build all CTF Docker images & seed tasks into the database.
#
# Usage:
#   ./scripts/deploy-labs.sh              # build + seed
#   ./scripts/deploy-labs.sh --build      # only build images
#   ./scripts/deploy-labs.sh --seed       # only seed database
#   ./scripts/deploy-labs.sh --hash       # only update flag hashes in task.yaml
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TASKS_DIR="$ROOT_DIR/tasks"
CTF_DIR="$TASKS_DIR/ctf"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

# --------------------------------------------------------------------------
# 1. Compute SHA-256 flag hashes from Dockerfiles and patch task.yaml files
# --------------------------------------------------------------------------
compute_flag_hashes() {
    log "Computing flag hashes from Dockerfiles..."

    for dir in "$CTF_DIR"/*/; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        dockerfile="$dir/Dockerfile"
        taskyaml="$dir/task.yaml"

        [ -f "$dockerfile" ] || { warn "No Dockerfile in $name, skipping hash"; continue; }
        [ -f "$taskyaml" ]   || { warn "No task.yaml in $name, skipping hash"; continue; }

        # Extract FLAG{...} from Dockerfile or app.py
        flag=""

        # Search in Dockerfile first, then app.py
        for src in "$dockerfile" "$dir/app.py"; do
            [ -f "$src" ] || continue
            flag=$(grep -o 'FLAG{[^}]*}' "$src" 2>/dev/null | head -1 || true)
            [ -n "$flag" ] && break
        done

        if [ -z "$flag" ]; then
            warn "$name: no FLAG{...} found, skipping hash"
            continue
        fi

        # Compute SHA-256
        hash=$(echo -n "$flag" | shasum -a 256 | awk '{print $1}')

        # Update task.yaml
        if grep -q 'flag_hash:' "$taskyaml"; then
            sed -i.bak "s|flag_hash:.*|flag_hash: \"$hash\"|" "$taskyaml"
            rm -f "$taskyaml.bak"
            info "$name: flag_hash → ${hash:0:16}..."
        fi
    done

    log "Flag hashes updated."
}

# --------------------------------------------------------------------------
# 2. Build Docker images for all CTF tasks
# --------------------------------------------------------------------------
build_images() {
    log "Building CTF Docker images..."

    local built=0
    local failed=0

    for dir in "$CTF_DIR"/*/; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        dockerfile="$dir/Dockerfile"

        [ -f "$dockerfile" ] || { warn "$name: no Dockerfile, skipping build"; continue; }

        image_name="lms/$name"
        info "Building $image_name ..."

        if docker build -t "$image_name" "$dir" --quiet 2>&1; then
            log "$image_name built successfully"
            ((built++))
        else
            err "$image_name build FAILED"
            ((failed++))
        fi
    done

    echo ""
    log "Build complete: $built succeeded, $failed failed."

    if [ "$failed" -gt 0 ]; then
        return 1
    fi
}

# --------------------------------------------------------------------------
# 3. Seed tasks into database
# --------------------------------------------------------------------------
seed_database() {
    log "Seeding tasks into database..."

    # Check if running inside docker compose or standalone
    if docker compose ps --services 2>/dev/null | grep -q backend; then
        info "Using docker compose exec..."
        docker compose exec backend python seed.py /tasks
    else
        warn "Backend container not running via docker compose."
        info "Trying direct Python execution..."

        if [ -f "$ROOT_DIR/backend/seed.py" ]; then
            cd "$ROOT_DIR/backend"
            python seed.py "$TASKS_DIR"
        else
            err "Cannot find seed.py. Start the backend first:"
            err "  docker compose up -d"
            return 1
        fi
    fi

    log "Database seeded."
}

# --------------------------------------------------------------------------
# 4. Print summary
# --------------------------------------------------------------------------
print_summary() {
    echo ""
    echo "========================================"
    echo "  LMS AppSec — Lab Deployment Summary"
    echo "========================================"
    echo ""

    # Count quizzes
    local quiz_count
    quiz_count=$(find "$TASKS_DIR/quizzes" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  Quizzes:      ${CYAN}$quiz_count${NC}"

    # Count CTF tasks
    local ctf_count
    ctf_count=$(find "$CTF_DIR" -name "task.yaml" 2>/dev/null | wc -l | tr -d ' ')
    echo -e "  CTF tasks:    ${CYAN}$ctf_count${NC}"

    echo -e "  Total:        ${GREEN}$((quiz_count + ctf_count))${NC}"
    echo ""

    # List all tasks with order
    echo "  Tasks by order:"
    echo "  ────────────────────────────────────────────"

    for f in "$TASKS_DIR"/quizzes/*.yaml "$CTF_DIR"/*/task.yaml; do
        [ -f "$f" ] || continue
        local title order type difficulty
        title=$(grep '^title:' "$f" | head -1 | sed 's/title: *"\?\(.*\)"\?/\1/')
        order=$(grep '^order:' "$f" | head -1 | awk '{print $2}')
        type=$(grep '^type:' "$f" | head -1 | awk '{print $2}')
        difficulty=$(grep 'difficulty:' "$f" | head -1 | awk '{print $2}')
        printf "  %3s  %-6s  %-7s  %s\n" "$order" "$type" "$difficulty" "$title"
    done | sort -t' ' -k1 -n

    echo ""

    # Docker images
    echo "  Docker images:"
    echo "  ────────────────────────────────────────────"
    docker images --format "  {{.Repository}}:{{.Tag}}  ({{.Size}})" 2>/dev/null | grep "^  lms/" | sort || echo "  (no images built yet)"

    echo ""
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
main() {
    cd "$ROOT_DIR"

    echo ""
    echo "========================================="
    echo "  LMS AppSec — Lab Deployment Script"
    echo "========================================="
    echo ""

    case "${1:-all}" in
        --hash)
            compute_flag_hashes
            ;;
        --build)
            compute_flag_hashes
            build_images
            ;;
        --seed)
            seed_database
            ;;
        --summary)
            print_summary
            ;;
        all|"")
            compute_flag_hashes
            build_images
            seed_database
            print_summary
            ;;
        *)
            echo "Usage: $0 [--build|--seed|--hash|--summary]"
            exit 1
            ;;
    esac
}

main "$@"
