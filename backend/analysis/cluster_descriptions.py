#!/usr/bin/env python3
"""
Cluster Description Generator

Generates structured JSON descriptions of hierarchical clustering results using OpenAI.
Uses the same structured output pattern as existing comment analysis.

Usage:
python cluster_descriptions.py [--input hierarchical_cluster_report.txt]
"""

import os
import json
import argparse
import re
from typing import Dict, List
from dotenv import load_dotenv
from litellm import completion
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Import config constants
from backend.config import config

class ClusterDescription(BaseModel):
    """Pydantic model for a single cluster description"""
    short: str = Field(description="Brief 10-15 word description")
    long: str = Field(description="Detailed 1-2 sentence description")

def parse_cluster_report(report_path: str) -> List[Dict]:
    """Parse the hierarchical cluster report to extract cluster information"""
    clusters = []
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by cluster sections (including sub-sub-clusters with 4 spaces)
    cluster_sections = re.split(r'\n    CLUSTER |\n  CLUSTER |\nCLUSTER ', content)
    
    for section in cluster_sections[1:]:  # Skip header
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # Extract cluster ID
        cluster_id = lines[0].strip()
        
        cluster_info = {'cluster_id': cluster_id}
        
        # Extract information from the section
        current_section = None
        for line in lines:
            line = line.strip()
            
            if line.startswith('Level:'):
                cluster_info['level'] = int(line.split(':')[1].strip())
            elif line.startswith('Unique texts:'):
                cluster_info['unique_texts'] = int(line.split(':')[1].strip())
            elif line.startswith('Total comments:'):
                cluster_info['total_comments'] = int(line.split(':')[1].strip())
            elif line.startswith('Keywords:'):
                keywords = line.split(':', 1)[1].strip()
                cluster_info['keywords'] = [k.strip() for k in keywords.split(',')]
            elif line.startswith('Dominant stance:'):
                stance_info = line.split(':', 1)[1].strip()
                cluster_info['dominant_stance'] = stance_info
            elif line.startswith('Stance distribution:'):
                current_section = 'stance_distribution'
                cluster_info['stance_distribution'] = {}
            elif current_section == 'stance_distribution' and ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    stance = parts[0].strip()
                    count_info = parts[1].strip()
                    # Extract count (before parentheses)
                    count_match = re.match(r'(\d+)', count_info)
                    if count_match:
                        cluster_info['stance_distribution'][stance] = int(count_match.group(1))
            elif line.startswith('EXAMPLES OF DOMINANT STANCE'):
                current_section = 'examples'
            elif line.startswith('DEVIATIONS FROM DOMINANT STANCE'):
                current_section = 'deviations'
            elif line.startswith('SUBCLUSTERS:'):
                break  # Stop processing, subclusters will be handled separately
        
        clusters.append(cluster_info)
    
    return clusters

def generate_cluster_descriptions(clusters: List[Dict]) -> Dict[str, List[str]]:
    """Generate descriptions for clusters using OpenAI with structured output"""
    print(f"🤖 Generating descriptions for {len(clusters)} clusters using OpenAI...")
    
    # Ensure API key is available
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError("OPENAI_API_KEY not found in environment variables or .env file")
    
    # Prepare cluster summaries for the prompt
    cluster_summaries = []
    for cluster in clusters:
        summary = f"""
Cluster {cluster['cluster_id']}:
- Level: {cluster.get('level', 'Unknown')}
- Unique texts: {cluster.get('unique_texts', 0):,}
- Total comments: {cluster.get('total_comments', 0):,}
- Keywords: {', '.join(cluster.get('keywords', [])[:10])}
- Dominant stance: {cluster.get('dominant_stance', 'Unknown')}
- Stance distribution: {cluster.get('stance_distribution', {})}
"""
        cluster_summaries.append(summary.strip())
    
    prompt = f"""You are analyzing hierarchical clustering results from public comments about a proposed federal employment rule (Schedule F).

Here are the cluster summaries:

{chr(10).join(cluster_summaries)}

For each cluster, provide a VERY BRIEF description (max 10-15 words) that captures the key theme or perspective. Be concise and focus on what makes this cluster distinct.

Examples of good descriptions:
- "Opposition focused on scientific integrity and research concerns"
- "General civil service protection arguments"
- "Merit-based hiring and performance concerns"
- "Democratic values and constitutional arguments"

Keep descriptions short and thematic."""
    
    try:
        # Create a more flexible prompt that asks for JSON response
        cluster_list = [c['cluster_id'] for c in clusters]
        
        prompt = f"""You are analyzing hierarchical clustering results from public comments about a proposed federal employment rule (Schedule F).

Here are the cluster summaries:

{chr(10).join(cluster_summaries)}

For each cluster ({', '.join(cluster_list)}), provide both a short and long description in JSON format:

{{
  "cluster_id": ["short description (max 10-15 words)", "long description (1-2 sentences)"]
}}

Examples:
"0": ["Opposition focused on scientific integrity and research concerns", "This cluster represents opposition from the scientific community, with comments highlighting concerns about the impact on federal research and grant processes."]

Return a JSON object with all clusters."""

        response = completion(
            temperature=0.0,
            model=config.llm.model,
            messages=[
                {"role": "system", "content": "You are analyzing public comment clusters. Respond with valid JSON containing short and long descriptions for each cluster."},
                {"role": "user", "content": prompt}
            ],
            timeout=300  # 5 minutes timeout
        )
        
        # Process the response
        if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
            content = response.choices[0].message.content
            if isinstance(content, str):
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = json.loads(content)
            else:
                result = content
        else:
            raise ValueError("Unexpected response format")
        
        return result
        
    except Exception as e:
        print(f"❌ Error generating descriptions: {e}")
        raise e  # Re-raise the exception instead of using fallback

def save_cluster_descriptions(descriptions: Dict[str, List[str]], output_path: str):
    """Save cluster descriptions to JSON file"""
    print(f"💾 Saving cluster descriptions to {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(descriptions, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(descriptions)} cluster descriptions")

def find_most_recent_cluster_report():
    """Find the most recent hierarchical cluster report"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Look in data/cluster and results directories
    search_paths = [
        os.path.join(project_root, "data", "cluster"),
        os.path.join(project_root, "cluster"),
        os.path.join(project_root, "results"),
    ]
    
    # Also check results subdirectories
    results_base = os.path.join(project_root, "results")
    if os.path.exists(results_base):
        import glob
        result_dirs = glob.glob(os.path.join(results_base, "results_*"))
        for result_dir in result_dirs:
            search_paths.append(os.path.join(result_dir, "cluster"))
    
    print(f"🔍 Looking for hierarchical_cluster_report.txt files...")
    
    candidates = []
    for search_path in search_paths:
        if os.path.exists(search_path):
            report_file = os.path.join(search_path, "hierarchical_cluster_report.txt")
            if os.path.exists(report_file):
                candidates.append(report_file)
                print(f"📁 Found: {report_file}")
    
    if candidates:
        # Sort by modification time, newest first
        candidates.sort(key=os.path.getctime, reverse=True)
        print(f"✅ Most recent: {candidates[0]}")
        return candidates[0]
    
    return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate cluster descriptions using OpenAI')
    parser.add_argument('--input', type=str, help='Path to hierarchical cluster report file')
    parser.add_argument('--output', type=str, help='Output path for descriptions JSON')
    
    args = parser.parse_args()
    
    # Find input file
    input_file = args.input
    if input_file is None:
        input_file = find_most_recent_cluster_report()
        if input_file is None:
            print("❌ Could not find hierarchical cluster report file. Please specify with --input")
            return
    
    # Set output path
    if args.output:
        output_path = args.output
    else:
        # Put it in the same directory as the input file
        input_dir = os.path.dirname(input_file)
        output_path = os.path.join(input_dir, "cluster_descriptions.json")
    
    print(f"🚀 Starting cluster description generation...")
    print(f"📁 Input: {input_file}")
    print(f"📁 Output: {output_path}")
    
    # Parse cluster report
    clusters = parse_cluster_report(input_file)
    print(f"📊 Parsed {len(clusters)} clusters from report")
    
    if not clusters:
        print("❌ No clusters found in report")
        return
    
    # Generate descriptions
    descriptions = generate_cluster_descriptions(clusters)
    
    # Save results
    save_cluster_descriptions(descriptions, output_path)
    
    print(f"\n✅ Cluster description generation complete!")
    print(f"📁 Descriptions saved to: {output_path}")
    
    # Show sample results
    print(f"\n📝 Sample descriptions:")
    for cluster_id, description_pair in list(descriptions.items())[:3]:
        if isinstance(description_pair, list) and len(description_pair) >= 2:
            print(f"  {cluster_id}: {description_pair[0]}")
            print(f"      Long: {description_pair[1]}")
        else:
            print(f"  {cluster_id}: {description_pair}")

if __name__ == "__main__":
    main()