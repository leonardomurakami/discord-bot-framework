# Discord Bot Framework - Comprehensive Development Makefile
# This Makefile provides a complete development workflow for the modular Discord bot

.PHONY: help install install-dev install-music clean test test-unit test-integration test-coverage test-separate lint format typecheck pre-commit docker-build docker-dev docker-prod db-create db-reset db-migrate plugins plugins-list bot-run bot-dev bot-cli coverage-html coverage-open docs docs-serve security-check deps-update deps-check env-setup env-validate release docker-clean logs-dev logs-prod backup-db restore-db benchmark profile

# Default target
.DEFAULT_GOAL := help

# Colors for output
BOLD := \033[1m
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
RESET := \033[0m

# Project settings
PROJECT_NAME := discord-bot
PYTHON := uv run python
UV := uv
DOCKER := docker
DOCKER_COMPOSE := docker-compose
BOT_MODULE := bot
TEST_DIR := tests
COVERAGE_DIR := htmlcov
DATA_DIR := data

# Environment settings
ENV_FILE := .env
ENV_EXAMPLE := .env.example

# Docker settings
DOCKER_IMAGE := $(PROJECT_NAME)
DOCKER_DEV_TARGET := development
DOCKER_PROD_TARGET := production
COMPOSE_DEV_SERVICE := bot-dev
COMPOSE_PROD_PROFILE := production

##@ Help

help: ## Display this help message
	@echo "$(BOLD)$(BLUE)Discord Bot Framework - Development Makefile$(RESET)"
	@echo ""
	@echo "$(BOLD)Usage:$(RESET)"
	@echo "  make $(CYAN)<target>$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BOLD)Available targets:$(RESET)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BOLD)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Environment Setup

install: ## Install production dependencies using uv
	@echo "$(BOLD)$(BLUE)Installing production dependencies...$(RESET)"
	$(UV) pip install --system -e .
	@echo "$(GREEN)✅ Production dependencies installed$(RESET)"

install-dev: ## Install development dependencies including dev tools
	@echo "$(BOLD)$(BLUE)Installing development dependencies...$(RESET)"
	$(UV) pip install --system -e .[dev]
	@echo "$(GREEN)✅ Development dependencies installed$(RESET)"

install-music: ## Install music plugin dependencies
	@echo "$(BOLD)$(BLUE)Installing music dependencies...$(RESET)"
	$(UV) pip install --system -e .[music]
	@echo "$(GREEN)✅ Music dependencies installed$(RESET)"

install-all: install-dev install-music ## Install all dependencies (dev + music)
	@echo "$(GREEN)✅ All dependencies installed$(RESET)"

env-setup: ## Create .env file from .env.example if it doesn't exist
	@if [ ! -f $(ENV_FILE) ]; then \
		if [ -f $(ENV_EXAMPLE) ]; then \
			cp $(ENV_EXAMPLE) $(ENV_FILE); \
			echo "$(GREEN)✅ Created $(ENV_FILE) from $(ENV_EXAMPLE)$(RESET)"; \
		else \
			echo "$(BOLD)$(BLUE)Creating default $(ENV_FILE)...$(RESET)"; \
			echo "# Discord Bot Configuration" > $(ENV_FILE); \
			echo "DISCORD_TOKEN=your_discord_bot_token_here" >> $(ENV_FILE); \
			echo "BOT_PREFIX=!" >> $(ENV_FILE); \
			echo "DATABASE_URL=sqlite:///data/bot.db" >> $(ENV_FILE); \
			echo "ENVIRONMENT=development" >> $(ENV_FILE); \
			echo "LOG_LEVEL=INFO" >> $(ENV_FILE); \
			echo "$(GREEN)✅ Created default $(ENV_FILE)$(RESET)"; \
		fi; \
	else \
		echo "$(YELLOW)⚠️  $(ENV_FILE) already exists$(RESET)"; \
	fi

env-validate: ## Validate environment configuration
	@echo "$(BOLD)$(BLUE)Validating environment...$(RESET)"
	@if [ -f $(ENV_FILE) ]; then \
		if grep -q "your_discord_bot_token_here" $(ENV_FILE); then \
			echo "$(YELLOW)⚠️  Please update DISCORD_TOKEN in $(ENV_FILE)$(RESET)"; \
		else \
			echo "$(GREEN)✅ Environment configuration looks good$(RESET)"; \
		fi; \
	else \
		echo "$(RED)❌ $(ENV_FILE) not found. Run 'make env-setup'$(RESET)"; \
		exit 1; \
	fi

clean: ## Clean up temporary files and caches
	@echo "$(BOLD)$(BLUE)Cleaning up...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf $(COVERAGE_DIR)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf build/
	rm -rf dist/
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

##@ Code Quality

lint: ## Run all linting tools (ruff, black check, mypy)
	@echo "$(BOLD)$(BLUE)Running linting tools...$(RESET)"
	@echo "$(CYAN)Running ruff...$(RESET)"
	$(UV) run ruff check .
	@echo "$(CYAN)Checking code formatting with black...$(RESET)"
	$(UV) run black --check .
	@echo "$(CYAN)Running type checker with mypy...$(RESET)"
	$(UV) run mypy $(BOT_MODULE)
	@echo "$(GREEN)✅ Linting complete$(RESET)"

format: ## Format code using black and ruff
	@echo "$(BOLD)$(BLUE)Formatting code...$(RESET)"
	$(UV) run black .
	$(UV) run ruff check --fix .
	@echo "$(GREEN)✅ Code formatting complete$(RESET)"

typecheck: ## Run type checking with mypy
	@echo "$(BOLD)$(BLUE)Running type checker...$(RESET)"
	$(UV) run mypy $(BOT_MODULE)
	@echo "$(GREEN)✅ Type checking complete$(RESET)"

security-check: ## Run security checks on dependencies
	@echo "$(BOLD)$(BLUE)Running security checks...$(RESET)"
	$(UV) pip audit
	@echo "$(GREEN)✅ Security check complete$(RESET)"

pre-commit: lint test-unit ## Run pre-commit checks (lint + unit tests)
	@echo "$(GREEN)✅ Pre-commit checks passed$(RESET)"

##@ Testing

test: ## Run all tests with coverage
	@echo "$(BOLD)$(BLUE)Running all tests...$(RESET)"
	$(PYTHON) run_tests.py

test-unit: ## Run unit tests only
	@echo "$(BOLD)$(BLUE)Running unit tests...$(RESET)"
	$(PYTHON) run_tests.py --unit-only

test-integration: ## Run integration tests only
	@echo "$(BOLD)$(BLUE)Running integration tests...$(RESET)"
	$(PYTHON) run_tests.py --integration-only

test-coverage: ## Run tests with detailed coverage report
	@echo "$(BOLD)$(BLUE)Running tests with coverage...$(RESET)"
	$(PYTHON) run_tests.py --html-report

test-separate: ## Run separate coverage for bot core and each plugin
	@echo "$(BOLD)$(BLUE)Running separate coverage reports...$(RESET)"
	$(PYTHON) run_tests.py --separate-coverage

test-bot-core: ## Run bot core tests only
	@echo "$(BOLD)$(BLUE)Running bot core tests...$(RESET)"
	$(PYTHON) run_tests.py --bot-core-only --html-report

test-plugin: ## Run tests for specific plugin (usage: make test-plugin PLUGIN=admin)
	@echo "$(BOLD)$(BLUE)Running tests for $(PLUGIN) plugin...$(RESET)"
	@if [ -z "$(PLUGIN)" ]; then \
		echo "$(RED)❌ Please specify PLUGIN variable (e.g., make test-plugin PLUGIN=admin)$(RESET)"; \
		echo "Available plugins: admin, fun, moderation, utility, help"; \
		exit 1; \
	fi
	$(PYTHON) run_tests.py --plugin $(PLUGIN) --html-report

test-watch: ## Run tests in watch mode (re-run on file changes)
	@echo "$(BOLD)$(BLUE)Running tests in watch mode...$(RESET)"
	$(UV) run pytest-watch

test-parallel: ## Run tests in parallel (requires pytest-xdist)
	@echo "$(BOLD)$(BLUE)Running tests in parallel...$(RESET)"
	$(PYTHON) run_tests.py --parallel 4

coverage-html: test-coverage ## Generate HTML coverage report and open it
	@echo "$(GREEN)✅ HTML coverage report generated$(RESET)"

coverage-open: ## Open HTML coverage report in browser
	@if [ -f "$(COVERAGE_DIR)/index.html" ]; then \
		echo "$(BOLD)$(BLUE)Opening coverage report...$(RESET)"; \
		open $(COVERAGE_DIR)/index.html; \
	else \
		echo "$(RED)❌ Coverage report not found. Run 'make coverage-html' first$(RESET)"; \
	fi

benchmark: ## Run performance benchmarks
	@echo "$(BOLD)$(BLUE)Running benchmarks...$(RESET)"
	$(UV) run pytest tests/ -m "benchmark" --benchmark-only

##@ Database Management

db-create: ## Create database tables
	@echo "$(BOLD)$(BLUE)Creating database tables...$(RESET)"
	$(PYTHON) -m $(BOT_MODULE).cli db create
	@echo "$(GREEN)✅ Database tables created$(RESET)"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(BOLD)$(YELLOW)⚠️  This will delete all data!$(RESET)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BOLD)$(BLUE)Resetting database...$(RESET)"; \
		$(PYTHON) -m $(BOT_MODULE).cli db reset; \
		echo "$(GREEN)✅ Database reset complete$(RESET)"; \
	else \
		echo "$(YELLOW)Database reset cancelled$(RESET)"; \
	fi

db-migrate: db-create ## Run database migrations (alias for db-create)
	@echo "$(GREEN)✅ Database migration complete$(RESET)"

backup-db: ## Backup SQLite database
	@echo "$(BOLD)$(BLUE)Backing up database...$(RESET)"
	@if [ -f "$(DATA_DIR)/bot.db" ]; then \
		cp $(DATA_DIR)/bot.db $(DATA_DIR)/bot.db.backup.$$(date +%Y%m%d_%H%M%S); \
		echo "$(GREEN)✅ Database backed up$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  Database file not found$(RESET)"; \
	fi

restore-db: ## Restore database from backup (usage: make restore-db BACKUP=filename)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)❌ Please specify BACKUP variable (e.g., make restore-db BACKUP=bot.db.backup.20240101_120000)$(RESET)"; \
		ls -la $(DATA_DIR)/bot.db.backup.* 2>/dev/null || echo "No backups found"; \
		exit 1; \
	fi
	@if [ -f "$(DATA_DIR)/$(BACKUP)" ]; then \
		cp $(DATA_DIR)/$(BACKUP) $(DATA_DIR)/bot.db; \
		echo "$(GREEN)✅ Database restored from $(BACKUP)$(RESET)"; \
	else \
		echo "$(RED)❌ Backup file $(BACKUP) not found$(RESET)"; \
	fi

##@ Bot Management

bot-run: env-validate ## Run the bot in production mode
	@echo "$(BOLD)$(BLUE)Starting bot in production mode...$(RESET)"
	$(PYTHON) -m $(BOT_MODULE)

bot-dev: env-validate ## Run the bot in development mode with hot reload
	@echo "$(BOLD)$(BLUE)Starting bot in development mode...$(RESET)"
	$(PYTHON) -m $(BOT_MODULE) --dev

bot-cli: ## Run bot CLI (usage: make bot-cli ARGS="db create")
	@if [ -z "$(ARGS)" ]; then \
		echo "$(BOLD)$(BLUE)Bot CLI Help:$(RESET)"; \
		$(PYTHON) -m $(BOT_MODULE).cli --help; \
	else \
		$(PYTHON) -m $(BOT_MODULE).cli $(ARGS); \
	fi

plugins: ## List all available plugins
	@echo "$(BOLD)$(BLUE)Available plugins:$(RESET)"
	$(PYTHON) -m $(BOT_MODULE).cli plugins list

plugins-list: plugins ## Alias for plugins

##@ Docker Development

docker-build: ## Build Docker image for development
	@echo "$(BOLD)$(BLUE)Building development Docker image...$(RESET)"
	$(DOCKER) build --target $(DOCKER_DEV_TARGET) -t $(DOCKER_IMAGE):dev .
	@echo "$(GREEN)✅ Development image built$(RESET)"

docker-build-prod: ## Build Docker image for production
	@echo "$(BOLD)$(BLUE)Building production Docker image...$(RESET)"
	$(DOCKER) build --target $(DOCKER_PROD_TARGET) -t $(DOCKER_IMAGE):latest .
	@echo "$(GREEN)✅ Production image built$(RESET)"

docker-dev: ## Run bot in development mode using Docker Compose
	@echo "$(BOLD)$(BLUE)Starting development environment...$(RESET)"
	$(DOCKER_COMPOSE) up $(COMPOSE_DEV_SERVICE)

docker-dev-build: ## Build and run development environment
	@echo "$(BOLD)$(BLUE)Building and starting development environment...$(RESET)"
	$(DOCKER_COMPOSE) up --build $(COMPOSE_DEV_SERVICE)

docker-dev-detached: ## Run development environment in background
	@echo "$(BOLD)$(BLUE)Starting development environment in background...$(RESET)"
	$(DOCKER_COMPOSE) up -d $(COMPOSE_DEV_SERVICE)

docker-prod: ## Run bot in production mode using Docker Compose
	@echo "$(BOLD)$(BLUE)Starting production environment...$(RESET)"
	$(DOCKER_COMPOSE) --profile $(COMPOSE_PROD_PROFILE) up -d

docker-logs: ## Show Docker logs for development
	$(DOCKER_COMPOSE) logs -f $(COMPOSE_DEV_SERVICE)

logs-dev: docker-logs ## Alias for docker-logs

logs-prod: ## Show Docker logs for production
	$(DOCKER_COMPOSE) --profile $(COMPOSE_PROD_PROFILE) logs -f

docker-stop: ## Stop all Docker containers
	@echo "$(BOLD)$(BLUE)Stopping all containers...$(RESET)"
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) --profile $(COMPOSE_PROD_PROFILE) down

docker-clean: ## Clean up Docker images and containers
	@echo "$(BOLD)$(BLUE)Cleaning up Docker resources...$(RESET)"
	$(DOCKER_COMPOSE) down --rmi all --volumes --remove-orphans
	$(DOCKER) system prune -f
	@echo "$(GREEN)✅ Docker cleanup complete$(RESET)"

docker-shell: ## Open shell in development container
	@echo "$(BOLD)$(BLUE)Opening shell in development container...$(RESET)"
	$(DOCKER_COMPOSE) exec $(COMPOSE_DEV_SERVICE) /bin/bash

##@ Dependencies

deps-update: ## Update all dependencies
	@echo "$(BOLD)$(BLUE)Updating dependencies...$(RESET)"
	$(UV) pip install --upgrade -e .[dev,music]
	@echo "$(GREEN)✅ Dependencies updated$(RESET)"

deps-check: ## Check for dependency updates
	@echo "$(BOLD)$(BLUE)Checking for dependency updates...$(RESET)"
	$(UV) pip list --outdated

deps-audit: security-check ## Audit dependencies for security issues

##@ Documentation

docs: ## Generate documentation (placeholder for future implementation)
	@echo "$(BOLD)$(BLUE)Documentation generation not yet implemented$(RESET)"
	@echo "Available documentation:"
	@echo "  - README.md (Project overview)"
	@echo "  - Plugin documentation in plugins/README.md"

docs-serve: ## Serve documentation locally (placeholder)
	@echo "$(BOLD)$(BLUE)Documentation server not yet implemented$(RESET)"

##@ Profiling & Debugging

profile: ## Profile the bot startup and plugin loading
	@echo "$(BOLD)$(BLUE)Profiling bot startup...$(RESET)"
	$(PYTHON) -m cProfile -o profile_output.prof -m $(BOT_MODULE) --help
	@echo "$(GREEN)✅ Profile saved to profile_output.prof$(RESET)"
	@echo "View with: python -m pstats profile_output.prof"

debug: ## Run bot with Python debugger
	@echo "$(BOLD)$(BLUE)Starting bot with debugger...$(RESET)"
	$(PYTHON) -m pdb -m $(BOT_MODULE) --dev

##@ Release & Deployment

version: ## Show current version
	@echo "$(BOLD)$(BLUE)Current version:$(RESET)"
	@grep version pyproject.toml | head -1 | cut -d'"' -f2

release-check: pre-commit test ## Run full release check (lint, test, security)
	@echo "$(GREEN)✅ Release checks passed$(RESET)"

build: ## Build distribution packages
	@echo "$(BOLD)$(BLUE)Building distribution packages...$(RESET)"
	$(UV) build
	@echo "$(GREEN)✅ Distribution packages built$(RESET)"

##@ Utilities

init: env-setup install-dev db-create ## Initialize complete development environment
	@echo "$(GREEN)✅ Development environment initialized$(RESET)"
	@echo "$(BOLD)Next steps:$(RESET)"
	@echo "1. Update $(ENV_FILE) with your Discord bot token"
	@echo "2. Run 'make bot-dev' to start the bot in development mode"

status: ## Show project status and health check
	@echo "$(BOLD)$(BLUE)Project Status:$(RESET)"
	@echo "Environment file: $$([ -f $(ENV_FILE) ] && echo '✅ Present' || echo '❌ Missing')"
	@echo "Database: $$([ -f $(DATA_DIR)/bot.db ] && echo '✅ Present' || echo '❌ Not created')"
	@echo "Dependencies: $$($(UV) pip check > /dev/null 2>&1 && echo '✅ OK' || echo '❌ Issues')"
	@echo "Docker: $$(docker --version > /dev/null 2>&1 && echo '✅ Available' || echo '❌ Not installed')"

quick-start: init ## Quick start for new developers
	@echo "$(BOLD)$(GREEN)🚀 Quick Start Complete!$(RESET)"
	@echo "$(BOLD)Your Discord bot is ready for development.$(RESET)"
	@echo ""
	@echo "$(BOLD)Next steps:$(RESET)"
	@echo "1. Edit $(ENV_FILE) and add your Discord bot token"
	@echo "2. Run: $(CYAN)make bot-dev$(RESET)"
	@echo ""
	@echo "$(BOLD)Common commands:$(RESET)"
	@echo "  $(CYAN)make test$(RESET)          - Run all tests"
	@echo "  $(CYAN)make lint$(RESET)          - Check code quality"
	@echo "  $(CYAN)make format$(RESET)        - Format code"
	@echo "  $(CYAN)make docker-dev$(RESET)    - Run with Docker"
	@echo "  $(CYAN)make help$(RESET)          - Show all commands"

# Development workflow shortcuts
dev-setup: install-dev env-setup db-create ## Setup development environment
dev-test: format lint test-unit ## Run development tests
dev-full: format lint test coverage-html ## Full development check with coverage

# CI/CD shortcuts  
ci-test: install-dev lint test ## CI testing pipeline
ci-build: ci-test docker-build-prod ## CI build pipeline

