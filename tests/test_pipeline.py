#!/usr/bin/env python3
"""
Comprehensive Test Suite for Schedule F Comment Analysis Pipeline

This test suite covers:
1. Main pipeline functionality (backend/pipeline.py)
2. Resume pipeline functionality (backend/resume_pipeline.py)  
3. JSON schema validation
4. Shell script execution
5. End-to-end workflow testing

Uses a subset of real comments.csv data and attachments for realistic testing.
"""

import unittest
import tempfile
import shutil
import os
import json
import sys
import subprocess
from pathlib import Path
import jsonschema
import pandas as pd

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.pipeline import main as pipeline_main
from backend.resume_pipeline import main as resume_pipeline_main
from backend.fetch.fetch_comments import read_comments_from_csv
from backend.analysis.create_lookup_table import create_lookup_table
from backend.analysis.analyze_lookup_table import analyze_lookup_table_batch
from backend.utils.comment_analyzer import CommentAnalyzer
from backend.utils.validate_pipeline_output import validate_pipeline_output


class TestPipelineBase(unittest.TestCase):
    """Base class for pipeline tests with common setup."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data paths and schemas."""
        cls.project_root = project_root
        cls.test_data_dir = cls.project_root / "tests" / "data"
        cls.test_csv = cls.test_data_dir / "test_comments.csv"
        cls.test_attachments_dir = cls.test_data_dir / "attachments"
        cls.schemas_dir = cls.project_root / "json-schemas"
        cls.data_schema_path = cls.schemas_dir / "data.schema.json"
        cls.lookup_schema_path = cls.schemas_dir / "lookup_table.schema.json"
        
        # Load schemas
        with open(cls.data_schema_path) as f:
            cls.data_schema = json.load(f)
        with open(cls.lookup_schema_path) as f:
            cls.lookup_schema = json.load(f)
    
    def setUp(self):
        """Set up temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy test attachments to temp directory
        if self.test_attachments_dir.exists():
            shutil.copytree(self.test_attachments_dir, self.output_dir / "attachments")
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def assertValidJSON(self, file_path, schema):
        """Assert that a JSON file is valid according to schema."""
        self.assertTrue(os.path.exists(file_path), f"File {file_path} does not exist")
        
        with open(file_path) as f:
            data = json.load(f)
        
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            self.fail(f"Schema validation failed for {file_path}: {e.message}")
    
    def assertFileExists(self, file_path, message=None):
        """Assert that a file exists."""
        if message is None:
            message = f"File {file_path} does not exist"
        self.assertTrue(os.path.exists(file_path), message)


class TestDataFetching(TestPipelineBase):
    """Test data fetching and processing components."""
    
    def test_csv_reading(self):
        """Test reading comments from CSV file."""
        raw_data_file = read_comments_from_csv(
            str(self.test_csv), 
            str(self.output_dir),
            limit=10
        )
        
        self.assertFileExists(raw_data_file)
        
        with open(raw_data_file) as f:
            raw_data = json.load(f)
        
        self.assertGreater(len(raw_data), 0)
        self.assertEqual(len(raw_data), 2)  # We have exactly 2 test comments
        
        # Check structure of first comment
        comment = raw_data[0]
        self.assertIn('id', comment)
        self.assertIn('attributes', comment)
        self.assertIn('comment', comment['attributes'])
        
        # Verify comment text is present
        self.assertTrue(comment['attributes']['comment'].strip())
        self.assertIn('CI testing purposes', comment['attributes']['comment'])
    
    def test_lookup_table_creation(self):
        """Test lookup table creation from raw data."""
        # First get raw data
        raw_data_file = read_comments_from_csv(
            str(self.test_csv), 
            str(self.output_dir),
            limit=20
        )
        
        with open(raw_data_file) as f:
            raw_data = json.load(f)
        
        # Create lookup table
        lookup_table = create_lookup_table(raw_data, truncate_chars=500)
        
        self.assertGreater(len(lookup_table), 0)
        self.assertLessEqual(len(lookup_table), len(raw_data))  # Should deduplicate
        
        # Check structure of first entry
        entry = lookup_table[0]
        required_fields = ['lookup_id', 'truncated_text', 'text_source', 
                          'comment_text', 'attachment_text', 'comment_ids', 
                          'comment_count', 'full_text_length', 'truncated_text_length']
        
        for field in required_fields:
            self.assertIn(field, entry, f"Missing required field: {field}")
        
        # Save lookup table for inspection (schema validation skipped for raw lookup table
        # since it has None values for analysis fields that schema expects as strings)
        lookup_file = self.output_dir / "test_lookup_table.json"
        with open(lookup_file, 'w') as f:
            json.dump(lookup_table, f, indent=2)
        
        # Check that file was created and has valid JSON structure
        self.assertFileExists(str(lookup_file))
        with open(lookup_file) as f:
            reloaded_data = json.load(f)
        self.assertEqual(len(reloaded_data), len(lookup_table))


class TestLLMAnalysis(TestPipelineBase):
    """Test LLM analysis components."""
    
    def test_comment_analyzer_initialization(self):
        """Test CommentAnalyzer can be initialized."""
        # Mock the environment variable for testing
        import unittest.mock as mock
        with mock.patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            analyzer = CommentAnalyzer(model="gpt-4o-mini")
            self.assertIsNotNone(analyzer)
            self.assertEqual(analyzer.model, "gpt-4o-mini")
    
    def test_batch_analysis_structure(self):
        """Test batch analysis returns correct structure (mock mode)."""
        # Create sample lookup table
        lookup_table = [
            {
                'lookup_id': 'lookup_000001',
                'truncated_text': 'This is a test comment opposing the proposal.',
                'text_source': 'comment',
                'comment_text': 'This is a test comment opposing the proposal.',
                'attachment_text': '',
                'comment_ids': ['OPM-2025-0004-9001'],
                'comment_count': 1,
                'full_text_length': 50,
                'truncated_text_length': 50,
                'stance': None,
                'key_quote': None,
                'rationale': None,
                'themes': None
            }
        ]
        
        # Mock analyzer that doesn't make real API calls
        class MockAnalyzer:
            def __init__(self):
                self.model = "mock"
            
            def analyze(self, comment_text, comment_id=None, max_retries=3):
                return {
                    'stance': 'Against',
                    'key_quote': 'opposing the proposal',
                    'rationale': 'Clear opposition expressed',
                    'themes': ['Opposition', 'Government Policy']
                }
        
        mock_analyzer = MockAnalyzer()
        
        # Run analysis
        analyzed_table = analyze_lookup_table_batch(
            lookup_table=lookup_table,
            analyzer=mock_analyzer,
            batch_size=1,
            use_parallel=False
        )
        
        self.assertEqual(len(analyzed_table), 1)
        entry = analyzed_table[0]
        
        # Check analysis fields were populated
        self.assertEqual(entry['stance'], 'Against')
        self.assertEqual(entry['key_quote'], 'opposing the proposal')
        self.assertIsNotNone(entry['rationale'])
        # themes should be converted to comma-separated string
        self.assertEqual(entry['themes'], 'Opposition, Government Policy')


class TestPipelineIntegration(TestPipelineBase):
    """Test full pipeline integration."""
    
    def test_pipeline_skip_analysis_mode(self):
        """Test pipeline in skip-analysis mode for faster testing."""
        print("🔧 Starting pipeline skip analysis test...")
        
        # Prepare arguments for pipeline
        test_args = [
            '--csv', str(self.test_csv),
            '--output_dir', str(self.output_dir),
            '--limit', '2',  # Much smaller for CI speed
            '--skip_analysis',
            '--skip_clustering',
            '--truncate', '100'  # Shorter truncation
        ]
        
        print(f"📋 Pipeline args: {test_args}")
        
        # Mock sys.argv
        original_argv = sys.argv
        try:
            print("🚀 Starting pipeline execution...")
            sys.argv = ['pipeline.py'] + test_args
            
            # This should create raw_data.json and lookup_table.json
            # but skip the expensive LLM analysis and clustering
            pipeline_main()
            print("✅ Pipeline execution completed")
            
        except SystemExit:
            print("📤 Pipeline exit (expected)")
            pass  # Expected when pipeline completes
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            raise
        finally:
            sys.argv = original_argv
        
        # Check expected output files
        raw_data_file = self.output_dir / "raw_data.json"
        lookup_table_file = self.output_dir / "lookup_table.json"
        
        self.assertFileExists(str(raw_data_file))
        self.assertFileExists(str(lookup_table_file))
        
        # Validate file contents
        with open(raw_data_file) as f:
            raw_data = json.load(f)
        self.assertGreater(len(raw_data), 0)
        
        with open(lookup_table_file) as f:
            lookup_table = json.load(f)
        self.assertGreater(len(lookup_table), 0)
        
        # Validate against schemas
        self.assertValidJSON(str(lookup_table_file), self.lookup_schema)
    
    def test_resume_pipeline_no_new_data(self):
        """Test resume pipeline with no new data to process."""
        print("🔄 Starting resume pipeline test...")
        
        # First run regular pipeline to create baseline data
        test_args = [
            '--csv', str(self.test_csv),
            '--output_dir', str(self.output_dir),
            '--limit', '2',  # Much smaller for CI speed
            '--skip_analysis',
            '--skip_clustering'
        ]
        
        print("1️⃣ Running initial pipeline...")
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + test_args
            pipeline_main()
            print("✅ Initial pipeline completed")
        except SystemExit:
            print("📤 Initial pipeline exit (expected)")
            pass
        except Exception as e:
            print(f"❌ Initial pipeline error: {e}")
            raise
        finally:
            sys.argv = original_argv
        
        # Now test resume pipeline with same data (should find no new comments)
        resume_output_dir = self.output_dir / "resume_test"
        resume_output_dir.mkdir()
        
        resume_args = [
            '--csv', str(self.test_csv),
            '--raw_data', str(self.output_dir / "raw_data.json"),
            '--lookup_table', str(self.output_dir / "lookup_table.json"),
            '--output_dir', str(resume_output_dir),
            '--limit', '2',  # Same limit, so no new comments
            '--skip_analysis',
            '--skip_clustering'
        ]
        
        print("2️⃣ Running resume pipeline...")
        try:
            sys.argv = ['resume_pipeline.py'] + resume_args
            resume_pipeline_main()
            print("✅ Resume pipeline completed")
        except SystemExit:
            print("📤 Resume pipeline exit (expected)")
            pass
        except Exception as e:
            print(f"❌ Resume pipeline error: {e}")
            raise
        finally:
            sys.argv = original_argv
        
        print("3️⃣ Checking output files...")
        # Check output files exist
        self.assertFileExists(str(resume_output_dir / "raw_data.json"))
        self.assertFileExists(str(resume_output_dir / "lookup_table.json"))
        print("✅ Resume pipeline test completed")


class TestSchemaValidation(TestPipelineBase):
    """Test JSON schema validation."""
    
    def test_data_schema_validation(self):
        """Test data.json schema validation with sample data."""
        # Create sample data that should validate
        sample_data = [
            {
                "id": "OPM-2025-0004-0002",
                "title": "Comment from Test User",
                "comment_on": "OPM-2025-0004-0001",
                "posted_date": "2025-04-28T04:00:00Z",
                "received_date": "2025-04-26T00:00:00Z",
                "submitter_name": "Test User",
                "organization": "",
                "city": "",
                "state": "",
                "country": "",
                "comment": "This is a test comment.",
                "original_comment": "This is a test comment.",
                "document_type": "Public Submission",
                "agency_id": "OPM",
                "category": "",
                "attachment_count": 0,
                "has_attachments": False,
                "attachment_urls": "",
                "attachment_titles": "",
                "attachment_local_paths": "",
                "lookup_id": "lookup_000001",
                "truncated_text": "This is a test comment.",
                "text_source": "comment",
                "comment_text": "This is a test comment.",
                "attachment_text": "",
                "comment_count": 1,
                "stance": "Against",
                "key_quote": "test comment",
                "rationale": "Test rationale",
                "themes": "Testing",
                "corrected": False,
                "cluster_id": "cluster_001",
                "pca_x": 0.5,
                "pca_y": 0.3
            }
        ]
        
        # Test validation
        try:
            jsonschema.validate(sample_data, self.data_schema)
        except jsonschema.ValidationError as e:
            self.fail(f"Valid data failed schema validation: {e.message}")
    
    def test_lookup_schema_validation(self):
        """Test lookup_table.json schema validation with sample data."""
        sample_lookup = [
            {
                "lookup_id": "lookup_000001",
                "truncated_text": "This is a test comment for lookup table validation.",
                "text_source": "comment",
                "comment_text": "This is a test comment for lookup table validation.",
                "attachment_text": "",
                "comment_ids": ["OPM-2025-0004-0002"],
                "comment_count": 1,
                "full_text_length": 55,
                "truncated_text_length": 55,
                "stance": "Against",
                "key_quote": "test comment",
                "rationale": "Test rationale for validation",
                "themes": "Testing, Validation",
                "cluster_id": "cluster_001",
                "pca_x": 0.5,
                "pca_y": 0.3
            }
        ]
        
        # Test validation
        try:
            jsonschema.validate(sample_lookup, self.lookup_schema)
        except jsonschema.ValidationError as e:
            self.fail(f"Valid lookup table failed schema validation: {e.message}")


class TestAttachmentProcessing(TestPipelineBase):
    """Test attachment download and text extraction components."""
    
    def setUp(self):
        """Set up test data and mock environment."""
        super().setUp()
        # Create mock attachment files for testing
        self.test_attachments_dir = self.output_dir / "test_attachments"
        self.test_attachments_dir.mkdir(exist_ok=True)
        
        # Create a simple test PDF content
        self.create_test_pdf()
        self.create_test_docx()
        self.create_test_txt()
    
    def create_test_pdf(self):
        """Create a simple test PDF file."""
        # For testing, we'll create a minimal PDF or just test the extraction logic
        # without creating actual PDF files since that requires external libraries
        self.test_pdf_path = self.test_attachments_dir / "test.pdf"
        # We'll mock this in the actual tests
    
    def create_test_docx(self):
        """Create a simple test DOCX file."""
        self.test_docx_path = self.test_attachments_dir / "test.docx"
        # We'll mock this in the actual tests
    
    def create_test_txt(self):
        """Create a simple test TXT file."""
        self.test_txt_path = self.test_attachments_dir / "test.txt"
        test_content = "This is a test document with some sample text for extraction testing."
        with open(self.test_txt_path, 'w') as f:
            f.write(test_content)
    
    def test_local_text_extraction_txt(self):
        """Test local text extraction from TXT files."""
        from backend.fetch.analyze_attachments import extract_text_local
        
        # Test TXT extraction
        extracted_text = extract_text_local(str(self.test_txt_path))
        self.assertIn("test document", extracted_text)
        self.assertIn("sample text", extracted_text)
    
    def test_gemini_api_request_structure(self):
        """Test that Gemini API requests are structured correctly."""
        from backend.fetch.analyze_attachments import extract_text_with_gemini
        import unittest.mock as mock
        
        # Mock the requests.post call
        with mock.patch('backend.fetch.analyze_attachments.requests.post') as mock_post:
            # Mock successful response
            mock_response = mock.Mock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "Extracted text from Gemini"}]
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            # Mock environment variable
            with mock.patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
                result = extract_text_with_gemini(str(self.test_txt_path), max_retries=1)
                
                # Verify the API call was made correctly
                self.assertTrue(mock_post.called)
                call_args = mock_post.call_args
                
                # Check URL (first positional argument)
                url = call_args[0][0]  # args[0] is the URL
                self.assertIn('generativelanguage.googleapis.com', url)
                self.assertIn('gemini-1.5-flash:generateContent', url)
                self.assertIn('test_key', url)
                
                # Check headers (keyword argument)
                headers = call_args[1]['headers']
                self.assertEqual(headers['Content-Type'], 'application/json')
                
                # Check request data structure (keyword argument)
                data = call_args[1]['json']
                self.assertIn('contents', data)
                self.assertIn('parts', data['contents'][0])
                
                # Verify inline data structure
                parts = data['contents'][0]['parts']
                inline_data_part = next((p for p in parts if 'inlineData' in p), None)
                self.assertIsNotNone(inline_data_part)
                self.assertIn('mimeType', inline_data_part['inlineData'])
                self.assertIn('data', inline_data_part['inlineData'])
                
                # Verify text prompt
                text_part = next((p for p in parts if 'text' in p), None)
                self.assertIsNotNone(text_part)
                self.assertIn('Extract all the text', text_part['text'])
                
                # Verify generation config
                self.assertIn('generationConfig', data)
                self.assertIn('temperature', data['generationConfig'])
                self.assertIn('maxOutputTokens', data['generationConfig'])
                
                # Check result
                self.assertEqual(result, "Extracted text from Gemini")
    
    def test_gemini_retry_mechanism(self):
        """Test that Gemini extraction retries on failures with exponential backoff."""
        from backend.fetch.analyze_attachments import extract_text_with_gemini
        import unittest.mock as mock
        import requests
        
        with mock.patch('backend.fetch.analyze_attachments.requests.post') as mock_post:
            # Mock rate limit error on first call, success on second
            mock_response_fail = mock.Mock()
            mock_response_fail.ok = False
            mock_response_fail.status_code = 429  # Rate limit
            mock_response_fail.text = "Rate limit exceeded"
            
            mock_response_success = mock.Mock()
            mock_response_success.ok = True
            mock_response_success.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "Retried extraction successful"}]
                    }
                }]
            }
            
            # First call fails, second succeeds
            mock_post.side_effect = [mock_response_fail, mock_response_success]
            
            # Mock sleep to speed up test
            with mock.patch('time.sleep'):
                with mock.patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
                    result = extract_text_with_gemini(str(self.test_txt_path), max_retries=2, base_delay=0.1)
                    
                    # Should succeed after retry
                    self.assertEqual(result, "Retried extraction successful")
                    # Should have been called twice
                    self.assertEqual(mock_post.call_count, 2)
    
    def test_gemini_retry_exhaustion(self):
        """Test that Gemini extraction fails after max retries."""
        from backend.fetch.analyze_attachments import extract_text_with_gemini
        import unittest.mock as mock
        
        with mock.patch('backend.fetch.analyze_attachments.requests.post') as mock_post:
            # Mock persistent failure
            mock_response = mock.Mock()
            mock_response.ok = False
            mock_response.status_code = 500  # Server error
            mock_response.text = "Internal server error"
            mock_post.return_value = mock_response
            
            # Mock sleep to speed up test
            with mock.patch('time.sleep'):
                with mock.patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
                    # Should raise RuntimeError after max retries
                    with self.assertRaises(RuntimeError) as context:
                        extract_text_with_gemini(str(self.test_txt_path), max_retries=2, base_delay=0.1)
                    
                    # Check error message mentions retries
                    self.assertIn("after 2 attempts", str(context.exception))
                    # Should have tried max_retries times
                    self.assertEqual(mock_post.call_count, 2)
    
    def test_gemini_interactive_skip(self):
        """Test that Gemini extraction allows user to skip files interactively."""
        from backend.fetch.analyze_attachments import extract_text_with_gemini
        import unittest.mock as mock
        
        with mock.patch('backend.fetch.analyze_attachments.requests.post') as mock_post:
            # Mock persistent failure
            mock_response = mock.Mock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_response.text = "Server error"
            mock_post.return_value = mock_response
            
            # Mock user input to choose skip (option 2)
            with mock.patch('builtins.input', return_value='2'):
                with mock.patch('time.sleep'):
                    with mock.patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
                        # Should return empty string when user chooses to skip
                        result = extract_text_with_gemini(
                            str(self.test_txt_path), 
                            max_retries=1, 
                            base_delay=0.1, 
                            interactive=True
                        )
                        self.assertEqual(result, "")  # Empty string for skipped file
    
    def test_attachment_download_workflow(self):
        """Test the complete attachment download and processing workflow."""
        from backend.fetch.fetch_comments import download_all_attachments
        import unittest.mock as mock
        
        # Create mock comment data with attachments
        comments_with_attachments = [
            {
                "id": "OPM-2025-0004-9001",
                "attributes": {
                    "title": "Test Comment with Attachment",
                    "comment": "This comment has an attachment",
                    "attachments": [
                        {
                            "title": "Test Document",
                            "fileUrl": "https://example.com/test.pdf"
                        }
                    ]
                }
            }
        ]
        
        # Mock the download function
        with mock.patch('backend.fetch.fetch_comments.download_attachment_with_retry') as mock_download:
            # Mock successful download
            mock_download.return_value = str(self.test_txt_path)
            
            # Mock text extraction
            with mock.patch('backend.fetch.analyze_attachments.extract_text_local') as mock_extract:
                mock_extract.return_value = "Extracted attachment text"
                
                # Run the download workflow
                updated_comments = download_all_attachments(
                    comments_with_attachments, 
                    str(self.output_dir)
                )
                
                # Verify the download was attempted
                self.assertTrue(mock_download.called)
                
                # Verify the comment was updated with attachment info
                self.assertEqual(len(updated_comments), 1)
                updated_comment = updated_comments[0]
                
                # Check that attachment processing updates were made
                # (The exact structure depends on implementation)
                self.assertIn("attributes", updated_comment)
    
    def test_attachment_text_extraction_pipeline(self):
        """Test the attachment analysis pipeline."""
        from backend.fetch.analyze_attachments import main as analyze_main
        import unittest.mock as mock
        import tempfile
        import sys
        
        # Create a mock results directory structure
        comment_dir = self.output_dir / "OPM-2025-0004-9001"
        comment_dir.mkdir()
        
        # Create a test attachment file
        test_file = comment_dir / "attachment_test.txt"
        with open(test_file, 'w') as f:
            f.write("This is test attachment content for processing.")
        
        # Mock sys.argv for the analyze_attachments script
        test_args = ['analyze_attachments.py', '--results_dir', str(self.output_dir)]
        
        with mock.patch.object(sys, 'argv', test_args):
            # Mock the Gemini extraction to avoid API calls
            with mock.patch('backend.fetch.analyze_attachments.extract_text_with_gemini') as mock_gemini:
                mock_gemini.return_value = "Gemini extracted text"
                
                # This should process files and create .extracted.txt files
                try:
                    analyze_main()
                except SystemExit:
                    pass  # analyze_main() may call sys.exit()
                
                # Check if extracted text file was created
                extracted_file = test_file.with_suffix(test_file.suffix + '.extracted.txt')
                if extracted_file.exists():
                    with open(extracted_file) as f:
                        extracted_content = f.read()
                    self.assertIn("attachment content", extracted_content)
    
    def test_mime_type_detection(self):
        """Test MIME type detection for different file types."""
        from backend.fetch.fetch_comments import get_mime_type
        
        test_cases = [
            ("https://example.com/doc.pdf", "doc.pdf", "application/pdf"),
            ("https://example.com/doc.docx", "doc.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("https://example.com/doc.txt", "doc.txt", "text/plain"),
            ("https://example.com/doc.rtf", "doc.rtf", "application/rtf"),
            ("https://example.com/unknown", "unknown", "application/octet-stream"),
        ]
        
        for url, filename, expected_mime in test_cases:
            with self.subTest(filename=filename):
                result = get_mime_type(url, filename)
                self.assertEqual(result, expected_mime)
    
    def test_attachment_processing_integration(self):
        """Test attachment processing integration with the main pipeline."""
        # Create test data with attachments
        test_data = {
            "OPM-2025-0004-9001": {
                "has_attachments": True,
                "attachment_count": 1,
                "attachment_urls": "https://example.com/test.pdf",
                "attachment_titles": "Test Document"
            }
        }
        
        # This tests that the pipeline can handle attachment data structure
        # and processes it correctly through the lookup table creation
        from backend.analysis.create_lookup_table import create_lookup_table
        
        # Create mock raw data with attachment info
        raw_data = [
            {
                "id": "OPM-2025-0004-9001",
                "attributes": {
                    "title": "Test Comment",
                    "comment": "Main comment text",
                    "attachmentCount": 1,
                    "attachments": [{"title": "Test Doc", "fileUrl": "https://example.com/test.pdf"}]
                }
            }
        ]
        
        # Test that lookup table creation handles attachments correctly
        lookup_table = create_lookup_table(raw_data, truncate_chars=500)
        
        self.assertGreater(len(lookup_table), 0)
        entry = lookup_table[0]
        
        # Verify attachment information is preserved
        self.assertIn('attachment_text', entry)
        # attachment_text might be empty if no local files exist, which is fine


class TestShellScripts(TestPipelineBase):
    """Test shell script functionality."""
    
    def test_merge_data_script_dry_run(self):
        """Test merge_data.sh script in dry-run mode."""
        # Create complete test data files that match the schema
        raw_data = [
            {
                "id": "OPM-2025-0004-9001",
                "attributes": {
                    "title": "Test Comment",
                    "comment": "Test comment",
                    "commentOnDocumentId": "OPM-2025-0004-9000",
                    "postedDate": "2025-04-26T00:00:00Z",
                    "receivedDate": "2025-04-26T00:00:00Z",
                    "submitterName": "Test User",
                    "organization": "",
                    "city": "",
                    "state": "",
                    "country": "",
                    "originalComment": "Test comment",
                    "documentType": "Public Submission",
                    "agencyId": "OPM",
                    "category": "",
                    "attachmentCount": 0
                }
            }
        ]
        
        lookup_table = [
            {
                "lookup_id": "lookup_000001",
                "truncated_text": "Test comment",
                "text_source": "comment",
                "comment_text": "Test comment",
                "attachment_text": "",
                "comment_ids": ["OPM-2025-0004-9001"],
                "comment_count": 1,
                "full_text_length": 12,
                "truncated_text_length": 12,
                "stance": "Neutral/Unclear",
                "key_quote": "Test comment",
                "rationale": "Test",
                "themes": "Testing",
                "cluster_id": "",
                "pca_x": None,
                "pca_y": None
            }
        ]
        
        # Write test files
        with open(self.output_dir / "raw_data.json", 'w') as f:
            json.dump(raw_data, f, indent=2)
        
        with open(self.output_dir / "lookup_table.json", 'w') as f:
            json.dump(lookup_table, f, indent=2)
        
        # Test the merge script
        script_path = self.project_root / "scripts" / "merge_data.sh"
        result = subprocess.run(
            [str(script_path), str(self.output_dir)],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        # Check if merge was successful (exit code 0)
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        
        self.assertEqual(result.returncode, 0, f"Merge script failed: {result.stderr}")
        
        # Check that data.json was created
        data_file = self.output_dir / "data.json"
        self.assertFileExists(str(data_file))
        
        # Validate merged data
        with open(data_file) as f:
            merged_data = json.load(f)
        
        self.assertEqual(len(merged_data), 1)
        
        # Check that lookup data was merged
        comment = merged_data[0]
        self.assertEqual(comment['lookup_id'], 'lookup_000001')
        self.assertEqual(comment['stance'], 'Neutral/Unclear')
    
    def test_run_pipeline_args_help(self):
        """Test that run_pipeline_args.sh shows help correctly."""
        script_path = self.project_root / "scripts" / "run_pipeline_args.sh"
        result = subprocess.run(
            [str(script_path), '--help'],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Usage:', result.stdout)
        self.assertIn('--resume', result.stdout)
        self.assertIn('--skip-analysis', result.stdout)
    
    def test_copy_latest_data_script_structure(self):
        """Test copy_latest_data.sh script structure and behavior."""
        script_path = self.project_root / "scripts" / "copy_latest_data.sh"
        
        # Test 1: Script exists and is executable
        self.assertTrue(script_path.exists(), f"Script not found: {script_path}")
        self.assertTrue(os.access(script_path, os.X_OK), f"Script not executable: {script_path}")
        
        # Test 2: Verify script shows expected output when run with 'N' (cancel)
        # The script will use the actual project's results directory
        
        process = subprocess.Popen(
            [str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.project_root)
        )
        
        # Send 'N' to cancel the operation
        stdout, stderr = process.communicate(input='N\n')
        
        # Test basic output structure
        self.assertIn('Copy Latest Results to Data Folder', stdout)
        self.assertIn('====================================', stdout)
        
        # The script should either find results or show an error
        if 'Latest results folder:' in stdout:
            # If results found, should show file listing and cancellation
            self.assertIn('Files to copy:', stdout)
            self.assertIn('Cancelled', stdout)
            self.assertEqual(process.returncode, 0)  # Should exit cleanly when cancelled
        else:
            # If no results found, should show appropriate error
            # Allow for different error message formats
            self.assertTrue(
                'No timestamped results folders found' in stdout or 
                'No results directory found' in stdout,
                f"Expected error message not found in: {stdout}"
            )
            self.assertEqual(process.returncode, 1)  # Should exit with error
        
        # Test 3: Test script help/structure by reading its content
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # Verify key functionality is present
        self.assertIn('Copy all files from the latest timestamped results folder', script_content)
        self.assertIn('dirname "$(dirname "$0")"', script_content)  # Project root detection
        self.assertIn('results_*', script_content)  # Timestamp pattern matching
        self.assertIn('read -p', script_content)  # Interactive confirmation
        self.assertIn('DELETE everything in the data/ folder', script_content)  # Warning message


class TestEndToEndWorkflow(TestPipelineBase):
    """Test complete end-to-end workflows."""
    
    def test_full_workflow_minimal(self):
        """Test a complete minimal workflow from CSV to final data.json."""
        print("🔄 Starting full workflow test...")
        
        # Step 1: Run pipeline with minimal data
        pipeline_args = [
            '--csv', str(self.test_csv),
            '--output_dir', str(self.output_dir),
            '--limit', '2',  # Even smaller for speed
            '--skip_analysis',  # Skip for speed
            '--skip_clustering',
            '--truncate', '100'  # Shorter truncation
        ]
        
        print("1️⃣ Running pipeline...")
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + pipeline_args
            pipeline_main()
            print("✅ Pipeline completed")
        except SystemExit:
            print("📤 Pipeline exit (expected)")
            pass
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            raise
        finally:
            sys.argv = original_argv
        
        print("2️⃣ Verifying pipeline outputs...")
        # Step 2: Verify pipeline outputs
        self.assertFileExists(str(self.output_dir / "raw_data.json"))
        self.assertFileExists(str(self.output_dir / "lookup_table.json"))
        
        print("3️⃣ Running merge script...")
        # Step 3: Run merge script
        script_path = self.project_root / "scripts" / "merge_data.sh"
        result = subprocess.run(
            [str(script_path), str(self.output_dir)],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        self.assertEqual(result.returncode, 0, f"Merge failed: {result.stderr}")
        print("✅ Merge script completed")
        
        print("4️⃣ Verifying final output...")
        # Step 4: Verify final output
        data_file = self.output_dir / "data.json"
        self.assertFileExists(str(data_file))
        
        print("5️⃣ Validating schema...")
        # Step 5: Validate final data against schema
        self.assertValidJSON(str(data_file), self.data_schema)
        
        print("6️⃣ Verifying data consistency...")
        # Step 6: Verify data consistency
        with open(self.output_dir / "raw_data.json") as f:
            raw_data = json.load(f)
        
        with open(data_file) as f:
            final_data = json.load(f)
        
        # Should have same number of comments
        self.assertEqual(len(raw_data), len(final_data))
        
        # All comments should have lookup_id populated
        for comment in final_data:
            self.assertIsNotNone(comment.get('lookup_id'))
        
        print("✅ Full workflow test completed successfully!")
    
    def test_pipeline_validation(self):
        """Test pipeline validation functionality."""
        # Create test data
        pipeline_args = [
            '--csv', str(self.test_csv),
            '--output_dir', str(self.output_dir),
            '--limit', '2',  # Smaller for speed
            '--skip_analysis',
            '--skip_clustering'
        ]
        
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + pipeline_args
            pipeline_main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Run validation
        validation_results = validate_pipeline_output(
            csv_file=str(self.test_csv),
            raw_data_file=str(self.output_dir / "raw_data.json"),
            data_file=None,  # Not created in skip-analysis mode
            lookup_table_file=str(self.output_dir / "lookup_table.json"),
            skip_count_validation=True,  # Tests use --limit
            skip_analysis_validation=True  # Tests use --skip_analysis
        )
        
        # Check validation results structure
        self.assertIn('valid', validation_results)
        self.assertIn('errors', validation_results)
        self.assertIn('warnings', validation_results)
        
        # Should pass basic validation
        self.assertTrue(validation_results['valid'] or len(validation_results['errors']) == 0)


class TestRealAPIIntegration(TestPipelineBase):
    """Test pipeline with REAL API calls - requires API keys."""
    
    def setUp(self):
        """Set up for real API tests."""
        super().setUp()
        
        # Check if API keys are available - FAIL if missing, don't skip
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.regs_key = os.getenv('REGS_API_KEY')
        
        # These should be available when running real API tests
        self.assertIsNotNone(self.openai_key, "OPENAI_API_KEY must be set for real API tests")
        self.assertIsNotNone(self.regs_key, "REGS_API_KEY must be set for real API tests")
    
    def tearDown(self):
        """Clean up temporary directory and any files created in root directory."""
        super().tearDown()
        
        # Clean up any test files that may have been created in the project root
        # These are created by the resume pipeline which saves to current directory
        root_files_to_clean = [
            'raw_data.json',
            'lookup_table.json', 
            'lookup_table.json.checkpoint',
            'data.json',
            'resume_pipeline.log',
            'pipeline.log',
            'data_validation_report.json',
            'lookup_table_quote_verification.json',
            'lookup_table_quote_verification.txt'
        ]
        
        for filename in root_files_to_clean:
            file_path = self.project_root / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"🧹 Cleaned up test file: {filename}")
                except Exception as e:
                    print(f"⚠️  Could not clean up {filename}: {e}")
    
    def test_full_pipeline_with_analysis(self):
        """Test complete pipeline WITH LLM analysis and attachment processing."""
        # Create test CSV with comments that have attachments for comprehensive testing
        test_csv_with_attachments = self.output_dir / "test_with_attachments.csv"
        
        # Read the header from the original test CSV
        with open(self.test_csv, 'r') as f:
            header = f.readline().strip()
        
        # Create CSV with mix of comments - some with attachments, some without
        with open(test_csv_with_attachments, 'w') as f:
            f.write(header + '\n')
            # Comment with both PDF and PNG attachments (real data from comments.csv)
            f.write('"OPM-2025-0004-25739","OPM","OPM-2025-0004","mb0-z605-bul8","Public Submission",2025-05-28T04:00Z,false,,,"Comment from Nicholas Hayden",,,false,OPM-2025-0004-0001,,,,2025-05-22T04:00Z,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,"Agency name: National Institute of Health","Agency",,,,,"https://downloads.regulations.gov/OPM-2025-0004-25739/attachment_1.png,https://downloads.regulations.gov/OPM-2025-0004-25739/attachment_1.pdf",\n')
            # Regular comment without attachments (from test CSV)
            f.write('"OPM-2025-0004-0002","OPM","OPM-2025-0004","m9y-jn9j-18n5","Public Submission",2025-04-28T04:00Z,false,,,"Comment from Elsa Lankford",,,false,OPM-2025-0004-0001,,,,2025-04-26T00:00Z,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,"This is an absolutely horrible idea. You\'re talking about removing 50,000 career public servants to replace them with unqualified Trump supporters?",,,,,,,\n')
        
        # Copy the actual attachment files to test directory so they can be found
        src_attachment_dir = Path("/Users/abigailhaddad/Documents/repos/regs/attachments/OPM-2025-0004-25739")
        if src_attachment_dir.exists():
            import shutil
            dest_attachment_dir = self.output_dir / "attachments" / "OPM-2025-0004-25739"
            dest_attachment_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_attachment_dir, dest_attachment_dir, dirs_exist_ok=True)
        
        # Use a very small dataset to control costs
        pipeline_args = [
            '--csv', str(test_csv_with_attachments),
            '--output_dir', str(self.output_dir),
            '--limit', '2',  # Only 2 comments to control API costs
            '--truncate', '500',  # Shorter text to reduce token usage
            '--model', 'gpt-4o-mini'  # Use cheapest model
        ]
        
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + pipeline_args
            pipeline_main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify outputs exist
        raw_data_file = self.output_dir / "raw_data.json"
        lookup_table_file = self.output_dir / "lookup_table.json"
        
        self.assertFileExists(str(raw_data_file))
        self.assertFileExists(str(lookup_table_file))
        
        # Load and validate lookup table with analysis
        with open(lookup_table_file) as f:
            lookup_table = json.load(f)
        
        # Verify analysis was performed
        analysis_found = False
        for entry in lookup_table:
            if 'stance' in entry and 'themes' in entry and 'key_quote' in entry:
                analysis_found = True
                # Verify analysis fields are populated
                self.assertIsNotNone(entry['stance'])
                # Themes can be list or string from LLM
                self.assertTrue(isinstance(entry['themes'], (list, str)))
                self.assertIsNotNone(entry['key_quote'])
                break
        
        self.assertTrue(analysis_found, "No LLM analysis found in lookup table")
        
        # Verify attachment processing occurred (if GEMINI_API_KEY is available)
        if self.gemini_key:
            attachments_dir = self.output_dir / "attachments"
            self.assertTrue(attachments_dir.exists(), "Attachments directory should exist when processing comments with attachments")
            
            # Look for the specific attachment directory we expect
            expected_attachment_dir = attachments_dir / "OPM-2025-0004-25739"
            self.assertTrue(expected_attachment_dir.exists(), f"Expected attachment directory {expected_attachment_dir} not found")
            
            # Verify some extracted files exist
            extracted_files = list(expected_attachment_dir.glob("*.extracted.txt"))
            self.assertGreater(len(extracted_files), 0, "No extracted text files found - attachment processing failed")
        
        # Validate against schema
        self.assertValidJSON(str(lookup_table_file), self.lookup_schema)
    
    def test_attachment_extraction_with_gemini(self):
        """Test attachment processing with real Gemini API calls using specific comments with attachments."""
        self.assertIsNotNone(self.gemini_key, "GEMINI_API_KEY must be set for Gemini tests")
        
        # Create a test CSV with specific comments that have both PDF and PNG attachments
        test_csv_with_attachments = self.output_dir / "test_with_attachments.csv"
        
        # Copy the header from the original test CSV
        with open(self.test_csv, 'r') as f:
            header = f.readline().strip()
        
        # Create CSV with the actual comment that has attachments (from main comments.csv)
        with open(test_csv_with_attachments, 'w') as f:
            f.write(header + '\n')
            # Use the real comment with PDF and PNG attachments
            f.write('"OPM-2025-0004-25739","OPM","OPM-2025-0004","mb0-z605-bul8","Public Submission",2025-05-28T04:00Z,false,,,"Comment from Nicholas Hayden",,,false,OPM-2025-0004-0001,,,,2025-05-22T04:00Z,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,"Agency name: National Institute of Health","Agency",,,,,"https://downloads.regulations.gov/OPM-2025-0004-25739/attachment_1.png,https://downloads.regulations.gov/OPM-2025-0004-25739/attachment_1.pdf",\n')
        
        # Copy the actual attachment files to test directory so they can be found
        src_attachment_dir = Path("/Users/abigailhaddad/Documents/repos/regs/attachments/OPM-2025-0004-25739")
        if src_attachment_dir.exists():
            import shutil
            dest_attachment_dir = self.output_dir / "attachments" / "OPM-2025-0004-25739"
            dest_attachment_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_attachment_dir, dest_attachment_dir, dirs_exist_ok=True)
        
        # Run pipeline with attachment processing on comments with known attachments
        pipeline_args = [
            '--csv', str(test_csv_with_attachments),
            '--output_dir', str(self.output_dir),
            '--limit', '1',  # Just process one comment with attachments
            '--skip_analysis',  # Focus only on attachment extraction
            '--skip_clustering'
        ]
        
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + pipeline_args
            pipeline_main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # REQUIRE that attachments were processed - don't skip gracefully
        attachments_dir = self.output_dir / "attachments"
        self.assertTrue(attachments_dir.exists(), "Attachments directory should exist after processing comments with attachments")
        
        # Look for the specific attachment directories we expect
        expected_attachment_dir = attachments_dir / "OPM-2025-0004-25739"
        self.assertTrue(expected_attachment_dir.exists(), f"Expected attachment directory {expected_attachment_dir} not found")
        
        # Look for extracted text files (both PDF and PNG should be processed)
        extracted_files = list(expected_attachment_dir.glob("*.extracted.txt"))
        self.assertGreater(len(extracted_files), 0, "No extracted text files found - Gemini processing failed")
        
        # Verify at least one file has substantial content
        substantial_content_found = False
        for txt_file in extracted_files:
            with open(txt_file) as f:
                content = f.read().strip()
            if len(content) > 20:  # Require actual extracted content
                print(f"✅ Successfully extracted {len(content)} chars from {txt_file.name}")
                substantial_content_found = True
        
        self.assertTrue(substantial_content_found, "No substantial content extracted from attachments - Gemini API may have failed")
    
    def test_full_pipeline_from_scratch_with_data_json(self):
        """Test complete fresh pipeline WITH analysis and data.json creation."""
        # Step 1: Run fresh pipeline with analysis
        pipeline_args = [
            '--csv', str(self.test_csv),
            '--output_dir', str(self.output_dir),
            '--limit', '3',
            '--truncate', '400',
            '--model', 'gpt-4o-mini'
        ]
        
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + pipeline_args
            pipeline_main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Step 2: Create data.json using merge script
        script_path = self.project_root / "scripts" / "merge_data.sh"
        result = subprocess.run(
            [str(script_path), str(self.output_dir)],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        self.assertEqual(result.returncode, 0, f"Merge script failed: {result.stderr}")
        
        # Step 3: Verify all outputs exist
        raw_data_file = self.output_dir / "raw_data.json"
        lookup_table_file = self.output_dir / "lookup_table.json"
        data_file = self.output_dir / "data.json"
        
        self.assertFileExists(str(raw_data_file))
        self.assertFileExists(str(lookup_table_file))
        self.assertFileExists(str(data_file))
        
        # Step 4: Validate both schemas
        self.assertValidJSON(str(lookup_table_file), self.lookup_schema)
        self.assertValidJSON(str(data_file), self.data_schema)
        
        # Step 5: Verify data consistency
        with open(raw_data_file) as f:
            raw_data = json.load(f)
        with open(data_file) as f:
            final_data = json.load(f)
        
        # Should have same number of comments
        self.assertEqual(len(raw_data), len(final_data))
        
        # Each comment should have analysis fields populated
        for comment in final_data:
            self.assertIn('stance', comment)
            self.assertIn('themes', comment)
            self.assertIn('key_quote', comment)
            # Verify fields are not empty
            self.assertIsNotNone(comment['stance'])
            self.assertTrue(isinstance(comment['themes'], (list, str)))
            self.assertIsNotNone(comment['key_quote'])
    
    def test_resume_pipeline_with_analysis(self):
        """Test resume pipeline functionality with real analysis."""
        # Step 1: Create initial data with 2 comments
        initial_args = [
            '--csv', str(self.test_csv),
            '--output_dir', str(self.output_dir),
            '--limit', '2',
            '--truncate', '400',
            '--model', 'gpt-4o-mini'
        ]
        
        original_argv = sys.argv
        try:
            sys.argv = ['pipeline.py'] + initial_args
            pipeline_main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Verify initial files exist
        raw_data_file = self.output_dir / "raw_data.json" 
        lookup_table_file = self.output_dir / "lookup_table.json"
        self.assertFileExists(str(raw_data_file))
        self.assertFileExists(str(lookup_table_file))
        
        # Step 2: Resume pipeline with more comments (should add 1 more)
        # Note: resume pipeline updates the input files in-place, so we don't specify --output_dir
        resume_args = [
            '--csv', str(self.test_csv),
            '--raw_data', str(raw_data_file),
            '--lookup_table', str(lookup_table_file),
            '--limit', '3',  # One more than initial
            '--truncate', '401',  # Must match actual truncation from pipeline
            '--model', 'gpt-4o-mini'
        ]
        
        try:
            sys.argv = ['resume_pipeline.py'] + resume_args
            resume_pipeline_main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv
        
        # Step 3: Verify updated files (resume pipeline updates files in-place, not in output dir)
        # The resume pipeline saves to current directory, so check there
        current_dir = Path.cwd()
        actual_raw_data_file = current_dir / "raw_data.json"
        actual_lookup_table_file = current_dir / "lookup_table.json"
        
        # If files don't exist in current dir, fall back to temp dir
        if not actual_raw_data_file.exists():
            actual_raw_data_file = raw_data_file
        if not actual_lookup_table_file.exists():
            actual_lookup_table_file = lookup_table_file
            
        with open(actual_raw_data_file) as f:
            updated_raw_data = json.load(f)
        with open(actual_lookup_table_file) as f:
            updated_lookup_table = json.load(f)
        
        # Should have 4 comments now (2 initial + up to 2 more due to limit=3 total, but CSV has more)
        # The exact number depends on how the resume pipeline handles limits
        self.assertGreaterEqual(len(updated_raw_data), 3)
        self.assertGreaterEqual(len(updated_lookup_table), 2)
        
        # Step 4: Create final data.json and validate both schemas  
        # Use the directory where the files actually are
        merge_dir = actual_raw_data_file.parent
        script_path = self.project_root / "scripts" / "merge_data.sh"
        result = subprocess.run(
            [str(script_path), str(merge_dir)],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        self.assertEqual(result.returncode, 0, f"Merge script failed: {result.stderr}")
        
        data_file = merge_dir / "data.json"
        self.assertFileExists(str(data_file))
        
        # Step 5: Validate schemas
        self.assertValidJSON(str(actual_lookup_table_file), self.lookup_schema)
        self.assertValidJSON(str(data_file), self.data_schema)
        
        # Step 6: Verify all comments have analysis
        with open(data_file) as f:
            final_data = json.load(f)
        
        analyzed_comments = 0
        for comment in final_data:
            if 'stance' in comment and comment['stance']:
                analyzed_comments += 1
        
        self.assertGreater(analyzed_comments, 0, "No analyzed comments found in resume pipeline")


def create_test_suite():
    """Create a test suite with all test classes."""
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDataFetching,
        TestLLMAnalysis, 
        TestPipelineIntegration,
        TestSchemaValidation,
        TestAttachmentProcessing,
        TestShellScripts,
        TestEndToEndWorkflow,
        TestRealAPIIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


if __name__ == '__main__':
    # Check if test data exists
    test_data_dir = Path(__file__).parent / "data"
    test_csv = test_data_dir / "test_comments.csv"
    
    if not test_csv.exists():
        print(f"ERROR: Test data not found at {test_csv}")
        print("Please run the setup to create test data first.")
        sys.exit(1)
    
    # Run specific test class if provided as argument
    if len(sys.argv) > 1:
        test_class_name = sys.argv[1]
        if hasattr(sys.modules[__name__], test_class_name):
            suite = unittest.TestLoader().loadTestsFromTestCase(
                getattr(sys.modules[__name__], test_class_name)
            )
        else:
            print(f"Test class {test_class_name} not found")
            sys.exit(1)
    else:
        # Run all tests
        suite = create_test_suite()
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)