#!/usr/bin/env python3
"""
Test runner script for the Discord bot framework.

This script provides a convenient way to run tests with various options
and automatically generates coverage reports.
"""

import sys
import subprocess
import argparse
import re
from pathlib import Path
from typing import Tuple, Dict


def run_command(cmd, capture_output=False, show_output=True):
    """Run a shell command and return the result."""
    if show_output:
        print(f"🚀 Running: {' '.join(cmd)}")
        print("-" * 60)

    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if show_output:
            if result.stdout:
                print(result.stdout)
            if result.stderr and result.returncode != 0:
                print("STDERR:", result.stderr)
        return result.returncode, result.stdout, result.stderr


def parse_coverage_output(output: str) -> Dict[str, str]:
    """Parse coverage output to extract coverage percentage."""
    coverage_info = {}

    # Look for TOTAL line in coverage output
    total_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
    if total_match:
        coverage_info['total'] = total_match.group(1)

    # Look for individual files
    file_matches = re.findall(r'(\S+\.py)\s+\d+\s+\d+\s+(\d+)%', output)
    for file_path, percentage in file_matches:
        coverage_info[file_path] = percentage

    return coverage_info


def parse_test_output(output: str) -> Tuple[int, int, int]:
    """Parse test output to extract passed, failed, and total test counts."""
    # Look for patterns like "23 passed, 2 failed" or "46 passed"
    passed = failed = total = 0

    passed_match = re.search(r'(\d+) passed', output)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r'(\d+) failed', output)
    if failed_match:
        failed = int(failed_match.group(1))

    total = passed + failed
    return passed, failed, total


def display_test_results(exit_code: int, stdout: str, stderr: str, component_name: str):
    """Display formatted test results."""
    passed, failed, total = parse_test_output(stdout)
    coverage_info = parse_coverage_output(stdout)

    print(f"\n📊 {component_name} Results:")
    print("=" * 50)

    if exit_code == 0:
        print(f"✅ Status: PASSED")
    else:
        print(f"❌ Status: FAILED")

    print(f"📈 Tests: {passed} passed, {failed} failed, {total} total")

    if coverage_info.get('total'):
        print(f"📊 Coverage: {coverage_info['total']}%")

    if failed > 0:
        print(f"\n❌ Failure Details:")
        # Look for FAILURES section
        failures_start = stdout.find('FAILURES')
        if failures_start != -1:
            failures_section = stdout[failures_start:failures_start + 1000]  # Show first 1000 chars
            print(failures_section[:1000] + "..." if len(failures_section) > 1000 else failures_section)
        elif stderr:
            print(stderr[:500] + "..." if len(stderr) > 500 else stderr)

    print("-" * 50)


def run_separate_coverage():
    """Run tests with separate coverage for bot core and each plugin."""
    plugins = ["admin", "fun", "moderation", "utility", "help"]

    print("🧪 Running separate coverage reports...")
    print("=" * 80)

    all_passed = True
    coverage_results = {}
    detailed_results = {}

    # Run bot core tests
    print("\n🏗️  Testing Bot Core...")
    bot_cmd = [
        "python", "-m", "pytest",
        "tests/unit/bot/",
        "--cov=bot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/bot_core",
        "--cov-fail-under=70",
        "-v"
    ]

    bot_exit, bot_stdout, bot_stderr = run_command(bot_cmd, capture_output=True, show_output=False)
    coverage_results["bot_core"] = bot_exit == 0
    detailed_results["bot_core"] = (bot_exit, bot_stdout, bot_stderr)

    display_test_results(bot_exit, bot_stdout, bot_stderr, "Bot Core")

    if bot_exit != 0:
        all_passed = False

    # Run each plugin separately
    for plugin in plugins:
        print(f"\n🔌 Testing {plugin.title()} Plugin...")

        plugin_cmd = [
            "python", "-m", "pytest",
            f"tests/unit/plugins/{plugin}/",
            f"--cov=plugins/{plugin}",
            "--cov-report=term-missing",
            f"--cov-report=html:htmlcov/plugin_{plugin}",
            "--cov-fail-under=70",
            "-v"
        ]

        plugin_exit, plugin_stdout, plugin_stderr = run_command(plugin_cmd, capture_output=True, show_output=False)
        coverage_results[f"plugin_{plugin}"] = plugin_exit == 0
        detailed_results[f"plugin_{plugin}"] = (plugin_exit, plugin_stdout, plugin_stderr)

        display_test_results(plugin_exit, plugin_stdout, plugin_stderr, f"{plugin.title()} Plugin")

        if plugin_exit != 0:
            all_passed = False

    # Summary
    print("\n" + "=" * 80)
    print("📈 FINAL SUMMARY")
    print("=" * 80)

    total_tests = 0
    total_passed = 0
    total_failed = 0

    for component, (exit_code, stdout, stderr) in detailed_results.items():
        passed, failed, total = parse_test_output(stdout)
        coverage_info = parse_coverage_output(stdout)

        status = "✅ PASS" if coverage_results[component] else "❌ FAIL"
        coverage_str = f"{coverage_info.get('total', 'N/A')}%"

        print(f"  {component.replace('_', ' ').title():<20} {status:<10} "
              f"Tests: {passed}/{total:<8} Coverage: {coverage_str}")

        total_tests += total
        total_passed += passed
        total_failed += failed

    print("-" * 80)
    print(f"  {'TOTAL':<20} {('✅ PASS' if all_passed else '❌ FAIL'):<10} "
          f"Tests: {total_passed}/{total_tests:<8}")

    print("\n📁 Coverage Reports Generated:")
    print(f"  Bot Core:      htmlcov/bot_core/index.html")
    for plugin in plugins:
        print(f"  {plugin.title()} Plugin: htmlcov/plugin_{plugin}/index.html")

    if all_passed:
        print("\n🎉 All components passed with adequate coverage!")
    else:
        print("\n⚠️  Some components failed or have insufficient coverage.")

    return 0 if all_passed else 1


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Discord bot tests")

    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage reporting (default: True)"
    )

    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Run without coverage reporting"
    )

    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report"
    )

    parser.add_argument(
        "--unit-only", "-u",
        action="store_true",
        help="Run only unit tests"
    )

    parser.add_argument(
        "--integration-only", "-i",
        action="store_true",
        help="Run only integration tests"
    )

    parser.add_argument(
        "--plugin",
        help="Run tests for specific plugin (admin, fun, moderation, utility, help)"
    )

    parser.add_argument(
        "--bot-core-only",
        action="store_true",
        help="Run only bot core tests with coverage"
    )

    parser.add_argument(
        "--separate-coverage",
        action="store_true",
        help="Generate separate coverage reports for bot core and each plugin"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first failure"
    )

    parser.add_argument(
        "--parallel", "-n",
        type=int,
        help="Run tests in parallel (requires pytest-xdist)"
    )

    parser.add_argument(
        "--markers", "-m",
        help="Run tests with specific markers (e.g., 'not slow')"
    )

    parser.add_argument(
        "test_path",
        nargs="?",
        help="Specific test path to run"
    )

    args = parser.parse_args()

    # Check if we're in the right directory
    if not Path("pytest.ini").exists():
        print("Error: pytest.ini not found. Please run from the project root directory.")
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
            print(f"Error: Plugin test directory '{plugin_path}' not found.")
            print("Available plugins: admin, fun, moderation, utility, help")
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
    print("🚀 Starting test run...")
    print("=" * 80)

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
        print(f"\n📊 HTML coverage report generated:")
        if args.bot_core_only:
            print(f"   📁 Open htmlcov/bot_core/index.html in your browser")
        elif args.plugin:
            print(f"   📁 Open htmlcov/plugin_{args.plugin}/index.html in your browser")
        else:
            print(f"   📁 Open htmlcov/index.html in your browser")

    # Check coverage threshold
    if not args.no_coverage and exit_code == 0:
        print(f"\n📈 Checking coverage threshold...")
        threshold_cmd = [
            "python", "-m", "pytest",
            "--cov=bot", "--cov=plugins",
            "--cov-fail-under=70",
            "--cov-report=term",
            "-q"
        ]

        threshold_exit, threshold_stdout, threshold_stderr = run_command(threshold_cmd, capture_output=True, show_output=False)

        if threshold_exit == 0:
            print("✅ Coverage threshold (70%) met!")
        else:
            print("⚠️  Coverage below 70% threshold")
            coverage_info = parse_coverage_output(threshold_stdout)
            if coverage_info.get('total'):
                print(f"   Current coverage: {coverage_info['total']}%")

    print("\n" + "=" * 80)
    if exit_code == 0:
        print("🎉 Test run completed successfully!")
    else:
        print("💥 Test run failed - see details above")
    print("=" * 80)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()