# Schedule F Comments Analysis

An automated analysis of the 28,000+ public comments submitted on the proposed "Schedule F" federal employment rule.

## What This Project Does

This project analyzes public comments submitted to regulations.gov about the proposed Schedule F rule, which would change employment protections for certain federal workers. The tool:

- **Collects comments** from the official government database
- **Processes attachments** like PDFs and images to extract text
- **Categorizes comments** by stance (for/against/neutral) and themes
- **Groups similar comments** to identify patterns
- **Provides a searchable web interface** to explore the results

## Why We Built This

Analyzing thousands of public comments manually isn't practical, but understanding what people said about proposed policies is valuable. This tool makes that analysis possible and demonstrates how LLMs can help make sense of large datasets from government processes.

## Approach

We processed the comments through several steps:

1. **Data Collection** - Downloaded bulk comment data from regulations.gov and fetched attachments via the regulations.gov API
2. **Text Extraction** - Extracted text from PDFs using PyPDF2 and Word docs using python-docx. For images and complex documents, we use Gemini directly
3. **Deduplication** - Grouped comments with identical first 1,000 characters together to avoid analyzing duplicates
4. **LLM Analysis** - Used OpenAI models to categorize each unique comment's stance and themes
5. **Clustering** - Used sentence-transformers to create embeddings, then hierarchical clustering to group comments by topic. Generated cluster descriptions using OpenAI
6. **Web Interface** - Built a searchable frontend to explore the results

This reduced the dataset from ~28,000 comments to ~21,000 unique patterns for analysis.

## Technical Details

**Text Processing:**
- PyPDF2 for PDF text extraction, python-docx for Word documents  
- Gemini for images and complex documents that fail basic extraction
- Deduplication based on first 1,000 characters of combined comment + attachment text

**Analysis:**
- OpenAI GPT models for stance classification and theme identification
- sentence-transformers for creating semantic embeddings
- Hierarchical clustering using Ward linkage to group similar comments
- OpenAI-generated descriptions for each cluster based on representative comments

**Infrastructure:**
- Python backend with JSON data storage
- Next.js frontend with search and filtering capabilities

## Limitations

This analysis system has two notable limitations:

### Attachment Processing
- Not all attachments are successfully processed. Some PDFs, images, or other file types may fail text extraction even with Gemini API fallback, or result in garbled attachment content. However, this affects a very small percentage of comments.

### Model Categorization Accuracy
- The LLM categorization is not perfect. Comments were much wider than expected in terms of content: there were some that we weren't even sure how to categorize doing manual review, which wasn't practical to do in general: we mainly used that to tweak the prompt, which you can see here: [backend/utils/comment_analyzer.py](backend/utils/comment_analyzer.py#L68-L127)
- Previous iterations of this project included both formal testing and manual relabeling frameworks, but these added a degree of complexity that wasn't practical for this project. 

### Impact on Results
- We believe these limitations don't significantly affect the top-level findings
- The main impact is likely on the "neutral" category - manual review would probably recategorize many neutral comments as having a stance, making the already small neutral percentage even lower. 

## License

MIT