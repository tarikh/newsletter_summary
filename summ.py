#!/usr/bin/env python3
"""
AI Newsletter Summarizer

This script:
1. Logs into a Gmail account using OAuth
2. Retrieves emails tagged with "ai newsletter" from the past week
3. Extracts and processes the content
4. Summarizes key topics and actionable insights for regular users
5. Outputs a report focused on practical applications rather than model competition

Usage:
    python summ.py --days 7
"""

import os
import base64
import email
import json
import argparse
from email.header import decode_header
import datetime
from dateutil.relativedelta import relativedelta
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import anthropic
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv('.env.local')

# Download required NLTK resources
def download_nltk_resources():
    """Download necessary NLTK resources with error handling."""
    try:
        resources = ['punkt', 'stopwords']
        for resource in resources:
            nltk.download(resource, quiet=False)
        
        # Additional download for punkt_tab (needed for tokenization)
        try:
            nltk.download('punkt_tab', quiet=False)
        except:
            # If punkt_tab isn't available as a separate download
            # The error might occur in a different way
            pass
            
        print("NLTK resources successfully loaded")
    except Exception as e:
        print(f"Error with NLTK resources: {str(e)}")
        print("Please run the following commands in a Python shell:")
        print("  import nltk")
        print("  nltk.download('punkt')")
        print("  nltk.download('stopwords')")
        print("  nltk.download('punkt_tab')")
        raise
        
download_nltk_resources()

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate with Gmail API using OAuth."""
    creds = None
    
    # Check if token.json exists (for saved credentials)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_info(
            json.loads(open('token.json').read()))
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def get_ai_newsletters(service, days=7):
    """Get emails tagged with 'ai newsletter' from the past week."""
    # Calculate date for 7 days ago
    date_from = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y/%m/%d')
    
    # Create query to find emails with the label and from the past week
    query = f"label:ai-newsletter after:{date_from}"
    
    # Get list of messages matching the query
    result = service.users().messages().list(userId='me', q=query).execute()
    messages = result.get('messages', [])
    
    newsletters = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        
        # Extract email details
        payload = msg['payload']
        headers = payload['headers']
        
        # Get subject and date
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No Date')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
        
        # Get email body
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    # Extract text from HTML (basic approach)
                    html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    body = re.sub('<[^<]+?>', ' ', html)  # Simple HTML tag removal
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        newsletters.append({
            'subject': subject,
            'date': date,
            'sender': sender,
            'body': body
        })
    
    return newsletters

def extract_key_topics(newsletters, num_topics=5):
    """Extract key topics from newsletters using more advanced NLP techniques."""
    # Combine all newsletter content
    all_text = " ".join([nl['body'] for nl in newsletters])
    
    # Extract and process subject lines with additional weighting
    subjects_text = " ".join([nl['subject'] for nl in newsletters])
    # Repeat subject lines multiple times to give them more weight
    weighted_subjects = " ".join([subjects_text] * 5)  # Give subject lines 5x weight
    
    # Combine body text with weighted subject lines
    combined_text = all_text + " " + weighted_subjects
    
    # Tokenize and remove stopwords
    stop_words = set(stopwords.words('english'))
    additional_stops = {'ai', 'artificial', 'intelligence', 'ml', 'model', 'models', 'news', 
                        'newsletter', 'week', 'weekly', 'new', 'https', 'com', 'www', 'email',
                        'subscribe', 'click', 'link', 'read', 'more', 'today', 'tomorrow',
                        'yesterday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                        'saturday', 'sunday', 'month', 'year', 'day', 'time', 'latest',
                        # Image related terms that are newsletter artifacts
                        'view', 'image', 'caption', 'view image', 'image caption', 
                        'alt', 'alt text', 'photo', 'picture', 'thumbnail', 'gif',
                        # Common newsletter footer terms
                        'unsubscribe', 'update', 'preferences', 'profile', 'contact',
                        'privacy', 'policy', 'terms', 'service', 'copyright',
                        # Time-related terms that don't indicate topics
                        'minute', 'minutes', 'hour', 'hours', 'second', 'seconds',
                        # Common comparison words that aren't topics
                        'like', 'such', 'similar', 'compared', 'example'}
    stop_words.update(additional_stops)
    
    # Process subject lines separately for additional topic extraction
    subject_phrases = []
    for nl in newsletters:
        # Clean and tokenize subject
        subject = nl['subject'].lower()
        # Remove common newsletter prefixes like "[Newsletter]" or "Weekly:"
        subject = re.sub(r'^\[.*?\]', '', subject).strip()
        subject = re.sub(r'^.*?:', '', subject).strip()
        
        # Extract potential topic phrases (2-4 word phrases)
        subject_words = [w for w in word_tokenize(subject) if w.isalpha() and w not in stop_words and len(w) > 3]
        if len(subject_words) >= 2:
            # Extract multi-word phrases from subjects
            for i in range(len(subject_words)-1):
                if i+1 < len(subject_words):
                    subject_phrases.append(' '.join(subject_words[i:i+2]))
                if i+2 < len(subject_words):
                    subject_phrases.append(' '.join(subject_words[i:i+3]))
                if i+3 < len(subject_words):
                    subject_phrases.append(' '.join(subject_words[i:i+4]))
    
    # Tokenize and filter main text
    words = word_tokenize(combined_text.lower())
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
    
    # Extract n-grams (1-3) to capture multi-word concepts
    from nltk.util import ngrams
    bigrams = list(ngrams(filtered_words, 2))
    trigrams = list(ngrams(filtered_words, 3))
    
    # Convert n-grams to strings
    bigram_phrases = [' '.join(bg) for bg in bigrams]
    trigram_phrases = [' '.join(tg) for tg in trigrams]
    
    # Count frequencies for words and phrases
    from collections import Counter
    word_freq = Counter(filtered_words)
    bigram_freq = Counter(bigram_phrases)
    trigram_freq = Counter(trigram_phrases)
    subject_phrase_freq = Counter(subject_phrases)
    
    # Combine and weight the counts (give higher weight to multi-word phrases)
    combined_freq = word_freq.copy()
    for bg, count in bigram_freq.items():
        combined_freq[bg] = count * 2  # Weight bigrams higher
    for tg, count in trigram_freq.items():
        combined_freq[tg] = count * 3  # Weight trigrams even higher
    
    # Add subject-derived phrases with even higher weight
    for phrase, count in subject_phrase_freq.items():
        if phrase in combined_freq:
            combined_freq[phrase] += count * 10  # Give subject phrases 10x more weight
        else:
            combined_freq[phrase] = count * 10
    
    # Get candidate topics (more than needed for filtering)
    candidate_topics = combined_freq.most_common(num_topics * 5)
    
    # Cluster similar topics using a simple similarity measure
    def are_related(topic1, topic2):
        # Check if topics share any words
        words1 = set(topic1.split())
        words2 = set(topic2.split())
        return len(words1.intersection(words2)) > 0
    
    # Group related topics
    topic_clusters = []
    for topic, count in candidate_topics:
        added_to_cluster = False
        for i, cluster in enumerate(topic_clusters):
            if any(are_related(topic, t) for t, _ in cluster):
                topic_clusters[i].append((topic, count))
                added_to_cluster = True
                break
        if not added_to_cluster:
            topic_clusters.append([(topic, count)])
    
    # Sort clusters by the highest count in each cluster
    topic_clusters.sort(key=lambda cluster: max(count for _, count in cluster), reverse=True)
    
    # Extract the final diverse topics
    final_topics = []
    for cluster in topic_clusters:
        if len(final_topics) >= num_topics:
            break
        
        # Use the most frequent term as the main topic
        main_topic, _ = max(cluster, key=lambda x: x[1])
        
        # Add related terms (up to 3)
        related_terms = [t for t, _ in sorted(cluster, key=lambda x: x[1], reverse=True)[1:4] 
                        if t != main_topic]
        
        if related_terms:
            final_topics.append(f"{main_topic} ({', '.join(related_terms)})")
        else:
            final_topics.append(main_topic)
    
    # Ensure we have the requested number of topics
    if len(final_topics) < num_topics:
        # If we couldn't find enough diverse topics, just add the remaining top topics
        remaining_topics = [t for t, _ in candidate_topics if t not in ' '.join(final_topics)]
        final_topics.extend(remaining_topics[:num_topics - len(final_topics)])
    
    return final_topics[:num_topics]  # Limit to requested number of topics

def analyze_with_llm(newsletters, topics):
    """Use an LLM (like Anthropic's Claude) to provide deeper insights about key topics."""
    # Set up Anthropic API (requires key)
    anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    # Extract relevant snippets for each topic
    topic_snippets = {}
    for topic in topics:
        base_topic = topic.split(' (')[0] if ' (' in topic else topic
        related_terms = re.findall(r'\((.*?)\)', topic)[0].split(', ') if ' (' in topic else []
        search_terms = [base_topic] + related_terms
        
        snippets = []
        for nl in newsletters:
            sentences = sent_tokenize(nl['body'])
            for sentence in sentences:
                if any(term.lower() in sentence.lower() for term in search_terms):
                    snippets.append(sentence)
        
        topic_snippets[base_topic] = snippets[:10]  # Limit to 10 snippets per topic
    
    # Prepare prompt for LLM
    prompt = """Based on the following AI newsletter content, identify and analyze the 5 most important developments or trends. Focus on DIVERSITY - ensure you cover distinct topics rather than different aspects of the same topic:

"""
    
    for topic, snippets in topic_snippets.items():
        prompt += f"TOPIC: {topic}\n"
        prompt += f"SNIPPETS: {' '.join(snippets[:5])}\n\n"
    
    prompt += """
Please format your response as follows for each of the top 5 developments, ensuring DIVERSITY across topics:

### 1. [Most Significant Development]
**What's New:** [Brief description of what happened, prioritizing the core development rather than secondary features]
**Why It Matters:** [Clear explanation for regular people about why this matters in their daily lives]
**Practical Impact:** [2-3 specific actions, opportunities, or ways regular people can benefit from or engage with this development]

IMPORTANT GUIDELINES:
1. Headlines should focus on the most significant aspects from the newsletters - whether it's a major product launch, important research, policy change, or industry trend
2. When a major development appears in multiple newsletters, prioritize it appropriately
3. For product launches, focus on the product itself, not demonstrations (e.g., "Anthropic Launches Claude 3.7 Sonnet" rather than "Claude AI Plays Pokémon")
4. Ensure all 5 topics are DISTINCT from each other - avoid multiple topics about the same general subject
5. If you see multiple submissions about the same topic (e.g., multiple security issues), consolidate them into ONE topic
6. "Why It Matters" should explain real-world implications for regular users, not just the tech industry
7. "Practical Impact" must be truly actionable - what can regular people DO with this information?
8. Keep each section concise but informative
9. Sort by importance (most important first)

Look broadly across different domains like: AI applications, new models, business developments, security, ethics, regulation, research breakthroughs, etc.
"""
    
    # Get LLM response using Claude
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2000,
        system="You are an AI consultant helping summarize AI newsletter content for regular people. Your primary goal is to identify the MOST SIGNIFICANT developments across different domains of AI, based on what appears in the newsletters being analyzed. When writing headlines, focus on the substantive development rather than secondary features or demonstrations (e.g., 'Anthropic Launches Claude 3.7' rather than 'Claude AI Plays Pokémon'). Make the 'Why It Matters' section relevant to everyday life, and ensure the 'Practical Impact' section provides specific, actionable advice that regular people can implement. Format your response with markdown headings and sections.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.content[0].text

def generate_report(newsletters, topics, llm_analysis, days):
    """Generate a final report with key insights."""
    # Count newsletters processed
    newsletter_sources = Counter([nl['sender'] for nl in newsletters])
    
    # Parse dates from newsletters to determine the actual date range
    newsletter_dates = []
    for nl in newsletters:
        try:
            # Parse the date from each newsletter
            # The email date format can be complex, so using email.utils.parsedate_to_datetime
            from email.utils import parsedate_to_datetime
            date_obj = parsedate_to_datetime(nl['date'])
            newsletter_dates.append(date_obj)
        except Exception as e:
            # If we can't parse the date, we'll skip this newsletter for date range calculation
            print(f"Warning: Could not parse date '{nl['date']}': {str(e)}")
    
    # Determine date range from parsed dates
    if newsletter_dates:
        earliest_date = min(newsletter_dates)
        latest_date = max(newsletter_dates)
        date_range = f"## {earliest_date.strftime('%B %d')} to {latest_date.strftime('%B %d, %Y')}"
        # Create date range string for filename
        filename_date_range = f"{earliest_date.strftime('%Y%m%d')}_to_{latest_date.strftime('%Y%m%d')}"
    else:
        # Fallback to previous method if no dates could be parsed
        earliest_date = datetime.datetime.now() - datetime.timedelta(days=days)
        latest_date = datetime.datetime.now()
        date_range = f"## Week of {earliest_date.strftime('%B %d')} to {latest_date.strftime('%B %d, %Y')}"
        # Create date range string for filename
        filename_date_range = f"{earliest_date.strftime('%Y%m%d')}_to_{latest_date.strftime('%Y%m%d')}"
    
    report = f"""
# AI NEWSLETTER SUMMARY
{date_range}

## TOP 5 AI DEVELOPMENTS THIS WEEK

{llm_analysis}

## NEWSLETTER SOURCES

This week's insights were gathered from {len(newsletters)} newsletters across {len(newsletter_sources)} sources:

"""
    
    # Extract and format email links from sender info
    for source, count in newsletter_sources.most_common():
        # Find matching newsletter to get subject/link
        matching_nl = next((nl for nl in newsletters if nl['sender'] == source), None)
        if matching_nl:
            # Extract email and name from sender format "Name <email@domain.com>"
            match = re.match(r'(.*?)\s*<(.+?)>', source)
            if match:
                name, email = match.groups()
                # Extract domain from email to create a web link
                domain = email.split('@')[-1]
                web_link = f"https://www.{domain}"
                report += f"- [{name.strip()}](mailto:{email}) ([Website]({web_link})) - {count} issues\n"
            else:
                # Try to extract domain if source looks like an email
                if '@' in source:
                    domain = source.split('@')[-1]
                    web_link = f"https://www.{domain}"
                    report += f"- [{source}](mailto:{source}) ([Website]({web_link})) - {count} issues\n"
                else:
                    report += f"- [{source}](mailto:{source}) - {count} issues\n"
    
    report += "\n## METHODOLOGY\n"
    report += "This report was generated by analyzing AI newsletters tagged in Gmail. "
    report += "Key topics were identified using frequency analysis and natural language processing, "
    report += "with a focus on practical implications for regular users rather than industry competition."
    
    return report, filename_date_range

def main():
    """Main function to run the newsletter summarizer."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Summarize AI newsletters from Gmail.')
    parser.add_argument('--days', type=int, default=7, 
                        help='Number of days to look back for newsletters (default: 7)')
    args = parser.parse_args()
    
    try:
        # Authenticate with Gmail
        print("Authenticating with Gmail...")
        service = authenticate_gmail()
        
        # Get newsletters
        print(f"Retrieving AI newsletters from the past {args.days} days...")
        newsletters = get_ai_newsletters(service, days=args.days)
        print(f"Found {len(newsletters)} newsletters.")
        
        if not newsletters:
            print("No newsletters found. Check your Gmail labels or date range.")
            return
        
        # Extract key topics
        print("Extracting key topics...")
        topics = extract_key_topics(newsletters)
        print(f"Identified {len(topics)} key topics: {', '.join(topics)}")
        
        # Analyze content with LLM
        print("Analyzing newsletter content...")
        llm_analysis = analyze_with_llm(newsletters, topics)
        
        # Generate final report
        print("Generating report...")
        report, filename_date_range = generate_report(newsletters, topics, llm_analysis, args.days)
        
        # Save report to file
        report_filename = f"ai_newsletter_summary_{filename_date_range}.md"
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"Report saved to {report_filename}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()