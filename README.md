# AI Newsletter Summarizer

This tool automatically summarizes AI-related newsletters from your Gmail account, extracting key topics and generating actionable insights using natural language processing and AI.

## Features

- Automatically fetches emails tagged with "ai newsletter" from your Gmail account
- Extracts and analyzes content from multiple newsletter sources
- Identifies key topics and trends across newsletters
- Uses Claude AI to generate summaries focused on practical applications
- Outputs a markdown report with the top 5 AI developments and why they matter

## Requirements

- Python 3.7+
- Gmail account with newsletters tagged/labeled as "ai-newsletter"
- Google API credentials
- Anthropic API key (for Claude AI access)

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/newsletter_summary.git
cd newsletter_summary
```

2. **Set up a virtual environment**

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up Google OAuth credentials**

- Go to the [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project
- Enable the Gmail API for your project
- Create OAuth 2.0 credentials (Desktop application type)
- Download the credentials JSON file
- Save it as `credentials.json` in the project directory

5. **Get an Anthropic API key**

- Sign up at [Anthropic](https://www.anthropic.com/)
- Obtain an API key from your account dashboard

6. **Create a .env.local file**

Create a file named `.env.local` in the project directory with:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Usage

1. **Setup Gmail labels**

In your Gmail account, create a label named "ai-newsletter" and apply it to your AI newsletters.

2. **Activate the virtual environment**

Before running the script, make sure your virtual environment is activated:

```bash
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

3. **Run the script**

```bash
python summ.py --days 7
```

This will analyze newsletters from the past 7 days. You can adjust the number of days as needed.

4. **First-time authentication**

The first time you run the script, it will open a browser window for you to authenticate with your Google account and grant permission to access your Gmail. After successful authentication, the credentials will be saved in `token.json` for future use.

5. **View the results**

The script will generate a markdown file named `ai_newsletter_summary_YYYYMMDD.md` with your summarized newsletter content.

## Customization

- To modify the number of topics extracted, adjust the `num_topics` parameter in the `extract_key_topics` function
- To change the LLM prompt or analysis approach, edit the `analyze_with_llm` function
- To customize the report format, modify the `generate_report` function

## Troubleshooting

- **NLTK Resource Errors**: If you encounter errors related to NLTK resources, try running:
  ```python
  import nltk
  nltk.download('punkt')
  nltk.download('stopwords')
  ```

- **Authentication Issues**: If you encounter authentication problems, delete the `token.json` file and try again

- **API Limits**: Be aware of the rate limits for both the Gmail API and Anthropic API

## License

[MIT License](LICENSE)

## Acknowledgements

This tool uses the Gmail API, NLTK for natural language processing, and Anthropic's Claude AI for generating insights from newsletter content. 