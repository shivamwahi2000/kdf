#!/bin/bash
# KDF Databricks Setup Script
#
# This script performs initial setup of KDF in a Databricks workspace:
# 1. Uploads KDF wheel to DBFS
# 2. Uploads runner notebook to workspace
# 3. Creates directory structure in DBFS
#
# Usage:
#   ./databricks_setup.sh
#
# Prerequisites:
#   - Databricks CLI installed and configured
#   - KDF installed locally

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     KDF Databricks Initial Setup                     ║${NC}"
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"

# Check for databricks CLI
if ! command -v databricks &> /dev/null; then
    echo -e "${RED}✗ Databricks CLI not found${NC}"
    echo "Install with: pip install databricks-cli"
    exit 1
fi
echo "  ✓ Databricks CLI found"

# Check for kdf
if ! command -v kdf &> /dev/null; then
    echo -e "${RED}✗ KDF not found${NC}"
    echo "Install with: pip install kdf"
    exit 1
fi
echo "  ✓ KDF found"

# Test databricks connection
if ! databricks workspace ls / &> /dev/null; then
    echo -e "${RED}✗ Cannot connect to Databricks workspace${NC}"
    echo "Configure with: databricks configure --token"
    exit 1
fi
echo "  ✓ Databricks connection OK"

# Create DBFS directory structure
echo ""
echo -e "${YELLOW}[2/5] Creating DBFS directory structure...${NC}"

databricks fs mkdirs dbfs:/kdf
databricks fs mkdirs dbfs:/kdf/configs
databricks fs mkdirs dbfs:/kdf/wheels
databricks fs mkdirs dbfs:/kdf/metadata

echo "  ✓ Created /kdf"
echo "  ✓ Created /kdf/configs"
echo "  ✓ Created /kdf/wheels"
echo "  ✓ Created /kdf/metadata"

# Upload KDF wheel
echo ""
echo -e "${YELLOW}[3/5] Building and uploading KDF wheel...${NC}"

kdf databricks upload-kdf --dbfs-path /kdf/wheels
echo "  ✓ KDF wheel uploaded"

# Upload runner notebook
echo ""
echo -e "${YELLOW}[4/5] Uploading KDF runner notebook...${NC}"

# Create workspace directory
databricks workspace mkdirs /Workspace/kdf || true
databricks workspace mkdirs /Workspace/kdf/notebooks || true

kdf databricks upload-notebook --workspace-path /Workspace/kdf/notebooks/run_kdf_pipeline
echo "  ✓ Runner notebook uploaded"

# Summary
echo ""
echo -e "${YELLOW}[5/5] Setup complete!${NC}"
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Setup Summary                                     ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  DBFS Structure:                                      ║${NC}"
echo -e "${GREEN}║    /kdf/configs    - Pipeline configurations          ║${NC}"
echo -e "${GREEN}║    /kdf/wheels     - KDF wheel file                   ║${NC}"
echo -e "${GREEN}║    /kdf/metadata   - Pipeline run metadata            ║${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}║  Workspace:                                           ║${NC}"
echo -e "${GREEN}║    /Workspace/kdf/notebooks/run_kdf_pipeline          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Upload your pipeline config:"
echo "     kdf databricks upload-config my_pipeline.yaml"
echo ""
echo "  2. Create a workflow:"
echo "     kdf databricks create-workflow my_pipeline.yaml \\"
echo "       --config-path dbfs:/kdf/configs/my_pipeline.yaml \\"
echo "       --schedule '0 0 2 * * ?'"
echo ""
echo "  Or use the deploy command:"
echo "     kdf databricks deploy my_pipeline.yaml --schedule '0 0 2 * * ?'"
echo ""
