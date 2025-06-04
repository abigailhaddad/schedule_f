# Testing Documentation

This directory contains comprehensive tests for the Schedule F Comment Analysis Pipeline.

## Test Structure

### Test Files
- `test_pipeline.py` - Main test suite with all test classes
- `run_tests.py` - Test runner with convenient options
- `data/` - Test data directory with subset of real comments

### Test Classes

1. **TestDataFetching** - Tests data ingestion and processing
   - CSV reading functionality
   - Raw data validation
   - Lookup table creation
   - Attachment handling

2. **TestLLMAnalysis** - Tests LLM analysis components
   - CommentAnalyzer initialization
   - Batch analysis structure (with mocking)
   - Analysis field validation

3. **TestPipelineIntegration** - Tests main pipeline workflows
   - Full pipeline execution (skip-analysis mode)
   - Resume pipeline functionality
   - Output file validation

4. **TestSchemaValidation** - Tests JSON schema compliance
   - Data schema validation
   - Lookup table schema validation
   - Schema error detection

5. **TestShellScripts** - Tests shell script functionality
   - merge_data.sh execution
   - Script argument parsing
   - Output validation

6. **TestEndToEndWorkflow** - Tests complete workflows
   - CSV → pipeline → merge → data.json
   - Pipeline validation
   - Data consistency checks

## Test Data

The test suite uses a real subset of the comments.csv file:
- `tests/data/test_comments.csv` - First 100 comments from real data
- `tests/data/attachments/` - Real attachment files for testing
- Schemas from `json-schemas/` directory

## Running Tests

### Quick Start
```bash
# Run all tests (using convenience script)
./scripts/run_tests.sh

# Run quick tests only (no external dependencies)
./scripts/run_tests.sh quick

# Run specific test category
./scripts/run_tests.sh schema

# Or use the Python test runner directly
python tests/run_tests.py --quick
python tests/run_tests.py --class TestDataFetching
python tests/run_tests.py --list
```

### Test Categories

**Quick Tests** (fast, no external calls):
- Data fetching and validation
- Schema validation
- Mock LLM analysis

**Integration Tests** (slower, real execution):
- Full pipeline execution
- Shell script execution
- End-to-end workflows

### Direct Test Execution
```bash
# Run all tests with unittest
python -m unittest tests.test_pipeline -v

# Run specific test class
python -m unittest tests.test_pipeline.TestDataFetching -v

# Run specific test method
python -m unittest tests.test_pipeline.TestDataFetching.test_csv_reading -v
```

## Test Environment Setup

The tests automatically check for required files and provide setup instructions if missing.

### Required Files
- `tests/data/test_comments.csv` - Test CSV data
- `json-schemas/data.schema.json` - Data validation schema
- `json-schemas/lookup_table.schema.json` - Lookup table schema

### Creating Test Data
If test data is missing, create it with:
```bash
mkdir -p tests/data
head -1 comments.csv > tests/data/test_comments.csv
tail -n +2 comments.csv | head -100 >> tests/data/test_comments.csv

# Copy some real attachments for testing
cp -r attachments/OPM-2025-0004-0119 tests/data/attachments/
cp -r attachments/OPM-2025-0004-0145 tests/data/attachments/
```

## Test Coverage

### What's Tested
✅ **Data Processing**
- CSV reading with various formats
- Raw data structure validation
- Attachment file handling
- Lookup table creation and deduplication

✅ **Pipeline Execution** 
- Main pipeline with skip-analysis mode
- Resume pipeline functionality
- Output file generation
- Error handling

✅ **Schema Validation**
- JSON schema compliance for all output formats
- Required field validation
- Data type validation
- Schema error detection

✅ **Shell Scripts**
- merge_data.sh execution and validation
- Script argument handling
- Output file validation

✅ **End-to-End Workflows**
- Complete CSV → data.json pipeline
- Data consistency across pipeline stages
- Integration between all components

### What's Mocked
- LLM API calls (to avoid costs and dependencies)
- Clustering (requires significant computation)
- Attachment extraction (uses existing extracted files)

### Performance Testing
Tests are designed to run quickly by:
- Using small data subsets (5-100 comments)
- Skipping expensive operations (LLM analysis, clustering)
- Reusing existing attachment extractions
- Mocking external API calls

## Debugging Failed Tests

### Common Issues

1. **Missing Test Data**
   ```
   ERROR: Test data not found at tests/data/test_comments.csv
   ```
   Solution: Create test data as shown above

2. **Schema Validation Failures**
   ```
   Schema validation failed: 'field_name' is a required property
   ```
   Solution: Check that pipeline output includes all required schema fields

3. **Shell Script Failures**
   ```
   Merge script failed: No such file or directory
   ```
   Solution: Ensure scripts have execute permissions and dependencies are installed

4. **Pipeline Import Errors**
   ```
   ModuleNotFoundError: No module named 'backend'
   ```
   Solution: Run tests from project root directory

### Debugging Tips

1. **Verbose Output**
   ```bash
   python tests/run_tests.py --verbose
   ```

2. **Individual Test Methods**
   ```bash
   python -m unittest tests.test_pipeline.TestDataFetching.test_csv_reading -v
   ```

3. **Test Output Files**
   Tests create temporary directories - check these for output files when debugging

4. **Pipeline Logs**
   Pipeline tests create log files in temp directories for debugging

## CI/CD Integration

This test suite is designed for continuous integration:

### GitHub Actions Example
```yaml
name: Test Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Create test data
      run: |
        mkdir -p tests/data
        head -1 comments.csv > tests/data/test_comments.csv
        tail -n +2 comments.csv | head -100 >> tests/data/test_comments.csv
    - name: Run tests
      run: python tests/run_tests.py --quick
```

### Local Pre-commit Hook
```bash
#!/bin/sh
# Run quick tests before commit
python tests/run_tests.py --quick
```

## Adding New Tests

### Test Class Template
```python
class TestNewFeature(TestPipelineBase):
    """Test new feature functionality."""
    
    def test_feature_basic(self):
        """Test basic feature functionality."""
        # Test setup
        # Feature execution
        # Assertions
        pass
    
    def test_feature_edge_cases(self):
        """Test edge cases and error conditions."""
        pass
```

### Best Practices
1. Use `TestPipelineBase` for common setup/teardown
2. Test both success and failure cases
3. Use meaningful assertion messages
4. Clean up temporary files in tearDown
5. Mock expensive external calls
6. Use small test data for speed
7. Validate outputs against schemas

## Troubleshooting

### Environment Issues
- Ensure all dependencies from requirements.txt are installed
- Run tests from project root directory
- Check Python path includes project root

### Data Issues  
- Verify test data exists and is valid CSV
- Check attachment files are present
- Ensure schemas are valid JSON

### Permission Issues
- Make shell scripts executable: `chmod +x scripts/*.sh`
- Check write permissions for temporary directories

### Performance Issues
- Use `--quick` flag for faster testing
- Run specific test classes instead of full suite
- Check for hung processes if tests timeout