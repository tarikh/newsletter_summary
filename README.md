# AI Newsletter Summarizer

The AI Newsletter Summarizer is a Python tool designed to automatically retrieve, analyze, and summarize AI-focused newsletters from a user's Gmail account. It distills key developments and actionable insights from multiple newsletters into a concise, easy-to-understand report targeted at regular users, rather than just AI experts.

## Features

- Automatically fetches emails tagged with "ai-newsletter" from your Gmail account
- Extracts and analyzes content from multiple newsletter sources
- Identifies key topics and trends across newsletters using advanced NLP techniques
- **Contextual Summarization & NER:** For each topic, extracts key entities (ORG, PERSON, PRODUCT, etc.), event-related sentences, and context snippets using spaCy and sumy, and provides these to the LLM for richer, more actionable summaries
- Prioritizes recent content and breaking news (configurable)
- Uses Anthropic's Claude AI or OpenAI's GPT-4.1 to generate summaries focused on practical applications and real-world impact (OpenAI is now the default)
- Outputs a markdown report with the top 5 AI developments, why they matter, and actionable insights
- Includes links to newsletter sources and a brief methodology section
- **Modular codebase**: Authentication, fetching, NLP, LLM analysis, and reporting are now in separate modules for easier maintenance and extension

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
- Anthropic API key (set as `ANTHROPIC_API_KEY` environment variable) if using Claude
- OpenAI API key (set as `OPENAI_API_KEY` environment variable) if using OpenAI (default)
- `keybert`, `sentence-transformers`, `scikit-learn` (for advanced topic extraction)
- `spacy`, `sumy` (for contextual summarization and NER/event detection)
- `openai` (for OpenAI GPT-4.1 support)

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

5.  **Get an Anthropic API key**

    - Sign up at [Anthropic](https://www.anthropic.com/) (if you don't have an account).
    - Obtain an API key from your account dashboard.

6.  **Create a `.env.local` file**

    Create a file named `.env.local` in the project directory and add your Anthropic API key:

    ```dotenv
    ANTHROPIC_API_KEY=your_anthropic_api_key_here
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

    By default, this analyzes newsletters from the past 7 days using OpenAI GPT-4.1. See Command-line Options below to customize.

    **Example: Use the advanced KeyBERT-based NLP method (default):**
    ```bash
    python main.py --days 3 --nlp-method keybert
    ```
    **Example: Use the classic n-gram frequency method:**
    ```bash
    python main.py --days 3 --nlp-method classic
    ```
    **Example: Use Claude 3.7 Sonnet instead of OpenAI (default):**
    ```bash
    python main.py --llm-provider claude
    ```
    **Example: Explicitly use OpenAI (default):**
    ```bash
    python main.py --llm-provider openai
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

-   `--nlp-method keybert|classic`: Choose the NLP technique for topic extraction. `keybert` uses KeyBERT and semantic clustering (default), `classic` uses the original n-gram frequency method.
    ```bash
    python main.py --nlp-method classic
    ```
    (Default: `keybert`)

-   `--llm-provider`, choices: `claude`, `openai` (default: `openai`): Choose the LLM provider for summarization. `openai` (default) uses OpenAI GPT-4.1, `claude` uses Claude 3.7 Sonnet.

-   `-h` / `--help`: Show all available command-line options and usage examples.

## NLP Topic Extraction Methods

- **KeyBERT + Semantic Clustering (default):**
  - Extracts candidate keyphrases using KeyBERT, then clusters them using sentence-transformers embeddings.
  - Dynamically adjusts the number of clusters to the data volume.
  - If not enough distinct topics are found, fills in with the next best keyphrases or falls back to the classic method.
  - **Always returns the requested number of topics if possible, even with thin data.**

- **Classic n-gram Frequency:**
  - Uses frequency analysis of n-grams and subject lines to extract topics.

## Modular Architecture

The codebase is now organized into the following modules for clarity and maintainability:

- `auth.py` — Gmail authentication
- `fetch.py` — Email fetching
- `nlp.py` — Topic extraction
- `llm.py` — LLM analysis
- `report.py` — Report generation
- `main.py` — Entry point (run this file to use your tool)
- `summ.py` — Now just a stub, instructing users to use `main.py`

## Customization

For more advanced modifications:

-   To modify the number of key topics extracted, adjust the `num_topics` argument in the `extract_key_topics` function call within `main.py`.
-   To change the specific LLM prompt, analysis approach, or the LLM model used (e.g., a different Claude model), edit the `analyze_with_llm` function in `llm.py`.
-   To customize the final report format or content, modify the `generate_report` function in `report.py`.
-   To add more stop words for NLP processing, update the `additional_stops` set in the `extract_key_topics` function in `nlp.py`.

## Troubleshooting

-   **NumPy Build Errors / Python Version:** If you encounter errors building NumPy or other scientific packages, use Python 3.11 (recommended) or 3.10. Python 3.12+ and 3.13 may not be fully supported by all dependencies yet.
-   **NLTK Resource Errors**: If you encounter errors like `Resource punkt not found.` during the first run, the tool attempts to download them automatically. If automatic download fails (e.g., due to network issues), you might need to run the following in a Python interpreter within your activated virtual environment:
    ```python
    import nltk
    nltk.download('punkt')
    nltk.download('stopwords')
    ```
-   **spaCy Model Not Found**: If you see an error about `en_core_web_sm` not found, run:
    ```bash
    python -m spacy download en_core_web_sm
    ```
-   **Authentication Issues / `token.json` Errors**: If you face persistent authentication problems or errors related to `token.json`, try deleting the `token.json` file and re-running the tool. This will force the authentication flow again. Ensure your `credentials.json` file is correct and hasn't been revoked in Google Cloud Console.
-   **API Rate Limits**: Be aware that both the Gmail API and the Anthropic API have usage limits. If you process a very large number of newsletters frequently, you might encounter rate limiting. Check the respective documentation for details.
-   **No Newsletters Found**: Ensure you have emails with the exact label `ai-newsletter` within the specified `--days` range. Check for typos in the label name.
-   **Newsletter Website Links Are Wrong:**
    - Run `python review_newsletter_websites.py` to review and correct cached websites.
    - Extend the curated mapping in `report.py` for newsletters you read often.
    - Delete `newsletter_websites.json` to force a full re-detection if needed.

## Functional Specification

This section provides a detailed breakdown of the tool's internal workings.

### 1. Overview

The tool automates the process of retrieving, analyzing, and summarizing AI-focused newsletters from Gmail, generating a user-focused report.

### 2. Core Functionality

#### 2.1. Gmail Authentication & Retrieval
-   **Authentication:** Uses OAuth 2.0 via `google-auth-oauthlib` and `google-api-python-client`. Requires `credentials.json` for initial setup, stores/refreshes tokens in `token.json`. Handles token expiry and refresh.
-   **Email Retrieval:** Queries the Gmail API using `service.users().messages().list()` with `q="label:ai-newsletter after:YYYY/MM/DD"`. Fetches full message content (`format='full'`) for matching message IDs.
-   **Content Extraction:** Parses message payloads using the `

## Testing & Developer Guide

### Test Types

- **Integration tests**: Simulate Gmail API responses and test core logic (see `test_fetch_api.py`).
- **E2E/CLI tests**: Run the full CLI workflow, verify output file and content (see `test_e2e_cli.py`).

### Running Tests

- To run all tests:
  ```bash
  pytest
  ```
- To run a specific test file:
  ```bash
  pytest test_fetch_api.py
  pytest test_e2e_cli.py
  ```
- To run a specific test function:
  ```bash
  pytest test_fetch_api.py::test_get_ai_newsletters_success
  ```

### E2E/CLI Test Environment Variables

- `NEWSLETTER_SUMMARY_OUTPUT_DIR`: If set, the CLI will write the report file to this directory (used for testing and automation).
- `NEWSLETTER_SUMMARY_MOCK_DATA`: If set (as a JSON string), the CLI will use this as the newsletter data instead of fetching from Gmail. This enables robust E2E/CLI testing.

### Developer Dependencies

- Developer/test dependencies are in `requirements-dev.txt` (e.g., `pytest`).
  ```bash
  pip install -r requirements-dev.txt
  ```

### Example: E2E/CLI Test

The E2E test runs the CLI with mocked data and checks the output file:
```python
import subprocess, os, sys, tempfile, json
with tempfile.TemporaryDirectory() as tmpdir:
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    env['NEWSLETTER_SUMMARY_OUTPUT_DIR'] = tmpdir
    env['NEWSLETTER_SUMMARY_MOCK_DATA'] = json.dumps([
        {'subject': 'Test Subject', 'date': '...', 'sender': '...', 'body': '...'}
    ])
    subprocess.run([sys.executable, 'main.py', '--days', '1'], env=env)
    # Check output file in tmpdir
```