#!/bin/bash
# Modern KDF Deployment Script using Databricks Asset Bundles
#
# This script deploys KDF using the latest Databricks CLI and Asset Bundles (DABs).
# Replaces the legacy databricks-cli Python package approach.
#
# Usage:
#   ./deploy_bundle.sh <environment>
#
# Examples:
#   ./deploy_bundle.sh dev
#   ./deploy_bundle.sh staging
#   ./deploy_bundle.sh production

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
ENVIRONMENT=${1:-dev}

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    echo -e "${RED}✗ Invalid environment: $ENVIRONMENT${NC}"
    echo "Usage: $0 <environment>"
    echo "Valid environments: dev, staging, production"
    exit 1
fi

echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     KDF Databricks Bundle Deployment                 ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Environment: ${ENVIRONMENT}                                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

# Check for new Databricks CLI
if ! command -v databricks &> /dev/null; then
    echo -e "${RED}✗ Databricks CLI not found${NC}"
    echo "Install with:"
    echo "  curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
    echo ""
    echo "Or download from: https://github.com/databricks/cli/releases"
    exit 1
fi
echo "  ✓ Databricks CLI found: $(databricks --version)"

# Check authentication
if ! databricks auth profiles 2>&1 | grep -q "."; then
    echo -e "${RED}✗ No Databricks profiles configured${NC}"
    echo "Configure with:"
    echo "  databricks auth login --host https://your-workspace.cloud.databricks.com"
    exit 1
fi
echo "  ✓ Databricks CLI authenticated"

# Check git status
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠ Warning: You have uncommitted changes${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo "  ✓ Git status checked"

# Validate bundle
echo ""
echo -e "${YELLOW}[2/6] Validating bundle configuration...${NC}"

databricks bundle validate -t $ENVIRONMENT

echo "  ✓ Bundle validation passed"

# Build artifacts (KDF wheel)
echo ""
echo -e "${YELLOW}[3/6] Building KDF wheel...${NC}"

# Clean old builds
rm -rf dist/ build/ *.egg-info 2>/dev/null || true

# Build wheel
pip wheel . --wheel-dir dist --no-deps

WHEEL_FILE=$(ls dist/*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL_FILE" ]; then
    echo -e "${RED}✗ Wheel build failed${NC}"
    exit 1
fi

echo "  ✓ Wheel built: $WHEEL_FILE"

# Show deployment plan
echo ""
echo -e "${YELLOW}[4/6] Deployment plan:${NC}"
echo ""

# Get bundle info
databricks bundle summary -t $ENVIRONMENT 2>/dev/null || true

echo ""
read -p "Proceed with deployment to $ENVIRONMENT? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Deploy bundle
echo ""
echo -e "${YELLOW}[5/6] Deploying bundle...${NC}"

databricks bundle deploy -t $ENVIRONMENT

echo "  ✓ Bundle deployed successfully"

# Show deployed resources
echo ""
echo -e "${YELLOW}[6/6] Deployment summary:${NC}"
echo ""

# List deployed jobs
echo -e "${BLUE}Deployed Jobs:${NC}"
databricks jobs list --output json | \
    jq -r '.jobs[] | select(.settings.name | contains("KDF '$ENVIRONMENT'")) | "  - \(.settings.name) (ID: \(.job_id))"' 2>/dev/null || \
    echo "  (Unable to list jobs)"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Deployment Complete!                              ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Environment: ${ENVIRONMENT}                                    ║${NC}"
echo -e "${GREEN}║  Bundle Path: /.bundle/kdf/${ENVIRONMENT}                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

echo "Next steps:"
echo "  1. View resources in Databricks UI:"
echo "     Workspace → .bundle → kdf → ${ENVIRONMENT}"
echo ""
echo "  2. Run a job:"
echo "     databricks bundle run -t ${ENVIRONMENT} kdf_medallion_orders"
echo ""
echo "  3. Monitor execution:"
echo "     Workflows → Find your job → View runs"
echo ""
echo "  4. Query metadata:"
echo "     SELECT * FROM delta.\`/kdf/metadata/pipeline_runs\`"
echo "     WHERE environment = '${ENVIRONMENT}'"
echo ""
