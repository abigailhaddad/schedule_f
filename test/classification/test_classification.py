#!/usr/bin/env python3
"""
Classification Testing Framework

This script tests the comment classification component with different:
- Prompt variations
- OpenAI models
- A balanced dataset of comments

It produces reports on accuracy and error analysis for each configuration.
"""

import json
import os
import time
import datetime
import argparse
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from litellm import completion
from collections import defaultdict
from tqdm import tqdm

# Ensure we can use backend utilities
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.analysis.analyze_comments import CommentAnalysisResult, Stance

class ClassificationTester:
    """Framework for testing various prompt and model combinations on comment classification."""
    
    def __init__(
        self, 
        test_data_path: str,
        prompt_variations_path: str,
        models: List[str],
        output_dir: str
    ):
        self.test_data_path = test_data_path
        self.prompt_variations_path = prompt_variations_path
        self.models = models
        self.output_dir = output_dir
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Load the test data
        with open(test_data_path, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
        
        # Load the prompt variations
        with open(prompt_variations_path, 'r', encoding='utf-8') as f:
            self.prompt_variations = json.load(f)
            
        # Verify API key is set
        if "OPENAI_API_KEY" not in os.environ:
            load_dotenv()
            if "OPENAI_API_KEY" not in os.environ:
                raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")
    
    def generate_system_prompt(self, stance_instruction: str) -> str:
        """
        Generate the system prompt with the given stance instruction variation.
        
        This maintains the full prompt structure while only changing the stance classification part.
        """
        return f"""You are analyzing public comments submitted regarding a proposed rule to implement "Schedule F" (or "Schedule Policy/Career").

This proposed rule would allow federal agencies to reclassify career civil servants in policy-influencing positions into a new employment category where they could be removed without the standard due process protections normally afforded to career federal employees.

For each comment (including any attached documents), provide:

{stance_instruction}

2. Themes: Identify which of these themes are present (select all that apply):
   - Merit-based system concerns (mentions civil service protections, merit system, etc.)
   - Due process/employee rights (mentions worker protections, procedural rights, etc.)
   - Politicization concerns (mentions political interference, partisan influence, etc.)
   - Scientific integrity (mentions concerns about scientific research, grant-making, etc.)
   - Institutional knowledge loss (mentions expertise, continuity, experience, etc.)
   
Note: Some comments include text from attached documents. Please consider ALL text in your analysis, including text from attachments if present.

3. Key Quote: Select the most important quote (max 100 words) that best captures the essence of the comment. Important requirements:
   - The quote must be exactly present in the original text - do not paraphrase or modify
   - Copy the text exactly as it appears, maintaining the original punctuation
   - Do not use any special characters, HTML entities (like &rsquo;), or Unicode symbols
   - Use plain ASCII characters only (regular quotes, apostrophes, hyphens, etc.)

4. Rationale: Briefly explain (1-2 sentences) why you classified the stance as you did.

Analyze objectively and avoid inserting personal opinions or biases."""
    
    def analyze_comment(self, comment_text: str, model: str, prompt_variation: Dict[str, str], max_retries: int = 3) -> Dict:
        """
        Analyze a single comment using the specified model and prompt variation.
        
        Args:
            comment_text: The text of the comment to analyze
            model: The OpenAI model to use
            prompt_variation: Dictionary with the prompt variation details
            max_retries: Maximum number of retry attempts
            
        Returns:
            The analysis result
        """
        system_prompt = self.generate_system_prompt(prompt_variation['instruction'])
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = completion(
                    temperature=0.0,
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Analyze the following public comment:\n\n{comment_text}"}
                    ],
                    response_format=CommentAnalysisResult
                )
                
                # Process the response based on its format
                if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
                    if isinstance(response.choices[0].message.content, str):
                        result = json.loads(response.choices[0].message.content)
                    else:
                        result = response.choices[0].message.content
                elif hasattr(response.choices[0].message, 'model_dump'):
                    result = response.choices[0].message.model_dump()
                else:
                    raise ValueError("Unexpected response format")
                    
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}
    
    def process_test_item(self, test_config: Tuple[Dict, str, Dict, int]) -> Dict:
        """
        Process a single test configuration (comment + model + prompt variation).
        This function is designed to be used in parallel processing.
        
        Args:
            test_config: Tuple containing (comment, model, prompt_variation, comment_index)
            
        Returns:
            Test result dictionary
        """
        comment, model, variation, i = test_config
        comment_id = comment.get('id', f'comment_{i}')
        expected_stance = comment.get('stance', '')
        variation_name = variation['name']
        
        try:
            # Analyze comment
            analysis = self.analyze_comment(
                comment_text=comment.get('comment', ''),
                model=model,
                prompt_variation=variation
            )
            
            # Check if we got an error
            if "error" in analysis:
                return {
                    "comment_id": comment_id,
                    "model": model,
                    "prompt_variation": variation_name,
                    "expected_stance": expected_stance,
                    "error": analysis["error"],
                    "status": "error"
                }
                
            # Get the predicted stance
            predicted_stance = analysis.get('stance', '')
            
            # Check if correct
            is_correct = predicted_stance == expected_stance
            
            # Record this result
            return {
                "comment_id": comment_id,
                "model": model,
                "prompt_variation": variation_name,
                "expected_stance": expected_stance,
                "predicted_stance": predicted_stance,
                "is_correct": is_correct,
                "rationale": analysis.get('rationale', ''),
                "themes": analysis.get('themes', []),
                "key_quote": analysis.get('key_quote', ''),
                "status": "success"
            }
                
        except Exception as e:
            return {
                "comment_id": comment_id,
                "model": model,
                "prompt_variation": variation_name,
                "expected_stance": expected_stance,
                "error": str(e),
                "status": "error"
            }
    
    def process_batch(self, batch_configs: List[Tuple[Dict, str, Dict, int]]) -> List[Dict]:
        """
        Process a batch of test configurations in parallel.
        
        Args:
            batch_configs: List of test configurations
            
        Returns:
            List of test results
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_config = {
                executor.submit(self.process_test_item, config): config
                for config in batch_configs
            }
            
            for future in concurrent.futures.as_completed(future_to_config):
                result = future.result()
                if result:
                    results.append(result)
        
        return results
    
    def run_tests(self, max_comments: Optional[int] = None, batch_size: int = 5) -> List[Dict]:
        """
        Run all tests for each prompt variation and model combination using parallel processing.
        
        Args:
            max_comments: Optional maximum number of comments to test
            batch_size: Number of comments to process in parallel
            
        Returns:
            List of test results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.output_dir, f"classification_test_results_{timestamp}.json")
        log_file = os.path.join(self.output_dir, f"classification_test_log_{timestamp}.txt")
        
        # Create a temp directory for intermediate results
        temp_dir = os.path.join(self.output_dir, f"temp_{timestamp}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup checkpoint file
        checkpoint_file = os.path.join(temp_dir, "test_checkpoint.json")
        
        test_data = self.test_data
        if max_comments:
            test_data = test_data[:max_comments]
        
        # Generate all possible test configurations
        all_test_configs = []
        for model in self.models:
            for variation in self.prompt_variations:
                for i, comment in enumerate(test_data):
                    all_test_configs.append((comment, model, variation, i))
        
        total_tests = len(all_test_configs)
        all_results = []
        processed_configs = set()
        
        # Check for existing checkpoint
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                    all_results = checkpoint_data.get('results', [])
                    processed_configs = set(tuple(x) for x in checkpoint_data.get('processed_configs', []))
                    print(f"Resuming from checkpoint with {len(all_results)} results")
            except Exception as e:
                print(f"Error loading checkpoint, starting from beginning: {e}")
        
        # Filter out already processed configs
        configs_to_process = []
        for config in all_test_configs:
            comment, model, variation, i = config
            config_key = (comment.get('id', f'comment_{i}'), model, variation['name'])
            if config_key not in processed_configs:
                configs_to_process.append(config)
        
        # Open log file for writing
        with open(log_file, 'w', encoding='utf-8') as log:
            log.write(f"Classification Test Run: {timestamp}\n")
            log.write(f"Models: {', '.join(self.models)}\n")
            log.write(f"Test data: {self.test_data_path} ({len(test_data)} comments)\n")
            log.write(f"Total test configurations: {total_tests}\n")
            log.write(f"Parallel batch size: {batch_size}\n")
            log.write("=" * 80 + "\n\n")
            
            # Process in batches with progress bar
            remaining_configs = len(configs_to_process)
            print(f"Processing {remaining_configs} of {total_tests} test configurations")
            
            with tqdm(total=remaining_configs, desc="Running tests") as pbar:
                for i in range(0, remaining_configs, batch_size):
                    # Get current batch
                    batch = configs_to_process[i:i+batch_size]
                    
                    # Process batch in parallel
                    batch_results = self.process_batch(batch)
                    
                    # Update results and processed tracking
                    for result in batch_results:
                        all_results.append(result)
                        processed_configs.add((
                            result['comment_id'], 
                            result['model'], 
                            result['prompt_variation']
                        ))
                    
                    # Save checkpoint
                    checkpoint_data = {
                        'results': all_results,
                        'processed_configs': list(processed_configs)
                    }
                    with open(checkpoint_file, 'w', encoding='utf-8') as f:
                        json.dump(checkpoint_data, f)
                    
                    pbar.update(len(batch))
            
            # Generate and log summary statistics by model and prompt variation
            log.write("\n===== RESULTS SUMMARY =====\n\n")
            
            # Group results by model and prompt variation
            grouped_results = defaultdict(list)
            for result in all_results:
                config_key = (result['model'], result['prompt_variation'])
                grouped_results[config_key].append(result)
            
            # Calculate and log statistics for each configuration
            for (model, variation_name), results in grouped_results.items():
                log.write(f"Model: {model}, Prompt Variation: {variation_name}\n")
                log.write("-" * 60 + "\n")
                
                # Calculate metrics
                total = len(results)
                success_count = sum(1 for r in results if r.get('status') == 'success')
                error_count = total - success_count
                
                successful_results = [r for r in results if r.get('status') == 'success']
                correct_count = sum(1 for r in successful_results if r.get('is_correct', False))
                
                accuracy = correct_count / success_count if success_count > 0 else 0
                success_rate = success_count / total if total > 0 else 0
                
                # Build confusion matrix
                confusion_matrix = defaultdict(int)
                for result in successful_results:
                    expected = result.get('expected_stance', '')
                    predicted = result.get('predicted_stance', '')
                    confusion_key = f"{expected}→{predicted}"
                    confusion_matrix[confusion_key] += 1
                
                # Log metrics
                log.write(f"Total tests: {total}\n")
                log.write(f"Successful API calls: {success_count} ({success_rate:.2%})\n")
                log.write(f"API errors: {error_count}\n")
                log.write(f"Correct classifications: {correct_count}\n")
                log.write(f"Accuracy: {accuracy:.2%}\n\n")
                
                # Log confusion matrix
                log.write("Confusion Matrix:\n")
                for key, count in sorted(confusion_matrix.items()):
                    percentage = count / success_count * 100 if success_count > 0 else 0
                    log.write(f"  {key}: {count} ({percentage:.1f}%)\n")
                
                # Log some example errors (up to 5)
                incorrect_results = [r for r in successful_results if not r.get('is_correct', False)]
                if incorrect_results:
                    log.write("\nSample incorrect classifications:\n")
                    for i, result in enumerate(incorrect_results[:5]):
                        log.write(f"  {i+1}. Comment {result['comment_id']}:\n")
                        log.write(f"     Expected: {result['expected_stance']}\n")
                        log.write(f"     Predicted: {result['predicted_stance']}\n")
                        log.write(f"     Rationale: {result['rationale']}\n\n")
                
                log.write("=" * 80 + "\n\n")
        
        # Save full results to JSON
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"Testing complete. Results saved to {results_file}")
        print(f"Log file: {log_file}")
        
        # Clean up checkpoint file
        try:
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
        except Exception as e:
            print(f"Error removing checkpoint file: {e}")
        
        return all_results
        
def main():
    """Command-line interface for the testing framework."""
    parser = argparse.ArgumentParser(description="Test comment classification with different prompts and models")
    
    parser.add_argument(
        "--test_data", 
        default="/Users/abigailhaddad/Documents/repos/regs/test/classification/test_data.json",
        help="Path to test data file"
    )
    parser.add_argument(
        "--prompt_variations", 
        default="/Users/abigailhaddad/Documents/repos/regs/test/classification/prompt_variations.json",
        help="Path to prompt variations file"
    )
    parser.add_argument(
        "--models", 
        nargs="+", 
        default=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        help="OpenAI models to test"
    )
    parser.add_argument(
        "--output_dir", 
        default="/Users/abigailhaddad/Documents/repos/regs/test/classification/results",
        help="Directory to save test results"
    )
    parser.add_argument(
        "--max_comments", 
        type=int, 
        default=None,
        help="Maximum number of comments to test (default: all)"
    )
    parser.add_argument(
        "--batch_size", 
        type=int, 
        default=5,
        help="Number of comments to process in parallel (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Create tester and run tests
    tester = ClassificationTester(
        test_data_path=args.test_data,
        prompt_variations_path=args.prompt_variations,
        models=args.models,
        output_dir=args.output_dir
    )
    
    tester.run_tests(max_comments=args.max_comments, batch_size=args.batch_size)

if __name__ == "__main__":
    main()