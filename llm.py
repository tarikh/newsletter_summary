import os
import re
import anthropic
from nltk.tokenize import sent_tokenize
# New imports for contextual summarization and NER/event detection
import spacy
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
import datetime
# Add OpenAI import
try:
    import openai
except ImportError:
    openai = None
from tqdm import tqdm
from yaspin import yaspin
from nlp import clean_body
# Add requests for OpenRouter API
import requests
import json

def analyze_newsletters_unified(newsletters, num_topics=10, provider='openai'):
    """
    Process newsletters in a single step - identifying topics and generating summaries.
    Now with OpenRouter support.
    
    Args:
        newsletters: List of newsletter dictionaries
        num_topics: Number of topics to identify and summarize (default: 10)
        provider: 'openai' or 'claude'
        
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
    
    # Build comprehensive prompt
    prompt = f"""
Analyze these AI newsletters and identify the {num_topics} most significant and distinct topics.

For each topic:
1. Create a clear, concise headline
2. Provide "What's New" - a brief description of the development
3. Explain "Why It Matters" for regular people in their daily lives
4. Suggest "Practical Impact" with 2-3 specific actions people can take

Format your response with markdown:

### 1. [Topic Headline]
**What's New:** [Brief description of the development]
**Why It Matters:** [Explanation for regular users]
**Practical Impact:** [2-3 specific actions or opportunities]

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

NEWSLETTER CONTENT:
{newsletter_content}
"""
    
    # Check if we should use OpenRouter
    use_openrouter = os.environ.get("USE_OPENROUTER", "true").lower() in ("true", "1", "yes")
    
    # Call the appropriate LLM
    analysis_text = ""
    if use_openrouter:
        print("Using OpenRouter for unified analysis")
        analysis_text = analyze_with_openrouter(prompt, provider)
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
        else:
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

def analyze_with_openrouter(prompt, model_provider):
    """
    Route LLM requests through OpenRouter while maintaining the original provider choice.
    
    Args:
        prompt: The prompt to send to the LLM
        model_provider: 'claude' or 'openai' to determine which model to use
    
    Returns:
        The LLM response
    """
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    # Map provider to actual OpenRouter model ID
    model_map = {
        'claude': "anthropic/claude-3-7-sonnet",
        'openai': "openai/gpt-4.1"
    }
    
    if model_provider not in model_map:
        raise ValueError(f"Unknown model provider: {model_provider}")
    
    model = model_map[model_provider]
    
    # Prepare the system message based on the provider
    system_message = "You are an AI consultant helping summarize AI newsletter content for regular people. Your primary goal is to identify the MOST SIGNIFICANT developments across different domains of AI, based on what appears in the newsletters being analyzed. When writing headlines, focus on the substantive development rather than secondary features or demonstrations (e.g., 'Anthropic Launches Claude 3.7' rather than 'Claude AI Plays Pokémon'). Make the 'Why It Matters' section relevant to everyday life, and ensure the 'Practical Impact' section provides specific, actionable advice that regular people can implement. Be sure to include brand new developments (even if only mentioned in 1-2 newsletters) if they appear to be significant. Format your response with markdown headings and sections. IMPORTANT: Ignore or exclude any sponsored, advertorial, or ad content when identifying and summarizing key developments. Do not include advertisers or sponsors as top content, even if they appear frequently."
    
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
            "provider": model_provider,
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

def analyze_with_fallback(prompt, provider='openai'):
    """Try OpenRouter first, fall back to direct API if there's an error"""
    try:
        # Try OpenRouter
        return analyze_with_openrouter(prompt, provider)
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
        # First check API status
        response = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
        
        if response.status_code == 200:
            key_info = response.json()
            
            # Check if key is valid and has credits
            if key_info.get('key'):
                return True, f"OpenRouter API key valid. Rate limit: {key_info.get('rateLimit', 'unknown')}"
            else:
                return False, "OpenRouter API key appears to be invalid"
        else:
            return False, f"OpenRouter API returned status code {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Error checking OpenRouter status: {str(e)}"

# Keep original implementation as a fallback
def analyze_with_llm_direct(prompt, topics=None, provider='claude'):
    """Direct API implementation for fallback"""
    if provider == 'claude':
        anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        # Use Claude 3.7 Sonnet
        response = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=2000,
            system="You are an AI consultant helping summarize AI newsletter content for regular people. Your primary goal is to identify the MOST SIGNIFICANT developments across different domains of AI, based on what appears in the newsletters being analyzed. When writing headlines, focus on the substantive development rather than secondary features or demonstrations (e.g., 'Anthropic Launches Claude 3.7' rather than 'Claude AI Plays Pokémon'). Make the 'Why It Matters' section relevant to everyday life, and ensure the 'Practical Impact' section provides specific, actionable advice that regular people can implement. Be sure to include brand new developments (even if only mentioned in 1-2 newsletters) if they appear to be significant. Format your response with markdown headings and sections. IMPORTANT: Ignore or exclude any sponsored, advertorial, or ad content when identifying and summarizing key developments. Do not include advertisers or sponsors as top content, even if they appear frequently.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    elif provider == 'openai':
        if openai is None:
            raise ImportError("openai package is not installed. Please install openai to use this provider.")
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider.")
        # Use the new OpenAI client interface (v1.x+)
        client = openai.OpenAI(api_key=openai_api_key)
        completion = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=[
                {"role": "system", "content": "You are an AI consultant helping summarize AI newsletter content for regular people. Your primary goal is to identify the MOST SIGNIFICANT developments across different domains of AI, based on what appears in the newsletters being analyzed. When writing headlines, focus on the substantive development rather than secondary features or demonstrations (e.g., 'Anthropic Launches Claude 3.7' rather than 'Claude AI Plays Pokémon'). Make the 'Why It Matters' section relevant to everyday life, and ensure the 'Practical Impact' section provides specific, actionable advice that regular people can implement. Be sure to include brand new developments (even if only mentioned in 1-2 newsletters) if they appear to be significant. Format your response with markdown headings and sections. IMPORTANT: Ignore or exclude any sponsored, advertorial, or ad content when identifying and summarizing key developments. Do not include advertisers or sponsors as top content, even if they appear frequently."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

# Modify the existing function to use OpenRouter when appropriate
def analyze_with_llm(newsletters, topics, provider='claude'):
    """
    Use an LLM to provide deeper insights about key topics.
    Now routes all requests through OpenRouter while maintaining the same interface.
    
    Args:
        provider: 'claude' or 'openai'
    """
    # All the existing preparations stay the same
    print(f"Using LLM provider: {provider}")
    
    # Prepare the prompt as usual
    print("Performing contextual summarization and NER for each topic (this may take a moment)...", flush=True)
    nlp = spacy.load("en_core_web_sm")
    summarizer = TextRankSummarizer()
    topic_context = {}
    event_verbs = [
        'launch', 'launched', 'announce', 'announced', 'release', 'released',
        'introduce', 'introduced', 'unveil', 'unveiled', 'debut', 'acquire', 'acquired',
        'partner', 'partnered', 'merge', 'merged', 'invest', 'invested', 'fund', 'funded',
        'appoint', 'appointed', 'join', 'joined', 'expand', 'expanded', 'collaborate', 'collaborated'
    ]
    with yaspin(text="", color="cyan") as spinner:
        for topic in topics:
            base_topic = topic.split(' (')[0] if ' (' in topic else topic
            related_terms = re.findall(r'\((.*?)\)', topic)[0].split(', ') if ' (' in topic else []
            search_terms = [base_topic] + related_terms
            # Gather all sentences relevant to the topic
            all_sentences = []
            all_text = ""
            for nl in newsletters:
                cleaned_body = clean_body(nl['body'], nl.get('body_format'))
                sentences = sent_tokenize(cleaned_body)
                for sentence in sentences:
                    if any(term.lower() in sentence.lower() for term in search_terms):
                        all_sentences.append(sentence)
                        all_text += sentence + " "
            # Contextual summarization using TextRank
            parser = PlaintextParser.from_string(all_text, Tokenizer("english"))
            summary_sentences = [str(s) for s in summarizer(parser.document, 5)]
            # NER using spaCy
            doc = nlp(all_text)
            entities = set([ent.text for ent in doc.ents if ent.label_ in {"ORG", "PERSON", "PRODUCT", "GPE", "EVENT"}])
            # Event detection: sentences with event verbs
            event_sentences = []
            for sent in doc.sents:
                if any(verb in sent.text.lower() for verb in event_verbs):
                    event_sentences.append(sent.text)
            topic_context[base_topic] = {
                "entities": list(entities)[:10],
                "events": event_sentences[:5],
                "snippets": summary_sentences if summary_sentences else all_sentences[:5]
            }
        spinner.ok("✔")
    from email.utils import parsedate_to_datetime
    newsletter_with_dates = []
    for i, nl in enumerate(newsletters):
        try:
            date_obj = parsedate_to_datetime(nl['date'])
            newsletter_with_dates.append((i, nl, date_obj))
        except Exception as e:
            newsletter_with_dates.append((i, nl, datetime.datetime.now()))
    newsletter_with_dates.sort(key=lambda x: x[2], reverse=True)
    sorted_newsletters = [nl for _, nl, _ in newsletter_with_dates]
    recent_nl_count = min(3, len(sorted_newsletters))
    recent_newsletters = sorted_newsletters[:recent_nl_count]
    breaking_news_indicators = ['breaking', 'just in', 'just announced', 'new release', 
                               'launches', 'launched', 'announces', 'announced', 
                               'releases', 'released', 'introduces', 'introduced',
                               'unveils', 'unveiled', 'debuts', 'just now']
    recent_developments = []
    for nl in recent_newsletters:
        subject = nl['subject'].lower()
        body_first_para = ' '.join(sent_tokenize(clean_body(nl['body'], nl.get('body_format')))[:5])
        if any(indicator in subject.lower() for indicator in breaking_news_indicators):
            recent_developments.append({
                'subject': nl['subject'],
                'content': body_first_para,
                'date': nl['date'],
                'is_breaking': True
            })
        elif any(indicator in body_first_para.lower() for indicator in breaking_news_indicators):
            recent_developments.append({
                'subject': nl['subject'],
                'content': body_first_para,
                'date': nl['date'],
                'is_breaking': True
            })
    prompt = """Based on the following AI newsletter content, identify and analyze the 5 most important developments or trends. Focus on DIVERSITY - ensure you cover distinct topics rather than different aspects of the same topic:\n\n"""
    for topic, context in topic_context.items():
        prompt += f"TOPIC: {topic}\n"
        prompt += f"KEY ENTITIES: {', '.join(context['entities'])}\n"
        prompt += f"KEY EVENTS: {' | '.join(context['events'])}\n"
        prompt += f"CONTEXT SNIPPETS: {' '.join(context['snippets'])}\n\n"
    if recent_developments:
        prompt += "RECENT BREAKING DEVELOPMENTS (These may be significant even if mentioned in fewer newsletters):\n\n"
        for dev in recent_developments:
            prompt += f"SUBJECT: {dev['subject']}\n"
            prompt += f"DATE: {dev['date']}\n"
            prompt += f"CONTENT: {dev['content'][:500]}...\n\n"
    prompt += """\nPlease format your response as follows for each of the top 5 developments, ensuring DIVERSITY across topics:\n\n### 1. [Most Significant Development]\n**What's New:** [Brief description of what happened, prioritizing the core development rather than secondary features]\n**Why It Matters:** [Clear explanation for regular people about why this matters in their daily lives]\n**Practical Impact:** [2-3 specific actions, opportunities, or ways regular people can benefit from or engage with this development]\n\nIMPORTANT GUIDELINES:\n1. Headlines should focus on the most significant aspects from the newsletters - whether it's a major product launch, important research, policy change, or industry trend\n2. When a major development appears in multiple newsletters, prioritize it appropriately\n3. For product launches, focus on the product itself, not demonstrations (e.g., \\\"Anthropic Launches Claude 3.7 Sonnet\\\" rather than \\\"Claude AI Plays Pokémon\\\")\n4. Ensure all 5 topics are DISTINCT from each other - avoid multiple topics about the same general subject\n5. If you see multiple submissions about the same topic (e.g., multiple security issues), consolidate them into ONE topic\n6. \\\"Why It Matters\\\" should explain real-world implications for regular users, not just the tech industry\n7. \\\"Practical Impact\\\" must be truly actionable - what can regular people DO with this information?\n8. Keep each section concise but informative\n9. Sort by importance (most important first)\n10. IMPORTANT: Pay close attention to the RECENT BREAKING DEVELOPMENTS section - these items may be significant even if they're not mentioned in many newsletters, because they're very new. Include at least one of these if it's substantive and important.\n\nLook broadly across different domains like: AI applications, new models, business developments, security, ethics, regulation, research breakthroughs, etc.\n"""

    # Check if we should use direct API or OpenRouter
    use_openrouter = os.environ.get("USE_OPENROUTER", "true").lower() in ("true", "1", "yes")
    
    if use_openrouter:
        print("Routing through OpenRouter for cost tracking")
        return analyze_with_openrouter(prompt, provider)
    else:
        # Fallback to direct API calls
        return analyze_with_llm_direct(prompt, topics, provider) 