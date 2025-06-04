#!/bin/bash
# Quick test execution script for Schedule F Pipeline

set -e  # Exit on any error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "myenv" ]; then
    echo "🐍 Activating virtual environment..."
    source myenv/bin/activate
fi

echo "🧪 Schedule F Pipeline Test Suite"
echo "=================================="

# Check if test data exists
if [ ! -f "tests/data/test_comments.csv" ]; then
    echo "📋 Creating test data..."
    mkdir -p tests/data
    echo "📝 Creating minimal test data for CI/testing..."
        python3 -c "
import pandas as pd
import os

test_data = [
    {'Document ID': 'OPM-2025-0004-0001', 'Agency ID': 'OPM', 'Document Type': 'Proposed Rule', 'Posted Date': '2025-04-23T04:00Z', 'Title': 'Test Proposed Rule', 'Comment on Document ID': '', 'Received Date': '2025-04-21T00:00Z', 'First Name': '', 'Last Name': '', 'City': '', 'State/Province': '', 'Country': '', 'Comment': '', 'Category': ''},
    {'Document ID': 'OPM-2025-0004-0002', 'Agency ID': 'OPM', 'Document Type': 'Public Submission', 'Posted Date': '2025-04-28T04:00Z', 'Title': 'Test Comment 1', 'Comment on Document ID': 'OPM-2025-0004-0001', 'Received Date': '2025-04-26T00:00Z', 'First Name': 'Test', 'Last Name': 'User', 'City': 'Test City', 'State/Province': 'Test State', 'Country': 'USA', 'Comment': 'This is a test comment for CI testing purposes.', 'Category': ''},
    {'Document ID': 'OPM-2025-0004-0003', 'Agency ID': 'OPM', 'Document Type': 'Public Submission', 'Posted Date': '2025-04-28T04:00Z', 'Title': 'Test Comment 2', 'Comment on Document ID': 'OPM-2025-0004-0001', 'Received Date': '2025-04-26T00:00Z', 'First Name': 'Another', 'Last Name': 'User', 'City': 'Another City', 'State/Province': 'Another State', 'Country': 'USA', 'Comment': 'Another test comment for validation purposes.', 'Category': ''}
]

all_columns = ['Document ID', 'Agency ID', 'Docket ID', 'Tracking Number', 'Document Type', 'Posted Date', 'Is Withdrawn?', 'Federal Register Number', 'FR Citation', 'Title', 'Comment Start Date', 'Comment Due Date', 'Allow Late Comments', 'Comment on Document ID', 'Effective Date', 'Implementation Date', 'Postmark Date', 'Received Date', 'Author Date', 'Related RIN(s)', 'Authors', 'CFR', 'Abstract', 'Legacy ID', 'Media', 'Document Subtype', 'Exhibit Location', 'Exhibit Type', 'Additional Field 1', 'Additional Field 2', 'Topics', 'Duplicate Comments', 'OMB/PRA Approval Number', 'Page Count', 'Page Length', 'Paper Width', 'Special Instructions', 'Source Citation', 'Start End Page', 'Subject', 'First Name', 'Last Name', 'City', 'State/Province', 'Zip/Postal Code', 'Country', 'Organization Name', 'Submitter Representative', 'Representative Address', 'Representative City State Zip', 'Government Agency', 'Government Agency Type', 'Comment', 'Category', 'Restrict Reason Type', 'Restrict Reason', 'Reason Withdrawn', 'Content Files', 'Attachment Files', 'Display Properties']

df_data = []
for comment in test_data:
    row = {}
    for col in all_columns:
        row[col] = comment.get(col, '')
    df_data.append(row)

df = pd.DataFrame(df_data)
os.makedirs('tests/data', exist_ok=True)
df.to_csv('tests/data/test_comments.csv', index=False)
print('Created minimal test CSV with 3 rows (1 rule + 2 comments)')
"
    echo "✅ Test data created (minimal dataset)"
fi

# Copy attachments if they don't exist
if [ ! -d "tests/data/attachments" ]; then
    echo "📎 Copying test attachments..."
    mkdir -p tests/data/attachments
    cp -r attachments/OPM-2025-0004-0119 tests/data/attachments/ 2>/dev/null || echo "⚠️  Attachment directory not found, continuing..."
    cp -r attachments/OPM-2025-0004-0145 tests/data/attachments/ 2>/dev/null || echo "⚠️  Attachment directory not found, continuing..."
    echo "✅ Test attachments copied"
fi

# Parse command line arguments
case "${1:-all}" in
    "quick"|"q")
        echo "🚀 Running quick tests..."
        python3 tests/run_tests.py --quick
        ;;
    "integration"|"i")
        echo "🔗 Running integration tests..."
        python3 tests/run_tests.py --integration
        ;;
    "schema"|"s")
        echo "📋 Running schema validation tests..."
        python3 tests/run_tests.py --class TestSchemaValidation
        ;;
    "data"|"d")
        echo "📊 Running data processing tests..."
        python3 tests/run_tests.py --class TestDataFetching
        ;;
    "pipeline"|"p")
        echo "⚙️  Running pipeline tests..."
        python3 tests/run_tests.py --class TestPipelineIntegration
        ;;
    "scripts"|"sh")
        echo "📝 Running shell script tests..."
        python3 tests/run_tests.py --class TestShellScripts
        ;;
    "e2e"|"end-to-end")
        echo "🔄 Running end-to-end tests..."
        python3 tests/run_tests.py --class TestEndToEndWorkflow
        ;;
    "list"|"l")
        echo "📋 Available test categories:"
        echo "  quick (q)        - Fast tests, no external dependencies"
        echo "  integration (i)  - Integration tests with real execution"
        echo "  schema (s)       - JSON schema validation tests"
        echo "  data (d)         - Data processing tests"
        echo "  pipeline (p)     - Pipeline execution tests"
        echo "  scripts (sh)     - Shell script tests"
        echo "  e2e              - End-to-end workflow tests"
        echo "  all              - All tests (default)"
        echo ""
        echo "Usage: ./scripts/run_tests.sh [category]"
        ;;
    "all"|*)
        echo "🧪 Running all tests..."
        python3 tests/run_tests.py
        ;;
esac

echo ""
echo "✨ Test execution complete!"