#!/usr/bin/env python3
"""
Test Runner for Schedule F Comment Analysis Pipeline

This script provides convenient ways to run different test suites:
- Quick tests (fast, no LLM calls)
- Full integration tests  
- Specific test classes
- Performance tests

Usage:
    python tests/run_tests.py                    # Run all tests
    python tests/run_tests.py --quick            # Run quick tests only
    python tests/run_tests.py --class TestName   # Run specific test class
    python tests/run_tests.py --list             # List available test classes
"""

import argparse
import sys
import os
import unittest
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_pipeline import (
    TestDataFetching,
    TestLLMAnalysis,
    TestPipelineIntegration, 
    TestSchemaValidation,
    TestShellScripts,
    TestEndToEndWorkflow,
    TestRealAPIIntegration,
    create_test_suite
)


def setup_test_environment():
    """Ensure test environment is properly set up."""
    test_data_dir = Path(__file__).parent / "data"
    test_csv = test_data_dir / "test_comments.csv"
    
    if not test_csv.exists():
        print("❌ Test data not found!")
        print(f"Expected: {test_csv}")
        print("\nTo create test data, run:")
        print("  mkdir -p tests/data")
        print("  head -1 comments.csv > tests/data/test_comments.csv")
        print("  tail -n +2 comments.csv | head -100 >> tests/data/test_comments.csv")
        return False
    
    # Check for schemas
    schemas_dir = project_root / "json-schemas"
    if not (schemas_dir / "data.schema.json").exists():
        print(f"❌ Schema files not found in {schemas_dir}")
        return False
    
    print("✅ Test environment ready")
    return True


def get_quick_test_suite():
    """Create a test suite with only quick tests (no LLM, no shell scripts)."""
    suite = unittest.TestSuite()
    
    # Quick test classes (no external dependencies)
    quick_classes = [
        TestDataFetching,
        TestLLMAnalysis,  # Uses mocked analyzer
        TestSchemaValidation
    ]
    
    for test_class in quick_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def get_integration_test_suite():
    """Create a test suite with integration tests."""
    suite = unittest.TestSuite()
    
    integration_classes = [
        TestPipelineIntegration,
        TestShellScripts,
        TestEndToEndWorkflow
    ]
    
    for test_class in integration_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


def list_test_classes():
    """List all available test classes."""
    test_classes = [
        TestDataFetching,
        TestLLMAnalysis,
        TestPipelineIntegration,
        TestSchemaValidation, 
        TestShellScripts,
        TestEndToEndWorkflow,
        TestRealAPIIntegration
    ]
    
    print("Available test classes:")
    for cls in test_classes:
        print(f"  {cls.__name__:<25} - {cls.__doc__.split('.')[0] if cls.__doc__ else 'No description'}")


def run_test_class(class_name):
    """Run a specific test class by name."""
    test_classes = {
        'TestDataFetching': TestDataFetching,
        'TestLLMAnalysis': TestLLMAnalysis,
        'TestPipelineIntegration': TestPipelineIntegration,
        'TestSchemaValidation': TestSchemaValidation,
        'TestShellScripts': TestShellScripts,
        'TestEndToEndWorkflow': TestEndToEndWorkflow,
        'TestRealAPIIntegration': TestRealAPIIntegration
    }
    
    if class_name not in test_classes:
        print(f"❌ Test class '{class_name}' not found")
        print("\nAvailable classes:")
        list_test_classes()
        return False, None
    
    suite = unittest.TestLoader().loadTestsFromTestCase(test_classes[class_name])
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    return result.wasSuccessful(), result


def main():
    parser = argparse.ArgumentParser(description='Run tests for Schedule F pipeline')
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick tests only (no shell scripts, no real LLM calls)')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration tests only')
    parser.add_argument('--real-apis', action='store_true',
                       help='Run tests with REAL API calls (requires API keys)')
    parser.add_argument('--class', dest='test_class',
                       help='Run specific test class')
    parser.add_argument('--list', action='store_true',
                       help='List available test classes')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    if args.list:
        list_test_classes()
        return
    
    # Check test environment
    if not setup_test_environment():
        sys.exit(1)
    
    print("🧪 Schedule F Pipeline Test Runner")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        if args.test_class:
            print(f"Running test class: {args.test_class}")
            success, result = run_test_class(args.test_class)
            
        elif args.quick:
            print("Running quick tests (no external dependencies)...")
            suite = get_quick_test_suite()
            runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1, buffer=True)
            result = runner.run(suite)
            success = result.wasSuccessful()
            
        elif args.integration:
            print("Running integration tests...")
            suite = get_integration_test_suite()
            runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1, buffer=True)
            result = runner.run(suite)
            success = result.wasSuccessful()
            
        else:
            print("Running all tests...")
            suite = create_test_suite()
            runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1, buffer=True)
            result = runner.run(suite)
            success = result.wasSuccessful()
            
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 50)
        if success:
            print(f"✅ All tests passed! ({elapsed:.1f}s)")
        else:
            print(f"❌ Some tests failed! ({elapsed:.1f}s)")
        
        # Show test summary
        if hasattr(result, 'testsRun'):
            print(f"📊 Tests run: {result.testsRun}")
            if result.failures:
                print(f"❌ Failures: {len(result.failures)}")
            if result.errors:
                print(f"💥 Errors: {len(result.errors)}")
            if result.skipped:
                print(f"⏭️  Skipped: {len(result.skipped)}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()