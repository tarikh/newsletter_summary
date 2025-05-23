import os
import re
import anthropic
import datetime
# Add OpenAI import
try:
    import openai
except ImportError:
    openai = None
from yaspin import yaspin
from utils import clean_body
# Add requests for OpenRouter API
import requests
import json

def analyze_newsletters_unified(newsletters, num_topics=10, provider='openai', model=None):
    """
    Process newsletters in a single step - identifying topics and generating summaries.
    Now with OpenRouter support and custom model option.
    
    Args:
        newsletters: List of newsletter dictionaries
        num_topics: Number of topics to identify and summarize (default: 10)
        provider: 'openai', 'claude', or 'google'
        model: Optional custom OpenRouter model name, overrides provider if specified
        
    Returns:
        Tuple of (analysis_text, extracted_topic_titles)
    """
    # Prepare newsletter content
    content_parts = []
    
    for i, nl in enumerate(newsletters, 1):
        clean_content = clean_body(nl['body'], nl.get('body_format'))
        
        # Add structured newsletter entry with metadata
        content_parts.append(
            f"NEWSLETTER #{i}\n"
            f"SUBJECT: {nl['subject']}\n"
            f"SENDER: {nl['sender']}\n"
            f"DATE: {nl['date']}\n"
            f"CONTENT:\n{clean_content[:3000]}...\n\n"  # Truncate to manage token usage
        )
    
    newsletter_content = "\n".join(content_parts)
    
    # Build comprehensive prompt with source and link requirements
    prompt = f"""
Analyze these AI newsletters and identify the {num_topics} most significant and distinct topics.

For each topic:
1. Create a clear, concise headline
2. Provide "What's New" - a brief description of the development
3. Explain "Why It Matters" for regular people in their daily lives
4. Suggest "Practical Impact" with 2-3 specific actions people can take
5. At the end of each topic, add:
   - A line starting with "**Source:**" that lists the newsletter(s) where this information came from (e.g., "**Source:** The Neuron, TLDR AI")
   - Add a line "- 🔗 [Visit Website](URL)" with a direct link to the product, model, paper, or announcement being discussed (NOT a link to the newsletter itself) if and only if there is an identifiably authoritative link available in the newsletters.

Format your response with markdown:

### 1. [Topic Headline]
- **What's New:** [Brief description of the development]

- **Why It Matters:** [Explanation for regular users]

- **Practical Impact:** [2-3 specific actions or opportunities]

- **Source:** [Newsletter names that covered this topic]

- 🔗 [Visit Website](https://link-to-actual-product-or-announcement)

### 2. [Next Topic]
...and so on

GUIDELINES:
- Identify exactly {num_topics} topics unless there aren't enough distinct topics in the content
- Sort topics by importance (most important first)
- Focus on substantive developments, not newsletter metadata or advertisements
- Ensure topics are distinct from each other (avoid multiple topics about the same subject)
- Prioritize recent developments, major product launches, policy changes, or significant research
- Focus on topics relevant to regular people, not just AI researchers or specialists
- "Why It Matters" should explain real-world implications, not just industry impact
- "Practical Impact" must be truly actionable - what can regular people DO with this information?
- For "Source" information, list the actual newsletter names (e.g., "The Neuron", "TLDR AI", "AI Breakfast")
- For links, include URLs to the actual products/announcements when available, not to the newsletters

NEWSLETTER CONTENT:
{newsletter_content}
"""
    
    # Check if we should use OpenRouter
    use_openrouter = os.environ.get("USE_OPENROUTER", "true").lower() in ("true", "1", "yes")
    
    # Call the appropriate LLM
    analysis_text = ""
    if use_openrouter:
        print("Using OpenRouter for unified analysis")
        analysis_text = analyze_with_openrouter(prompt, provider, model)
    else:
        if provider == 'openai':
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": "You are an AI consultant helping summarize AI newsletter content for regular people."},
                    {"role": "user", "content": prompt}
                ]
            )
            analysis_text = response.choices[0].message.content
        else:  # Default to Claude if not OpenAI
            anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = anthropic_client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=3000,
                system="You are an AI consultant helping summarize AI newsletter content for regular people.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            analysis_text = response.content[0].text
    
    # Extract topic titles from the analysis for report metadata
    topic_titles = re.findall(r'###\s*\d+\.\s*(.*?)\n', analysis_text)
    
    return analysis_text, topic_titles

def analyze_with_openrouter(prompt, model_provider, custom_model=None):
    """
    Route LLM requests through OpenRouter while maintaining the original provider choice
    or using a custom model if specified.
    
    Args:
        prompt: The prompt to send to the LLM
        model_provider: 'claude', 'openai', or 'google' to determine which model to use
        custom_model: Optional custom OpenRouter model name that overrides the model_provider
    
    Returns:
        The LLM response
    """
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    # Map provider to actual OpenRouter model ID
    model_map = {
        'claude': "anthropic/claude-sonnet-4",
        'openai': "openai/gpt-4.1-mini",
        'google': "google/gemini-2.5-flash-preview-05-20"
    }
    
    # Choose between custom model or mapped provider
    if custom_model:
        model = custom_model
        print(f"Using custom OpenRouter model: {model}")
    else:
        if model_provider not in model_map:
            raise ValueError(f"Unknown model provider: {model_provider}")
        model = model_map[model_provider]
        print(f"Using mapped OpenRouter model: {model}")
    
    # Prepare the system message based on the provider
    system_message = "You are an AI consultant helping summarize AI newsletter content for regular people. Your primary goal is to identify the MOST SIGNIFICANT developments across different domains of AI, based on what appears in the newsletters being analyzed. When writing headlines, focus on the substantive development rather than secondary features or demonstrations (e.g., 'Anthropic Launches Claude 3.7' rather than 'Claude AI Plays Pokémon'). Make the 'Why It Matters' section relevant to everyday life, and ensure the 'Practical Impact' section provides specific, actionable advice that regular people can implement. Be sure to include brand new developments (even if only mentioned in 1-2 newsletters) if they appear to be significant. Format your response with markdown headings and sections. For each topic, include source information and relevant links to the actual products/announcements. IMPORTANT: Ignore or exclude any sponsored, advertorial, or ad content when identifying and summarizing key developments. Do not include advertisers or sponsors as top content, even if they appear frequently."
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "HTTP-Referer": "https://github.com/saadiq/newsletter_summary",  # Your application URL
        "X-Title": "AI Newsletter Summarizer",  # Your application name
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    }
    
    # Add tracing tags for cost analysis
    data["transforms"] = ["middle-out"]  # Enable detailed token breakdowns
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    data["route"] = f"newsletter_summary_{current_datetime}"  # For cost tracking
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(data)
    )
    
    if response.status_code != 200:
        raise Exception(f"Error from OpenRouter API: {response.text}")
    
    result = response.json()
    
    # Log usage information
    if 'usage' in result:
        tokens = result['usage']['total_tokens']
        # Optional: Save detailed cost data
        cost_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model": model,
            "provider": model_provider if not custom_model else "custom",
            "prompt_tokens": result['usage'].get('prompt_tokens', 0),
            "completion_tokens": result['usage'].get('completion_tokens', 0),
            "total_tokens": tokens,
            "cost": result['usage'].get('cost', 0)
        }
        
        log_cost_data(cost_log)
        
        print(f"OpenRouter call: {tokens} tokens used with {model}")
        if 'cost' in result['usage']:
            print(f"Estimated cost: ${result['usage']['cost']}")
    
    return result['choices'][0]['message']['content']

def log_cost_data(cost_data):
    """Save cost data to a JSON file for later analysis"""
    log_file = os.environ.get("OPENROUTER_COST_LOG", "openrouter_costs.json")
    
    # Create or append to the log file
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
    
    existing_data.append(cost_data)
    
    with open(log_file, 'w') as f:
        json.dump(existing_data, f, indent=2)

def analyze_with_fallback(prompt, provider='openai', model=None):
    """Try OpenRouter first, fall back to direct API if there's an error"""
    try:
        # Try OpenRouter
        return analyze_with_openrouter(prompt, provider, model)
    except Exception as e:
        print(f"Error using OpenRouter: {str(e)}")
        print("Falling back to direct API call...")
        
        # Force direct API mode temporarily
        old_setting = os.environ.get("USE_OPENROUTER", "true")
        os.environ["USE_OPENROUTER"] = "false"
        
        try:
            # Use direct API
            result = analyze_with_llm_direct(prompt, [], provider)
            return result
        finally:
            # Restore setting
            os.environ["USE_OPENROUTER"] = old_setting

def check_openrouter_status():
    """Check if OpenRouter is operational and your account is properly configured"""
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        return False, "OPENROUTER_API_KEY environment variable not set"
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, f"OpenRouter configured correctly. Rate limit: {data.get('rate_limit', 'unknown')}, remaining: {data.get('rate_limit_remaining', 'unknown')}"
        else:
            return False, f"OpenRouter API error: {response.text}"
    except Exception as e:
        return False, f"Error checking OpenRouter status: {str(e)}"

def analyze_with_llm_direct(prompt, topics=None, provider='claude'):
    """
    Generate analysis text directly from the LLM based on the provided prompt.
    This is a simplified version for fallback purposes.
    
    Args:
        prompt: The prompt to send to the LLM
        topics: Optional list of topics (not used in this function, but kept for API compatibility)
        provider: 'claude' or 'openai'
        
    Returns:
        The LLM response text
    """
    if provider == 'openai':
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": "You are an AI consultant helping summarize newsletter content."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    else:  # Default to Claude
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=3000,
            system="You are an AI consultant helping summarize newsletter content.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text