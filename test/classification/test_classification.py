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
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from litellm import completion
from collections import defaultdict

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
    
    def analyze_comment(self, comment_text: str, model: str, prompt_variation: Dict[str, str]) -> Dict:
        """
        Analyze a single comment using the specified model and prompt variation.
        
        Args:
            comment_text: The text of the comment to analyze
            model: The OpenAI model to use
            prompt_variation: Dictionary with the prompt variation details
            
        Returns:
            The analysis result
        """
        system_prompt = self.generate_system_prompt(prompt_variation['instruction'])
        
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
            print(f"Error analyzing comment: {str(e)}")
            return {"error": str(e)}
    
    def run_tests(self, max_comments: Optional[int] = None) -> List[Dict]:
        """
        Run all tests for each prompt variation and model combination.
        
        Args:
            max_comments: Optional maximum number of comments to test
            
        Returns:
            List of test results
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.output_dir, f"classification_test_results_{timestamp}.json")
        log_file = os.path.join(self.output_dir, f"classification_test_log_{timestamp}.txt")
        
        test_data = self.test_data
        if max_comments:
            test_data = test_data[:max_comments]
        
        all_results = []
        
        # Open log file for writing
        with open(log_file, 'w', encoding='utf-8') as log:
            log.write(f"Classification Test Run: {timestamp}\n")
            log.write(f"Models: {', '.join(self.models)}\n")
            log.write(f"Test data: {self.test_data_path} ({len(test_data)} comments)\n")
            log.write("=" * 80 + "\n\n")
            
            for model in self.models:
                log.write(f"Model: {model}\n")
                log.write("-" * 80 + "\n")
                
                for variation in self.prompt_variations:
                    variation_name = variation['name']
                    log.write(f"Prompt variation: {variation_name}\n")
                    log.write(f"Description: {variation['description']}\n\n")
                    
                    # Track metrics for this configuration
                    total = len(test_data)
                    correct = 0
                    errors = 0
                    confusion_matrix = defaultdict(int)
                    
                    # Track all results for this configuration
                    config_results = []
                    
                    for i, comment in enumerate(test_data):
                        comment_id = comment.get('id', f'comment_{i}')
                        expected_stance = comment.get('stance', '')
                        
                        # Log progress
                        print(f"Testing {model} + {variation_name}: {i+1}/{total} ({comment_id})")
                        
                        # Analyze comment
                        try:
                            analysis = self.analyze_comment(
                                comment_text=comment.get('comment', ''),
                                model=model,
                                prompt_variation=variation
                            )
                            
                            # Check if we got an error
                            if "error" in analysis:
                                log.write(f"Error analyzing {comment_id}: {analysis['error']}\n")
                                errors += 1
                                continue
                                
                            # Get the predicted stance
                            predicted_stance = analysis.get('stance', '')
                            
                            # Check if correct
                            is_correct = predicted_stance == expected_stance
                            if is_correct:
                                correct += 1
                            
                            # Update confusion matrix
                            confusion_key = f"{expected_stance}→{predicted_stance}"
                            confusion_matrix[confusion_key] += 1
                            
                            # Record this result
                            result = {
                                "comment_id": comment_id,
                                "model": model,
                                "prompt_variation": variation_name,
                                "expected_stance": expected_stance,
                                "predicted_stance": predicted_stance,
                                "is_correct": is_correct,
                                "rationale": analysis.get('rationale', '')
                            }
                            config_results.append(result)
                            all_results.append(result)
                            
                            # Add a short delay to avoid rate limiting
                            time.sleep(0.1)
                            
                        except Exception as e:
                            log.write(f"Error processing {comment_id}: {str(e)}\n")
                            errors += 1
                    
                    # Calculate accuracy
                    accuracy = correct / total if total > 0 else 0
                    
                    # Log results for this configuration
                    log.write(f"Results for {model} + {variation_name}:\n")
                    log.write(f"  Total comments: {total}\n")
                    log.write(f"  Correct classifications: {correct}\n")
                    log.write(f"  Errors/failures: {errors}\n")
                    log.write(f"  Accuracy: {accuracy:.2%}\n\n")
                    
                    # Log confusion matrix
                    log.write("Confusion Matrix:\n")
                    for key, count in confusion_matrix.items():
                        log.write(f"  {key}: {count}\n")
                    
                    # Log some example errors (up to 5)
                    incorrect_results = [r for r in config_results if not r.get('is_correct', False)]
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
    
    args = parser.parse_args()
    
    # Create tester and run tests
    tester = ClassificationTester(
        test_data_path=args.test_data,
        prompt_variations_path=args.prompt_variations,
        models=args.models,
        output_dir=args.output_dir
    )
    
    tester.run_tests(max_comments=args.max_comments)

if __name__ == "__main__":
    main()