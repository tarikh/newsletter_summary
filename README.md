# AI Newsletter Summarizer

The AI Newsletter Summarizer is a Python tool designed to automatically retrieve, analyze, and summarize AI-focused newsletters from a user's Gmail account. It distills key developments and actionable insights from multiple newsletters into a concise, easy-to-understand report targeted at regular users, rather than just AI experts.

## Features

- Automatically fetches emails tagged with "ai-newsletter" from your Gmail account
- Extracts and analyzes content from multiple newsletter sources
- Identifies key topics and trends across newsletters using advanced LLM techniques (default) or traditional NLP methods
- Uses OpenRouter to route requests to either OpenAI GPT-4.1 (default) or Anthropic's Claude 3.7 Sonnet for cost-efficient API usage and tracking
- Prioritizes recent content and breaking news (configurable)
- Outputs a markdown report with the top AI developments, why they matter, and actionable insights
- Includes links to newsletter sources and a brief methodology section
- **Modular codebase**: Authentication, fetching, LLM analysis, and reporting are in separate modules for easier maintenance and extension

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

    **The entry point is `main.py`**:

    ```bash
    python main.py
    ```

    By default, this analyzes newsletters from the past 7 days using OpenRouter to connect to OpenAI GPT-4.1. See Command-line Options below to customize.

    **Example: Use Claude 3.7 Sonnet instead of OpenAI (default):**
    ```bash
    python main.py --llm-provider claude
    ```
    
    **Example: Use a specific custom OpenRouter model:**
    ```bash
    python main.py --model google/gemini-2.5-flash-preview:thinking
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

-   `--no-label`: Do not use any Gmail label as a search criterion (useful if you want to search by other criteria like sender).
    ```bash
    python main.py --no-label --from-email newsletter@example.com
    ```

-   `--from-email EMAIL`: Only include emails from the specified sender.
    ```bash
    python main.py --from-email newsletter@example.com
    ```

-   `--to-email EMAIL`: Only include emails sent to the specified recipient.
    ```bash
    python main.py --to-email yourname@gmail.com
    ```

-   `--llm-provider PROVIDER`: Choose between `claude` (Claude 3.7 Sonnet), `openai` (GPT-4.1, default), or `google` (Gemini 2.0 Flash).
    ```bash
    python main.py --llm-provider claude
    ```

-   `--model MODEL`: Specify a custom OpenRouter model to use (overrides --llm-provider).
    ```bash
    python main.py --model google/gemini-2.5-flash-preview:thinking
    ```
    This allows using any model available on OpenRouter.

-   `--num-topics N`: Specify the number of topics to extract and summarize (default: 10).
    ```bash
    python main.py --num-topics 7
    ```

-   `--no-prioritize-recent`: Disable higher weighting for recent newsletters.
    ```bash
    python main.py --no-prioritize-recent
    ```

-   `--no-breaking-news-section`: Disable the separate "Just In" section for latest developments.
    ```bash
    python main.py --no-breaking-news-section
    ```

-   `-h` / `--help`: Show all available command-line options and usage examples.

## OpenRouter Integration

This project uses [OpenRouter](https://openrouter.ai) by default for all LLM API calls, providing:

1. Competitive pricing
2. Detailed usage tracking
3. Access to both Claude and OpenAI models through a single API

To check your OpenRouter setup:
```bash
python verify_openrouter.py
```

To analyze request costs:
```bash
python analyze_costs.py
```

## Approaches

The tool offers two distinct approaches to generating summaries:

### 1. Direct-to-LLM Approach (Default)
- Sends newsletter content directly to the LLM
- LLM identifies topics and generates summaries in a single step
- Streamlined process with potentially more coherent topics

## Modular Architecture

The codebase is organized into the following modules for clarity and maintainability:

- `auth.py` — Gmail authentication
- `fetch.py` — Email fetching
- `llm.py` — LLM analysis
- `report.py` — Report generation
- `main.py` — Entry point (run this file to use your tool)
- `summ.py` — Now just a stub, instructing users to use `main.py`

## Customization

For more advanced modifications:

-   To modify the number of key topics extracted, adjust the `num_topics` argument.
-   To change the direct-LLM prompt or model, edit the `analyze_newsletters_unified` function in `llm.py`.
-   To customize the final report format or content, modify the `generate_report` function in `report.py`.

## Troubleshooting

-   **NumPy Build Errors / Python Version:** If you encounter errors building NumPy or other scientific packages, use Python 3.11 (recommended) or 3.10. Python 3.12+ and 3.13 may not be fully supported by all dependencies yet.
-   **OpenRouter API Issues**: If you encounter problems with OpenRouter, you can disable it by setting `USE_OPENROUTER=false` in your `.env.local` file. This will make direct API calls to either OpenAI or Anthropic, but you'll need to provide the respective API keys.

## Testing

- `test_fetch_api.py`: Unit tests for email fetching and parsing logic.
- `test_e2e_cli.py`: End-to-end tests for the CLI workflow and report generation.

To run all tests:

```bash
pytest
```

## Contributing

Contributions are welcome! Feel free to submit a Pull Request.

## License

This project is available under the MIT License.