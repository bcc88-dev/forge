#!/bin/bash
set -e

# CLIDE - AI coding agent that never forgets
# Installer: curl -fsSL https://clide-cli.vercel.app/install.sh | bash

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}${BOLD}"
cat << "EOF"
  ______           _
 |  ____|         | |
 | |__   ___  _ __| |___
 |  __| / _ \| '__| / __|
 | |___| (_) | |  | \__ \
 |______\___/|_|  |_|___/
EOF
echo -e "${NC}"
echo -e "${BOLD}CLIDE - The AI coding agent that never forgets${NC}"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${YELLOW}Python 3.10+ is required. Installing...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y python3 python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-pip
        else
            echo "Please install Python 3.10+ manually: https://python.org"
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install python@3
        else
            echo "Please install Python 3.10+ manually: https://python.org"
            exit 1
        fi
    else
        echo "Please install Python 3.10+ manually: https://python.org"
        exit 1
    fi
fi

echo -e "${CYAN}Installing clide-cli...${NC}"

if command -v pip3 &> /dev/null; then
    pip3 install forge-cli
elif command -v pip &> /dev/null; then
    pip install forge-cli
else
    $PYTHON -m pip install forge-cli
fi

echo ""
echo -e "${GREEN}${BOLD}CLIDE installed!${NC}"
echo ""
echo "Run:"
echo -e "  ${CYAN}forge${NC}                    # Interactive mode"
echo -e "  ${CYAN}forge --help${NC}              # All commands"
echo -e "  ${CYAN}forge providers${NC}           # Check available providers"
echo -e "  ${CYAN}forge config --help${NC}       # Configure settings"
echo ""
