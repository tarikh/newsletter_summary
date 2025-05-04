# AI Newsletter Summarizer

The AI Newsletter Summarizer is a Python tool designed to automatically retrieve, analyze, and summarize AI-focused newsletters from a user's Gmail account. It distills key developments and actionable insights from multiple newsletters into a concise, easy-to-understand report targeted at regular users, rather than just AI experts.

## Features

- Automatically fetches emails tagged with "ai-newsletter" from your Gmail account
- Extracts and analyzes content from multiple newsletter sources
- Identifies key topics and trends across newsletters using advanced NLP techniques
- **Contextual Summarization & NER:** For each topic, extracts key entities (ORG, PERSON, PRODUCT, etc.), event-related sentences, and context snippets using spaCy and sumy, and provides these to the LLM for richer, more actionable summaries
- Prioritizes recent content and breaking news (configurable)
- Uses OpenRouter to route requests to either OpenAI GPT-4.1 (default) or Anthropic's Claude 3.7 Sonnet for cost-efficient API usage and tracking
- Outputs a markdown report with the top AI developments, why they matter, and actionable insights
- Includes links to newsletter sources and a brief methodology section
- **Modular codebase**: Authentication, fetching, NLP, LLM analysis, and reporting are now in separate modules for easier maintenance and extension
- **Two approaches available**: A streamlined direct-to-LLM approach (default) or traditional NLP-based topic extraction + LLM analysis

## Newsletter Website Cache & Review Workflow

The tool caches detected newsletter websites for each source and marks them as **verified** or **unverified**:
- **Verified:** Trusted and used for future runs.
- **Unverified:** Used as a fallback, but will be replaced if a better guess or curated mapping is found.
- **Curated mapping:** Always takes precedence and is always trusted.

### How to Review and Confirm Newsletter Websites

1. **After running the tool**, review the detected websites for accuracy:

    ```bash
    python review_newsletter_websites.py
    ```

    For each unverified entry, you can:
    - `[a]ccept` to mark as verified
    - `[e]dit` to correct the website and mark as verified
    - `[d]elete` to remove the entry (it will be re-guessed next run)
    - `[s]kip` to leave it unverified for now

2. **Why review?**
    - Ensures your report always links to the correct main site for each newsletter.
    - Prevents bad guesses (e.g., tracking links, forms) from persisting in your reports.
    - Lets you maintain high-quality, human-verified source links.

3. **How to extend the curated mapping:**
    - Edit the `curated_websites` dictionary in `report.py` to add or update known newsletters and their homepages. These are always trusted and override guesses.

## Requirements

- Python 3.11 (recommended), or 3.10 (also supported)
- Gmail account with newsletters tagged/labeled as `ai-newsletter`
- Google API credentials (`credentials.json`) obtained from Google Cloud Console
- **OpenRouter API key** (set as `OPENROUTER_API_KEY` environment variable) - required as the default API provider
- OpenAI API key (set as `OPENAI_API_KEY` environment variable) - only needed if not using OpenRouter
- Anthropic API key (set as `ANTHROPIC_API_KEY` environment variable) - only needed if not using OpenRouter
- `keybert`, `sentence-transformers`, `scikit-learn` (for advanced topic extraction)
- `spacy`, `sumy` (for contextual summarization and NER/event detection)
- `openai` and `anthropic` Python packages for API access

## Installation

1.  **Clone the repository**

    ```bash
    git clone https://github.com/saadiq/newsletter_summary.git
    cd newsletter_summary
    ```

2.  **Set up a virtual environment (Recommended)**

    ```bash
    # Use Python 3.11 (recommended)
    python3.11 -m venv venv
    source venv/bin/activate  # On macOS/Linux
    # venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies**

    ```bash
    pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    # Download spaCy English model
    python -m spacy download en_core_web_sm
    ```

4.  **Set up Google OAuth credentials**

    - Go to the [Google Cloud Console](https://console.cloud.google.com/)
    - Create a new project or select an existing one.
    - Enable the **Gmail API** for your project.
    - Go to "Credentials", click "Create Credentials", and select "OAuth client ID".
    - Choose "Desktop application" as the application type.
    - Download the credentials JSON file.
    - **Rename and save the downloaded file as `credentials.json`** in the project's root directory.

5.  **Get an OpenRouter API key**

    - Sign up at [OpenRouter](https://openrouter.ai/) (if you don't have an account).
    - Obtain an API key from your account dashboard.

6.  **Create a `.env.local` file**

    Create a file named `.env.local` in the project directory and add your API keys:

    ```dotenv
    # Required - default API provider
    OPENROUTER_API_KEY=your_openrouter_api_key_here
    
    # Optional - OpenRouter configuration
    USE_OPENROUTER=true
    OPENROUTER_COST_LOG=openrouter_costs.json
    
    # Optional - only needed if bypassing OpenRouter with USE_OPENROUTER=false
    ANTHROPIC_API_KEY=your_anthropic_api_key_here
    OPENAI_API_KEY=your_openai_api_key_here
    ```
    *(Note: Ensure this file is included in your `.gitignore` if you plan to commit the code)*

## Usage

1.  **Setup Gmail Label**

    In your Gmail account, create a label named exactly `ai-newsletter`. Apply this label to all the AI newsletters you want the script to process.

2.  **Activate the virtual environment**

    ```bash
    source venv/bin/activate  # On macOS/Linux
    # venv\Scripts\activate  # On Windows
    ```

3.  **Run the tool**

    **The entry point is now `main.py` (not `summ.py`)**:

    ```bash
    python main.py
    ```

    By default, this analyzes newsletters from the past 7 days using OpenRouter to connect to OpenAI GPT-4.1. See Command-line Options below to customize.

    **Example: Use the advanced KeyBERT-based NLP method (with traditional NLP approach):**
    ```bash
    python main.py --days 3 --nlp-method keybert --traditional-nlp
    ```
    **Example: Use the classic n-gram frequency method:**
    ```bash
    python main.py --days 3 --nlp-method classic --traditional-nlp
    ```
    **Example: Use Claude 3.7 Sonnet instead of OpenAI (default):**
    ```bash
    python main.py --llm-provider claude
    ```
    **Example: Use the traditional NLP approach instead of direct-LLM (default):**
    ```bash
    python main.py --traditional-nlp
    ```
    **Example: Specify the number of topics to extract and analyze:**
    ```bash
    python main.py --num-topics 7
    ```

4.  **First-time Authentication**

    The *very first time* you run the tool, it will open a browser window. You'll need to:
    - Log in to the Google account associated with the Gmail inbox you want to analyze.
    - Grant the tool permission to **view your email messages and settings** (this is the `gmail.readonly` scope).
    After successful authentication, the tool will create a `token.json` file to store the authorization credentials, so you won't need to authenticate via the browser on subsequent runs (unless the token expires or is revoked).

5.  **View the Results**

    The tool will output progress messages to the console. Once finished, it will generate a markdown file named `ai_newsletter_summary_YYYYMMDD_to_YYYYMMDD_HHMM.md` in the project directory. The filename reflects the actual date range of the newsletters analyzed **and the time of the summary run**, so multiple runs in a day will not overwrite each other. Open this file to view your summarized report.

    **Each topic in the summary now includes:**
    - Key entities (organizations, people, products, etc.)
    - Key event sentences (launches, announcements, etc.)
    - Contextual snippets (summarized sentences)
    - All of this is provided to the LLM for more informative and actionable summaries.

### Custom Output Directory

To save reports to a custom directory, set the `NEWSLETTER_SUMMARY_OUTPUT_DIR` environment variable:

```bash
export NEWSLETTER_SUMMARY_OUTPUT_DIR=/path/to/output
```

### Mock Data for Testing

For development or testing, you can inject mock newsletter data by setting the `NEWSLETTER_SUMMARY_MOCK_DATA` environment variable to a JSON array of newsletter objects. This will bypass Gmail fetching:

```bash
export NEWSLETTER_SUMMARY_MOCK_DATA='[{"subject": "Test Subject", "date": "2024-01-01", "sender": "sender@example.com", "body": "Test body."}]'
```

## Command-line Options

You can modify the tool's behavior using these optional flags:

-   `--days N`: Specify the number of past days to retrieve emails from.
    ```bash
    python main.py --days 14
    ```
    (Default: `7`)

-   `--label LABEL`: Specify the Gmail label to filter newsletters (default: `ai-newsletter`).
    ```bash
    python main.py --label my-custom-label
    ```
    (Default: `ai-newsletter`)

-   `--no-label`: Do not use any Gmail label as a search criteria (overrides `--label`).
    ```bash
    python main.py --no-label --from-email sender@example.com
    ```
    (Use this to summarize emails by sender, recipient, or date only, with no label required.)

-   `--from-email EMAIL`: Only include emails from this sender email address (optional).
    ```bash
    python main.py --from-email sender@example.com
    ```
    (Optional)

-   `--to-email EMAIL`: Only include emails sent to this recipient email address (optional).
    ```bash
    python main.py --to-email recipient@example.com
    ```
    (Optional)

-   `--prioritize-recent` / `--no-prioritize-recent`: Enable or disable giving higher weight to more recent newsletters during topic extraction.
    ```bash
    python main.py --no-prioritize-recent
    ```
    (Default: enabled)

-   `--breaking-news-section` / `--no-breaking-news-section`: Enable or disable the separate "Just In" section in the report, which highlights headlines from the very latest newsletters (last ~24 hours).
    ```bash
    python main.py --no-breaking-news-section
    ```
    (Default: enabled)

-   `--nlp-method keybert|classic`: Choose the NLP technique for topic extraction when using `--traditional-nlp`. `keybert` uses KeyBERT and semantic clustering (default for traditional approach), `classic` uses the original n-gram frequency method.
    ```bash
    python main.py --nlp-method classic
    ```
    **Example: Use the classic n-gram frequency method with traditional NLP approach:**
    ```bash
    python main.py --nlp-method classic --traditional-nlp
    ```
    (Default: `keybert`)

-   `--llm-provider`, choices: `claude`, `openai` (default: `openai`): Choose the LLM provider for summarization. `openai` (default) uses OpenAI GPT-4.1, `claude` uses Claude 3.7 Sonnet. This is routed through OpenRouter by default for cost tracking.

-   `--num-topics N`: Specify the number of topics to extract and summarize.
    ```bash
    python main.py --num-topics 8
    ```
    (Default: `10`)

-   `--traditional-nlp`: Use traditional NLP-based topic extraction instead of direct-LLM.
    ```bash
    python main.py --traditional-nlp
    ```
    (Default: disabled)

-   `-h` / `--help`: Show all available command-line options and usage examples.

## NLP Topic Extraction Methods

These methods are used when running with the `--traditional-nlp` flag:

- **KeyBERT + Semantic Clustering (default for traditional approach):**
  - Extracts candidate keyphrases using KeyBERT, then clusters them using sentence-transformers embeddings.
  - Dynamically adjusts the number of clusters to the data volume.
  - If not enough distinct topics are found, fills in with the next best keyphrases or falls back to the classic method.
  - **Always returns the requested number of topics if possible, even with thin data.**

- **Classic n-gram Frequency:**
  - Uses frequency analysis of n-grams and subject lines to extract topics.

## Approaches

The tool offers two distinct approaches to generating summaries:

### 1. Direct-to-LLM Approach (Default)
- Sends newsletter content directly to the LLM
- LLM identifies topics and generates summaries in a single step
- Streamlined process with potentially more coherent topics

### 2. Traditional NLP + LLM Approach
- First extracts topics using either KeyBERT or classic n-gram frequency methods
- Then provides these topics to the LLM for analysis and summarization
- More control over topic selection but requires two processing stages
- Enable with the `--traditional-nlp` flag

Both approaches support customizing the number of topics (default: 10) and choosing between OpenAI and Claude as the LLM provider through OpenRouter.

## Modular Architecture

The codebase is now organized into the following modules for clarity and maintainability:

- `auth.py` — Gmail authentication
- `fetch.py` — Email fetching
- `nlp.py` — Topic extraction (includes traditional and direct-LLM methods)
- `llm.py` — LLM analysis (both unified and sequential approaches)
- `report.py` — Report generation
- `main.py` — Entry point (run this file to use your tool)
- `summ.py` — Now just a stub, instructing users to use `main.py`

## Customization

For more advanced modifications:

-   To modify the number of key topics extracted, adjust the `num_topics` argument in both approaches.
-   To change the direct-LLM prompt or model, edit the `analyze_newsletters_unified` function in `llm.py`.
-   To modify the traditional approach prompt, edit the `analyze_with_llm` function in `llm.py`.
-   To customize the final report format or content, modify the `generate_report` function in `report.py`.
-   To add more stop words for NLP processing in the traditional approach, update the `additional_stops` set in the `extract_key_topics` function in `nlp.py`.

## Troubleshooting

-   **NumPy Build Errors / Python Version:** If you encounter errors building NumPy or other scientific packages, use Python 3.11 (recommended) or 3.10. Python 3.12+ and 3.13 may not be fully supported by all dependencies yet.
-   **NLTK Resource Errors**: If you encounter errors like `Resource punkt not found.` during the first run, the tool attempts to download them automatically. If automatic download fails (e.g., due to network issues), you might need to run the following in a Python interpreter within your activated virtual environment:
    ```python
    import nltk
    nltk.download('punkt')
    nltk.download('stopwords')
    ```
-   **spaCy Model Not Found**: If you see an error about `en_core_web_sm` not found, run:
    ```
    python -m spacy download en_core_web_sm
    ```
-   **OpenRouter API Issues**: If you encounter problems with OpenRouter, you can disable it by setting `USE_OPENROUTER=false` in your `.env.local` file. This will make direct API calls to either OpenAI or Anthropic, but you'll need to provide the respective API keys.

## Testing

- `test_fetch_api.py`: Unit tests for email fetching and parsing logic.
- `test_e2e_cli.py`: End-to-end tests for the CLI workflow and report generation.

To run all tests:

```bash
pytest
```

## OpenRouter Integration

This project uses [OpenRouter](https://openrouter.ai) by default for all LLM API calls, providing improved cost tracking and analytics. 

### Configuration Options

- `USE_OPENROUTER`: Set to `true` (default) to route all LLM calls through OpenRouter or `false` to use direct API calls
- `OPENROUTER_COST_LOG`: Path to the JSON file for logging cost data (default: `openrouter_costs.json`)

### Verifying the Integration

Run the verification script to check if OpenRouter is properly configured:

```bash
python verify_openrouter.py
```

### Cost Analysis

You can analyze OpenRouter usage costs using the analysis tool:

```bash
python analyze_costs.py
```

Additional options:
```bash
python analyze_costs.py --days 7  # Analyze costs for the past 7 days
```

### Model Mapping

When using OpenRouter, the following models are used:
- `--llm-provider claude`: routes to `anthropic/claude-3-7-sonnet`
- `--llm-provider openai`: routes to `openai/gpt-4.1`

All LLM requests now include usage tracking information, making it easier to monitor costs and adjust usage patterns accordingly.