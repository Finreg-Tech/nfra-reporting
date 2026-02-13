# =============================================================================
# Clean Architecture Refactoring Script for Fin-LLM-NFRA
# =============================================================================
# Run from project root: .\scripts\refactor_structure.ps1
# 
# WARNING: Commit your changes to Git before running this script!
# =============================================================================

$ErrorActionPreference = "Stop"
Write-Host "=== Starting Clean Architecture Refactoring ===" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# Step 1: Create new directory structure
# -----------------------------------------------------------------------------
Write-Host "`n[1/5] Creating new directory structure..." -ForegroundColor Yellow

$directories = @(
    "config",
    "src",
    "src/api",
    "src/api/routes",
    "src/core",
    "src/core/agents",
    "src/services",
    "src/services/rag",
    "src/services/extraction",
    "src/services/extraction/llm",
    "src/services/database",
    "src/utils",
    "resources",
    "resources/models",
    "resources/prompts",
    "scripts"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------------
# Step 2: Move configuration files
# -----------------------------------------------------------------------------
Write-Host "`n[2/5] Moving configuration files..." -ForegroundColor Yellow

# Root config → config/settings.py
if (Test-Path "config.py") {
    Move-Item -Path "config.py" -Destination "config/settings.py" -Force
    Write-Host "  config.py → config/settings.py" -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# Step 3: Move core logic (Agents → src/core)
# -----------------------------------------------------------------------------
Write-Host "`n[3/5] Moving core logic (Agents → src/core)..." -ForegroundColor Yellow

# State and Workflow go to src/core root
if (Test-Path "Agents/state.py") {
    Move-Item -Path "Agents/state.py" -Destination "src/core/state.py" -Force
    Write-Host "  Agents/state.py → src/core/state.py" -ForegroundColor Green
}

if (Test-Path "Agents/workflow.py") {
    Move-Item -Path "Agents/workflow.py" -Destination "src/core/workflow.py" -Force
    Write-Host "  Agents/workflow.py → src/core/workflow.py" -ForegroundColor Green
}

# Agent modules go to src/core/agents/
$agentFiles = @("gatekeeper.py", "accountant.py", "auditor.py", "quant.py", "publisher.py")
foreach ($file in $agentFiles) {
    if (Test-Path "Agents/$file") {
        Move-Item -Path "Agents/$file" -Destination "src/core/agents/$file" -Force
        Write-Host "  Agents/$file → src/core/agents/$file" -ForegroundColor Green
    }
}

# Prompts and knowledge graph → resources/prompts
if (Test-Path "Agents/prompts.py") {
    Move-Item -Path "Agents/prompts.py" -Destination "resources/prompts/prompts.py" -Force
    Write-Host "  Agents/prompts.py → resources/prompts/prompts.py" -ForegroundColor Green
}

if (Test-Path "Agents/knowledge_graph.json") {
    Move-Item -Path "Agents/knowledge_graph.json" -Destination "resources/prompts/knowledge_graph.json" -Force
    Write-Host "  Agents/knowledge_graph.json → resources/prompts/knowledge_graph.json" -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# Step 4: Move API layer
# -----------------------------------------------------------------------------
Write-Host "`n[4/5] Moving API layer..." -ForegroundColor Yellow

# main.py → server.py
if (Test-Path "api/main.py") {
    Move-Item -Path "api/main.py" -Destination "src/api/server.py" -Force
    Write-Host "  api/main.py → src/api/server.py" -ForegroundColor Green
}

# Route files
$routeFiles = @("ingest.py", "nfra_query.py", "rag_query.py")
foreach ($file in $routeFiles) {
    if (Test-Path "api/$file") {
        Move-Item -Path "api/$file" -Destination "src/api/routes/$file" -Force
        Write-Host "  api/$file → src/api/routes/$file" -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------------
# Step 5: Move services (Infrastructure Layer)
# -----------------------------------------------------------------------------
Write-Host "`n[5/5] Moving services (Infrastructure Layer)..." -ForegroundColor Yellow

# Database (DB → src/services/database)
$dbFiles = @("db_config.py", "db_init.py", "models.py", "__init__.py")
foreach ($file in $dbFiles) {
    if (Test-Path "DB/$file") {
        Move-Item -Path "DB/$file" -Destination "src/services/database/$file" -Force
        Write-Host "  DB/$file → src/services/database/$file" -ForegroundColor Green
    }
}

# RAG services (RAG → src/services/rag)
$ragFiles = Get-ChildItem -Path "RAG" -Filter "*.py" -ErrorAction SilentlyContinue
foreach ($file in $ragFiles) {
    Move-Item -Path $file.FullName -Destination "src/services/rag/$($file.Name)" -Force
    Write-Host "  RAG/$($file.Name) → src/services/rag/$($file.Name)" -ForegroundColor Green
}

# Extraction services (Preprocessing/LLM → src/services/extraction/llm)
$llmFiles = Get-ChildItem -Path "Preprocessing/LLM" -Filter "*.py" -ErrorAction SilentlyContinue
foreach ($file in $llmFiles) {
    Move-Item -Path $file.FullName -Destination "src/services/extraction/llm/$($file.Name)" -Force
    Write-Host "  Preprocessing/LLM/$($file.Name) → src/services/extraction/llm/$($file.Name)" -ForegroundColor Green
}

# Utils
if (Test-Path "Preprocessing/utils.py") {
    Move-Item -Path "Preprocessing/utils.py" -Destination "src/utils/preprocessing.py" -Force
    Write-Host "  Preprocessing/utils.py → src/utils/preprocessing.py" -ForegroundColor Green
}

# Move prompts templates
if (Test-Path "Preprocessing/JSON/prompts") {
    Get-ChildItem -Path "Preprocessing/JSON/prompts" -Filter "*.j2" | ForEach-Object {
        Move-Item -Path $_.FullName -Destination "resources/prompts/$($_.Name)" -Force
        Write-Host "  Preprocessing/JSON/prompts/$($_.Name) → resources/prompts/$($_.Name)" -ForegroundColor Green
    }
}

# ML Models
if (Test-Path "ML_MODELS") {
    Get-ChildItem -Path "ML_MODELS" -Filter "*.pkl" | ForEach-Object {
        Move-Item -Path $_.FullName -Destination "resources/models/$($_.Name)" -Force
        Write-Host "  ML_MODELS/$($_.Name) → resources/models/$($_.Name)" -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------------
# Step 6: Create __init__.py files
# -----------------------------------------------------------------------------
Write-Host "`n[6/6] Creating __init__.py files..." -ForegroundColor Yellow

$initDirs = @(
    "config",
    "src",
    "src/api",
    "src/api/routes",
    "src/core",
    "src/core/agents",
    "src/services",
    "src/services/rag",
    "src/services/extraction",
    "src/services/extraction/llm",
    "src/services/database",
    "src/utils",
    "resources",
    "resources/prompts"
)

foreach ($dir in $initDirs) {
    $initPath = "$dir/__init__.py"
    if (-not (Test-Path $initPath)) {
        New-Item -ItemType File -Path $initPath -Force | Out-Null
        Write-Host "  Created: $initPath" -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------------
# Cleanup empty old directories
# -----------------------------------------------------------------------------
Write-Host "`n[Cleanup] Removing empty old directories..." -ForegroundColor Yellow

$oldDirs = @("Agents", "api", "DB", "RAG", "Preprocessing", "ML_MODELS")
foreach ($dir in $oldDirs) {
    if (Test-Path $dir) {
        $remaining = Get-ChildItem -Path $dir -Recurse -File -ErrorAction SilentlyContinue | 
                     Where-Object { $_.Name -ne "__init__.py" -and $_.Extension -ne ".pyc" }
        if ($remaining.Count -eq 0) {
            Remove-Item -Path $dir -Recurse -Force
            Write-Host "  Removed empty directory: $dir" -ForegroundColor Gray
        } else {
            Write-Host "  Keeping $dir (still has files)" -ForegroundColor Yellow
        }
    }
}

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
Write-Host "`n=== Refactoring Complete ===" -ForegroundColor Cyan
Write-Host @"

NEXT STEPS:
1. Update imports in all Python files (see import_mapping.md)
2. Run: pip install -e .
3. Test with: python -c "from src.core.workflow import run_validation_chain"

"@ -ForegroundColor White
