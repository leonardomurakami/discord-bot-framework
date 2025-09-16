#!/usr/bin/env python3
"""
Test runner script for the Discord bot framework.

This script provides a convenient way to run tests with various options
and automatically generates coverage reports.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd, capture_output=False, show_output=True):
    """Run a shell command and return the result."""
    if show_output:
        pass

    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if show_output:
            if result.stdout:
                pass
            if result.stderr and result.returncode != 0:
                pass
        return result.returncode, result.stdout, result.stderr


def parse_coverage_output(output: str) -> dict[str, str]:
    """Parse coverage output to extract coverage percentage."""
    coverage_info = {}

    # Look for TOTAL line in coverage output
    total_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
    if total_match:
        coverage_info["total"] = total_match.group(1)

    # Look for individual files
    file_matches = re.findall(r"(\S+\.py)\s+\d+\s+\d+\s+(\d+)%", output)
    for file_path, percentage in file_matches:
        coverage_info[file_path] = percentage

    return coverage_info


def parse_test_output(output: str) -> tuple[int, int, int]:
    """Parse test output to extract passed, failed, and total test counts."""
    # Look for patterns like "23 passed, 2 failed" or "46 passed"
    passed = failed = total = 0

    passed_match = re.search(r"(\d+) passed", output)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r"(\d+) failed", output)
    if failed_match:
        failed = int(failed_match.group(1))

    total = passed + failed
    return passed, failed, total


def display_test_results(exit_code: int, stdout: str, stderr: str, component_name: str):
    """Display formatted test results."""
    passed, failed, total = parse_test_output(stdout)
    coverage_info = parse_coverage_output(stdout)

    if exit_code == 0:
        pass
    else:
        pass

    if coverage_info.get("total"):
        pass

    if failed > 0:
        # Look for FAILURES section
        failures_start = stdout.find("FAILURES")
        if failures_start != -1:
            stdout[failures_start : failures_start + 1000]  # Show first 1000 chars
        elif stderr:
            pass


def run_separate_coverage():
    """Run tests with separate coverage for bot core and each plugin."""
    plugins = ["admin", "fun", "moderation", "utility", "help"]

    all_passed = True
    coverage_results = {}
    detailed_results = {}

    # Run bot core tests
    bot_cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/bot/",
        "--cov=bot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/bot_core",
        "--cov-fail-under=70",
        "-v",
    ]

    bot_exit, bot_stdout, bot_stderr = run_command(bot_cmd, capture_output=True, show_output=False)
    coverage_results["bot_core"] = bot_exit == 0
    detailed_results["bot_core"] = (bot_exit, bot_stdout, bot_stderr)

    display_test_results(bot_exit, bot_stdout, bot_stderr, "Bot Core")

    if bot_exit != 0:
        all_passed = False

    # Run each plugin separately
    for plugin in plugins:

        plugin_cmd = [
            "python",
            "-m",
            "pytest",
            f"tests/unit/plugins/{plugin}/",
            f"--cov=plugins/{plugin}",
            "--cov-report=term-missing",
            f"--cov-report=html:htmlcov/plugin_{plugin}",
            "--cov-fail-under=70",
            "-v",
        ]

        plugin_exit, plugin_stdout, plugin_stderr = run_command(plugin_cmd, capture_output=True, show_output=False)
        coverage_results[f"plugin_{plugin}"] = plugin_exit == 0
        detailed_results[f"plugin_{plugin}"] = (
            plugin_exit,
            plugin_stdout,
            plugin_stderr,
        )

        display_test_results(plugin_exit, plugin_stdout, plugin_stderr, f"{plugin.title()} Plugin")

        if plugin_exit != 0:
            all_passed = False

    # Summary

    total_tests = 0
    total_passed = 0
    total_failed = 0

    for component, (_exit_code, stdout, _stderr) in detailed_results.items():
        passed, failed, total = parse_test_output(stdout)
        coverage_info = parse_coverage_output(stdout)

        "✅ PASS" if coverage_results[component] else "❌ FAIL"
        f"{coverage_info.get('total', 'N/A')}%"

        total_tests += total
        total_passed += passed
        total_failed += failed

    for plugin in plugins:
        pass

    if all_passed:
        pass
    else:
        pass

    return 0 if all_passed else 1


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Discord bot tests")

    parser.add_argument(
        "--coverage",
        "-c",
        action="store_true",
        help="Run with coverage reporting (default: True)",
    )

    parser.add_argument("--no-coverage", action="store_true", help="Run without coverage reporting")

    parser.add_argument("--html-report", action="store_true", help="Generate HTML coverage report")

    parser.add_argument("--unit-only", "-u", action="store_true", help="Run only unit tests")

    parser.add_argument(
        "--integration-only",
        "-i",
        action="store_true",
        help="Run only integration tests",
    )

    parser.add_argument(
        "--plugin",
        help="Run tests for specific plugin (admin, fun, moderation, utility, help)",
    )

    parser.add_argument(
        "--bot-core-only",
        action="store_true",
        help="Run only bot core tests with coverage",
    )

    parser.add_argument(
        "--separate-coverage",
        action="store_true",
        help="Generate separate coverage reports for bot core and each plugin",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument("--fail-fast", "-x", action="store_true", help="Stop on first failure")

    parser.add_argument(
        "--parallel",
        "-n",
        type=int,
        help="Run tests in parallel (requires pytest-xdist)",
    )

    parser.add_argument("--markers", "-m", help="Run tests with specific markers (e.g., 'not slow')")

    parser.add_argument("test_path", nargs="?", help="Specific test path to run")

    args = parser.parse_args()

    # Check if we're in the right directory
    if not Path("pytest.ini").exists():
        sys.exit(1)

    # Handle separate coverage mode
    if args.separate_coverage:
        exit_code = run_separate_coverage()
        sys.exit(exit_code)

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    # Add test path
    if args.test_path:
        cmd.append(args.test_path)
    elif args.unit_only:
        cmd.append("tests/unit/")
    elif args.integration_only:
        cmd.append("tests/integration/")
    elif args.bot_core_only:
        cmd.append("tests/unit/bot/")
    elif args.plugin:
        plugin_path = f"tests/unit/plugins/{args.plugin}/"
        if not Path(plugin_path).exists():
            sys.exit(1)
        cmd.append(plugin_path)

    # Add coverage options
    if not args.no_coverage:
        if args.bot_core_only:
            cmd.append("--cov=bot")
        elif args.plugin:
            cmd.append(f"--cov=plugins/{args.plugin}")
        else:
            cmd.extend(["--cov=bot", "--cov=plugins"])

        cmd.append("--cov-report=term-missing")

        if args.html_report:
            if args.bot_core_only:
                cmd.append("--cov-report=html:htmlcov/bot_core")
            elif args.plugin:
                cmd.append(f"--cov-report=html:htmlcov/plugin_{args.plugin}")
            else:
                cmd.append("--cov-report=html:htmlcov")

    # Add other options
    if args.verbose:
        cmd.append("-v")

    if args.fail_fast:
        cmd.append("-x")

    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    if args.markers:
        cmd.extend(["-m", args.markers])

    # Run the tests

    exit_code, stdout, stderr = run_command(cmd, capture_output=True, show_output=False)

    # Display detailed results
    component_name = "All Tests"
    if args.bot_core_only:
        component_name = "Bot Core"
    elif args.plugin:
        component_name = f"{args.plugin.title()} Plugin"
    elif args.test_path:
        component_name = f"Custom ({args.test_path})"

    display_test_results(exit_code, stdout, stderr, component_name)

    if args.html_report and not args.no_coverage:
        if args.bot_core_only:
            pass
        elif args.plugin:
            pass
        else:
            pass

    # Check coverage threshold
    if not args.no_coverage and exit_code == 0:
        threshold_cmd = [
            "python",
            "-m",
            "pytest",
            "--cov=bot",
            "--cov=plugins",
            "--cov-fail-under=70",
            "--cov-report=term",
            "-q",
        ]

        threshold_exit, threshold_stdout, threshold_stderr = run_command(threshold_cmd, capture_output=True, show_output=False)

        if threshold_exit == 0:
            pass
        else:
            coverage_info = parse_coverage_output(threshold_stdout)
            if coverage_info.get("total"):
                pass

    if exit_code == 0:
        pass
    else:
        pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
