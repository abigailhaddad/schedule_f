# Comment Classification Testing Framework

This directory contains a testing framework for the comment classification component, allowing evaluation of different prompt variations and OpenAI models.

## Files and Structure

- `create_test_dataset.py`: Script to create a balanced test dataset from the main data.json file
- `test_classification.py`: Main testing script that evaluates different prompt and model combinations
- `prompt_variations.json`: JSON file containing different prompt variations to test
- `results/`: Directory storing test results and logs
- `test_data.json`: Generated balanced test dataset with equal representation of stances (created by running `create_test_dataset.py`)

## Usage

### 1. Create a balanced test dataset

```bash
python create_test_dataset.py --samples 30
```

This will:
- Read from frontend/data.json
- Select 30 comments from each stance category (For/Against/Neutral)
- Create a balanced test_data.json file

### 2. Run classification tests

```bash
python test_classification.py --models gpt-4o-mini gpt-4o --max_comments 20
```

This will:
- Test the specified OpenAI models
- Try each prompt variation from prompt_variations.json
- Use up to 20 comments from the test dataset
- Generate detailed logs and results in the results/ directory

### 3. View results

Test results are saved in two formats:
- JSON file with detailed results for each test
- Text log with summary statistics and error analysis

## Customization

### Adding New Prompt Variations

Edit `prompt_variations.json` to add new prompt variations to test. Each variation should include:
- `name`: Short name for the variation
- `description`: Description of the variation
- `instruction`: The actual instruction text that replaces the stance instruction in the prompt

### Testing with Different Models

Specify different OpenAI models using the `--models` parameter:

```bash
python test_classification.py --models gpt-3.5-turbo gpt-4o gpt-4-turbo
```