#!/usr/bin/env bash
#
# test_workflow_simulation.sh — VNS-CI-SAFETY-HARDENING-001
#
# Test LOGIC của deploy.yml KHÔNG chạy workflow thật (tránh restart production).
# Mỗi scenario mock 1 bước fail và verify workflow dừng/rollback đúng,
# MÔ PHỎNG CHÍNH XÁC hành vi workflow thật (step gating + health gate).
#
# Chạy: bash test_workflow_simulation.sh
# KHÔNG chạy trên EC2 production — chỉ test logic cục bộ.
#
# Scenarios (Sol R1 yêu cầu):
#   1. Dependency fail trước sync (no rollback — fail trước snapshot)
#   2. Deploy thành công
#   3. Health fail (HTTP 200 + healthy=false) → rollback
#   4. pip fail → PM2 không chạy (step gating)
#   5. rsync fail → pip + PM2 không chạy (step gating)
#   6. Production venv missing → fail-closed (dependency preflight)

set -euo pipefail

PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MOCK_DIR=$(mktemp -d)
trap 'rm -rf "$MOCK_DIR"' EXIT

# --- Helpers ---

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  ✅ $desc: expected=$expected actual=$actual"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $desc: expected=$expected actual=$actual"
        FAIL=$((FAIL + 1))
    fi
}

# --- Mock deploy.yml steps ---
# Each function returns 0 (success) or 1 (failure), simulating workflow step behavior.
# Global variables track step execution to verify gating.

# Reset state before each scenario
reset_state() {
    RAN_PREFLIGHT=0
    RAN_DEP_PREFLIGHT=0
    RAN_SMOKE=0
    RAN_SNAPSHOT=0
    RAN_RSYNC=0
    RAN_PIP=0
    RAN_PM2=0
    RAN_HEALTH=0
    RAN_ROLLBACK=0
    ROLLBACK_SUCCESS=0
    FAILED_STEP=""
    DEPLOY_SUCCESS=0
}

step_preflight_disk() {
    RAN_PREFLIGHT=1
    return 0
}

# Dependency preflight — now fail-closed if venv missing
step_dependency_preflight() {
    local req_file="$1" venv_exists="$2"
    RAN_DEP_PREFLIGHT=1

    if [ ! -f "$req_file" ]; then
        FAILED_STEP="dependency_preflight"
        return 1
    fi
    local non_comment=$(grep -v '^\s*#' "$req_file" | grep -v '^\s*$' || true)
    if [ -z "$non_comment" ]; then
        FAILED_STEP="dependency_preflight"
        return 1
    fi

    # Fail-closed: venv must exist (R2-F3)
    if [ "$venv_exists" = "no" ]; then
        echo "  [step] dependency preflight: FAIL (production venv missing — fail-closed)"
        FAILED_STEP="dependency_preflight"
        return 1
    fi

    # Simulate pip --dry-run: detect unresolvable package
    if echo "$non_comment" | grep -q "nonexistent-package-xyz"; then
        echo "  [step] dependency preflight: FAIL (No matching distribution)"
        FAILED_STEP="dependency_preflight"
        return 1
    fi
    return 0
}

step_smoke_test() {
    local venv_exists="$2"
    RAN_SMOKE=1
    if [ "$venv_exists" = "no" ]; then
        FAILED_STEP="smoke"
        return 1
    fi
    return 0
}

step_snapshot() {
    RAN_SNAPSHOT=1
    return 0
}

step_rsync() {
    local inject_fail="$1"
    RAN_RSYNC=1
    if [ "$inject_fail" = "rsync_fail" ]; then
        FAILED_STEP="rsync"
        return 1
    fi
    return 0
}

step_pip_install() {
    local req_file="$1" inject_fail="$2"
    RAN_PIP=1
    if [ "$inject_fail" = "pip_fail" ]; then
        FAILED_STEP="pip_install"
        return 1
    fi
    return 0
}

step_pm2_restart() {
    RAN_PM2=1
    return 0
}

# Health gate — now parses healthy field (R2-F1)
step_health_check() {
    local health_http="$1" health_healthy="$2"
    RAN_HEALTH=1
    if [ "$health_http" != "200" ]; then
        FAILED_STEP="health"
        return 1
    fi
    # Must be healthy=true, not just HTTP 200 (Sol R1 finding #1)
    if [ "$health_healthy" != "true" ]; then
        FAILED_STEP="health"
        return 1
    fi
    return 0
}

step_rollback() {
    local rb_health_healthy="$1"
    RAN_ROLLBACK=1
    # Rollback health gate (R3-F1): parse JSON + require healthy=true
    if [ "$rb_health_healthy" = "true" ]; then
        ROLLBACK_SUCCESS=1
    else
        ROLLBACK_SUCCESS=0
    fi
    return 0
}

# --- Workflow simulator ---
# Runs steps in order, with EXACT gating from deploy.yml R3:
#   - pip only if rsync success
#   - PM2 only if rsync + pip success
#   - health only if rsync + pip + PM2 success
#   - rollback if ANY post-snapshot step fails
#   - rollback health gate: parse JSON + require healthy=true
#
# Parameters: req_file venv_exists inject_fail health_http health_healthy rb_health_healthy
simulate_deploy() {
    local req_file="$1" venv_exists="$2" inject_fail="$3" health_http="$4" health_healthy="$5" rb_health_healthy="$6"

    step_preflight_disk || return 1
    step_dependency_preflight "$req_file" "$venv_exists" || return 1
    step_smoke_test "$req_file" "$venv_exists" || return 1
    step_snapshot || return 1

    # rsync (continue-on-error)
    local rsync_ok=1
    step_rsync "$inject_fail" || rsync_ok=0

    # pip only if rsync success (R2-F2 gating)
    local pip_ok=1
    if [ "$rsync_ok" = "1" ]; then
        step_pip_install "$req_file" "$inject_fail" || pip_ok=0
    fi

    # PM2 only if rsync + pip success (R2-F2 gating)
    local pm2_ok=1
    if [ "$rsync_ok" = "1" ] && [ "$pip_ok" = "1" ]; then
        step_pm2_restart || pm2_ok=0
    fi

    # health only if rsync + pip + PM2 success (R2-F2 gating)
    local health_ok=1
    if [ "$rsync_ok" = "1" ] && [ "$pip_ok" = "1" ] && [ "$pm2_ok" = "1" ]; then
        step_health_check "$health_http" "$health_healthy" || health_ok=0
    fi

    # Rollback if ANY post-snapshot step failed
    if [ "$rsync_ok" = "0" ] || [ "$pip_ok" = "0" ] || [ "$pm2_ok" = "0" ] || [ "$health_ok" = "0" ]; then
        step_rollback "$rb_health_healthy"
        return 1
    fi

    DEPLOY_SUCCESS=1
    return 0
}

# ============================================================
# Setup: mock requirements files
# ============================================================
cat > "$MOCK_DIR/requirements_good.txt" << 'EOF'
fastapi
uvicorn
pandas
vnstock_data>=2.0.0
vnstock_pipeline==2.3.2
EOF

cat > "$MOCK_DIR/requirements_bad.txt" << 'EOF'
fastapi
uvicorn
nonexistent-package-xyz==1.0.0
EOF

# ============================================================
# Scenario 1: Dependency fail trước sync (unresolvable package)
# Expect: fail at dependency_preflight, no rollback (before snapshot)
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 1: Dependency fail (unresolvable package)"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_bad.txt" "yes" "none" "200" "true" "true" || true
assert_eq "Deploy failed" "0" "$DEPLOY_SUCCESS"
assert_eq "Failed at dependency_preflight" "dependency_preflight" "$FAILED_STEP"
assert_eq "No rollback (before snapshot)" "0" "$RAN_ROLLBACK"
assert_eq "Snapshot not reached" "0" "$RAN_SNAPSHOT"

# ============================================================
# Scenario 2: Deploy success
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 2: Deploy success"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_good.txt" "yes" "none" "200" "true" "true" || true
assert_eq "Deploy succeeded" "1" "$DEPLOY_SUCCESS"
assert_eq "No failed step" "" "$FAILED_STEP"
assert_eq "No rollback" "0" "$RAN_ROLLBACK"

# ============================================================
# Scenario 3: HTTP 200 + healthy=false → fail/rollback (Sol R1 #1)
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 3: Health fail (HTTP 200 + healthy=false) → rollback"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_good.txt" "yes" "none" "200" "false" "true" || true
assert_eq "Deploy failed" "0" "$DEPLOY_SUCCESS"
assert_eq "Failed at health" "health" "$FAILED_STEP"
assert_eq "Rollback triggered" "1" "$RAN_ROLLBACK"

# ============================================================
# Scenario 4: pip fail → PM2 không chạy (Sol R1 #2)
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 4: pip fail → PM2 not reached"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_good.txt" "yes" "pip_fail" "200" "true" "true" || true
assert_eq "Deploy failed" "0" "$DEPLOY_SUCCESS"
assert_eq "Failed at pip_install" "pip_install" "$FAILED_STEP"
assert_eq "PM2 did NOT run (gated)" "0" "$RAN_PM2"
assert_eq "Health did NOT run (gated)" "0" "$RAN_HEALTH"
assert_eq "Rollback triggered" "1" "$RAN_ROLLBACK"

# ============================================================
# Scenario 5: rsync fail → pip + PM2 không chạy (Sol R1 #2)
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 5: rsync fail → pip + PM2 not reached"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_good.txt" "yes" "rsync_fail" "200" "true" "true" || true
assert_eq "Deploy failed" "0" "$DEPLOY_SUCCESS"
assert_eq "Failed at rsync" "rsync" "$FAILED_STEP"
assert_eq "pip did NOT run (gated)" "0" "$RAN_PIP"
assert_eq "PM2 did NOT run (gated)" "0" "$RAN_PM2"
assert_eq "Health did NOT run (gated)" "0" "$RAN_HEALTH"
assert_eq "Rollback triggered" "1" "$RAN_ROLLBACK"

# ============================================================
# Scenario 6: Production venv missing → fail-closed (R2-F3)
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 6: Production venv missing → fail-closed"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_good.txt" "no" "none" "200" "true" "true" || true
assert_eq "Deploy failed" "0" "$DEPLOY_SUCCESS"
assert_eq "Failed at dependency_preflight (fail-closed)" "dependency_preflight" "$FAILED_STEP"
assert_eq "No rollback (before snapshot)" "0" "$RAN_ROLLBACK"
assert_eq "Snapshot not reached" "0" "$RAN_SNAPSHOT"

# ============================================================
# Scenario 7: Rollback healthy=false → rollback NOT successful (Sol R2 #1)
# Post-rollback endpoint returns HTTP 200 + healthy=false.
# Must NOT report "rollback successful" — must signal manual intervention.
# ============================================================
echo ""
echo "============================================================"
echo "Scenario 7: Rollback healthy=false → rollback failed"
echo "============================================================"
reset_state
simulate_deploy "$MOCK_DIR/requirements_good.txt" "yes" "none" "200" "false" "false" || true
assert_eq "Deploy failed (health gate caught)" "0" "$DEPLOY_SUCCESS"
assert_eq "Rollback ran" "1" "$RAN_ROLLBACK"
assert_eq "Rollback NOT successful (healthy=false)" "0" "$ROLLBACK_SUCCESS"

# ============================================================
# Summary
# ============================================================
echo ""
echo "============================================================"
echo "Summary: $PASS passed, $FAIL failed"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
