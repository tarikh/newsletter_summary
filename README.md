# AI Newsletter Summarizer

The AI Newsletter Summarizer is a Python tool designed to automatically retrieve, analyze, and summarize AI-focused newsletters from a user's Gmail account. It distills key developments and actionable insights from multiple newsletters into a concise, easy-to-understand report targeted at regular users, rather than just AI experts.

## Features

- Automatically fetches emails tagged with "ai-newsletter" from your Gmail account
- Extracts and analyzes content from multiple newsletter sources
- Identifies key topics and trends across newsletters using advanced NLP techniques
- **Contextual Summarization & NER:** For each topic, extracts key entities (ORG, PERSON, PRODUCT, etc.), event-related sentences, and context snippets using spaCy and sumy, and provides these to the LLM for richer, more actionable summaries
- Prioritizes recent content and breaking news (configurable)
- Uses Anthropic's Claude AI to generate summaries focused on practical applications and real-world impact
- Outputs a markdown report with the top 5 AI developments, why they matter, and actionable insights
- Includes links to newsletter sources and a brief methodology section
- **Modular codebase**: Authentication, fetching, NLP, LLM analysis, and reporting are now in separate modules for easier maintenance and extension

## Requirements

- Python 3.11 (recommended), or 3.10 (also supported)
- Gmail account with newsletters tagged/labeled as `ai-newsletter`
- Google API credentials (`credentials.json`) obtained from Google Cloud Console
- Anthropic API key (set as `ANTHROPIC_API_KEY` environment variable)
- `keybert`, `sentence-transformers`, `scikit-learn` (for advanced topic extraction)
- `spacy`, `sumy` (for contextual summarization and NER/event detection)

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

    By default, this analyzes newsletters from the past 7 days. See Command-line Options below to customize.

    **Example: Use the advanced KeyBERT-based NLP method (default):**
    ```bash
    python main.py --days 3 --nlp-method keybert
    ```
    **Example: Use the classic n-gram frequency method:**
    ```bash
    python main.py --days 3 --nlp-method classic
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

## Functional Specification

This section provides a detailed breakdown of the tool's internal workings.

### 1. Overview

The tool automates the process of retrieving, analyzing, and summarizing AI-focused newsletters from Gmail, generating a user-focused report.

### 2. Core Functionality

#### 2.1. Gmail Authentication & Retrieval
-   **Authentication:** Uses OAuth 2.0 via `google-auth-oauthlib` and `google-api-python-client`. Requires `credentials.json` for initial setup, stores/refreshes tokens in `token.json`. Handles token expiry and refresh.
-   **Email Retrieval:** Queries the Gmail API using `service.users().messages().list()` with `q="label:ai-newsletter after:YYYY/MM/DD"`. Fetches full message content (`format='full'`) for matching message IDs.
-   **Content Extraction:** Parses message payloads using the `email` module. Extracts 'Subject', 'Date', and 'From' headers. Decodes body content (prioritizing `text/plain`, falling back to basic HTML stripping from `text/html`) from base64 encoding.

#### 2.2. Content Processing & Analysis
-   **Text Aggregation:** Concatenates body text and subject lines from all retrieved newsletters.
-   **Recency Weighting (Optional, Default: ON):** Parses email 'Date' headers using `email.utils.parsedate_to_datetime`. Calculates a weight for each newsletter based on its recency within the fetched date range. Repeats newsletter content (text and subjects) proportionally to this weight before analysis.
-   **NLP Preprocessing:** Uses `nltk` for:
    -   Tokenization (`word_tokenize`).
    -   Stopword removal (standard English stopwords + custom list including common newsletter/AI terms).
    -   Filters out non-alphabetic tokens and short words.
-   **Key Topic Extraction:**
    -   Calculates frequency of remaining words (unigrams).
    -   Generates and counts frequency of bigrams and trigrams (`nltk.util.ngrams`).
    -   Extracts 2-4 word phrases from subject lines, removing common prefixes/labels. Gives subject phrases significantly higher weight, further boosted by "breaking news" keyword indicators (`breaking`, `launched`, etc.).
    -   Combines frequencies, weighting n-grams and subject phrases higher than single words.
    -   Identifies top candidate topics/phrases based on weighted frequency.
    -   Performs simple clustering: groups candidates sharing words to avoid redundancy.
    -   Selects the top N (default 5) most frequent terms from distinct clusters as final topics, potentially listing related terms within a topic.

#### 2.3. LLM-Powered Insight Generation
-   **Context Preparation:** For each key topic, finds relevant sentences (snippets) from the newsletter bodies. Identifies potential "breaking news" items by checking subjects and initial body content of the 3 most recent newsletters for keywords like `launched`, `announced`, etc.
-   **LLM Interaction:** Uses the `anthropic` library to call the Claude API (model `claude-3-opus-20240229`). Requires `ANTHROPIC_API_KEY` environment variable.
-   **Structured Prompting:** Constructs a detailed prompt including:
    -   Instructions to act as an AI consultant summarizing for regular users.
    -   Guidance to focus on significant, distinct developments, practical impact, and real-world relevance.
    -   Emphasis on prioritizing major news and recent/breaking developments.
    -   Key topics and their associated text snippets.
    -   A specific section listing identified recent/breaking developments.
    -   A required output format (Markdown headings: "### Title", "**What's New:**", "**Why It Matters:**", "**Practical Impact:**").
-   **Response Processing:** Extracts the text content from the LLM's response.

#### 2.4. Report Generation
-   **Date Range Determination:** Finds the earliest and latest dates from parsed newsletter headers to create an accurate report title range and filename component.
-   **Report Structure:** Assembles the final Markdown report including:
    -   Title and accurate date range.
    -   The formatted LLM analysis.
    -   An optional "Just In" section (Default: ON): Lists cleaned subject lines from newsletters received in the last ~24 hours, highlighting those with breaking news indicators.
    -   A "Newsletter Sources" section: Lists unique senders, counts, and attempts to generate mailto: and website links from sender information.
    -   A brief methodology paragraph.
-   **Output:** Writes the report string to a file: `ai_newsletter_summary_{start_date}_to_{end_date}.md`.

### 3. Dependencies (Packages)

-   `google-api-python-client`
-   `google-auth-httplib2`
-   `google-auth-oauthlib`
-   `nltk` (requires `punkt`, `stopwords` data)
-   `anthropic`
-   `python-dotenv`
-   `python-dateutil`

### 4. Error Handling

-   Provides guidance messages if NLTK resource downloads fail.
-   Handles exceptions during credential loading/refreshing (`token.json`), suggesting re-authentication.
-   Includes `try-except` blocks for potential date parsing errors.
-   Uses a main `try-except` block to catch and print general errors during tool execution.

## Acknowledgements

This tool leverages the following services and libraries:

-   [Google Gmail API](https://developers.google.com/gmail/api/) for email access.
-   [NLTK (Natural Language Toolkit)](https://www.nltk.org/) for text processing.
-   [Anthropic Claude API](https://www.anthropic.com/) for AI-powered analysis and summarization.
