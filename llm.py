import os
import re
import anthropic
from nltk.tokenize import sent_tokenize

def analyze_with_llm(newsletters, topics):
    """Use an LLM (like Anthropic's Claude) to provide deeper insights about key topics."""
    anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
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
        topic_snippets[base_topic] = snippets[:10]
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
        body_first_para = ' '.join(sent_tokenize(nl['body'])[:5])
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
    for topic, snippets in topic_snippets.items():
        prompt += f"TOPIC: {topic}\n"
        prompt += f"SNIPPETS: {' '.join(snippets[:5])}\n\n"
    if recent_developments:
        prompt += "RECENT BREAKING DEVELOPMENTS (These may be significant even if mentioned in fewer newsletters):\n\n"
        for dev in recent_developments:
            prompt += f"SUBJECT: {dev['subject']}\n"
            prompt += f"DATE: {dev['date']}\n"
            prompt += f"CONTENT: {dev['content'][:500]}...\n\n"
    prompt += """\nPlease format your response as follows for each of the top 5 developments, ensuring DIVERSITY across topics:\n\n### 1. [Most Significant Development]\n**What's New:** [Brief description of what happened, prioritizing the core development rather than secondary features]\n**Why It Matters:** [Clear explanation for regular people about why this matters in their daily lives]\n**Practical Impact:** [2-3 specific actions, opportunities, or ways regular people can benefit from or engage with this development]\n\nIMPORTANT GUIDELINES:\n1. Headlines should focus on the most significant aspects from the newsletters - whether it's a major product launch, important research, policy change, or industry trend\n2. When a major development appears in multiple newsletters, prioritize it appropriately\n3. For product launches, focus on the product itself, not demonstrations (e.g., \"Anthropic Launches Claude 3.7 Sonnet\" rather than \"Claude AI Plays Pokémon\")\n4. Ensure all 5 topics are DISTINCT from each other - avoid multiple topics about the same general subject\n5. If you see multiple submissions about the same topic (e.g., multiple security issues), consolidate them into ONE topic\n6. \"Why It Matters\" should explain real-world implications for regular users, not just the tech industry\n7. \"Practical Impact\" must be truly actionable - what can regular people DO with this information?\n8. Keep each section concise but informative\n9. Sort by importance (most important first)\n10. IMPORTANT: Pay close attention to the RECENT BREAKING DEVELOPMENTS section - these items may be significant even if they're not mentioned in many newsletters, because they're very new. Include at least one of these if it's substantive and important.\n\nLook broadly across different domains like: AI applications, new models, business developments, security, ethics, regulation, research breakthroughs, etc.\n"""
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=2000,
        system="You are an AI consultant helping summarize AI newsletter content for regular people. Your primary goal is to identify the MOST SIGNIFICANT developments across different domains of AI, based on what appears in the newsletters being analyzed. When writing headlines, focus on the substantive development rather than secondary features or demonstrations (e.g., 'Anthropic Launches Claude 3.7' rather than 'Claude AI Plays Pokémon'). Make the 'Why It Matters' section relevant to everyday life, and ensure the 'Practical Impact' section provides specific, actionable advice that regular people can implement. Be sure to include brand new developments (even if only mentioned in 1-2 newsletters) if they appear to be significant. Format your response with markdown headings and sections.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text 