import re
from collections import Counter
import datetime
import json
import os
from urllib.parse import urlparse

def generate_report(newsletters, topics, llm_analysis, days):
    """Generate a final report with key insights."""
    newsletter_sources = Counter([nl['sender'] for nl in newsletters])
    newsletter_dates = []
    newsletter_with_dates = []
    for i, nl in enumerate(newsletters):
        try:
            from email.utils import parsedate_to_datetime
            date_obj = parsedate_to_datetime(nl['date'])
            newsletter_dates.append(date_obj)
            newsletter_with_dates.append((i, nl, date_obj))
        except Exception as e:
            print(f"Warning: Could not parse date '{nl['date']}': {str(e)}")
    if newsletter_dates:
        earliest_date = min(newsletter_dates)
        latest_date = max(newsletter_dates)
        run_time = datetime.datetime.now()
        date_range = f"## {earliest_date.strftime('%B %d')} to {latest_date.strftime('%B %d, %Y, %H:%M')} (summary run at {run_time.strftime('%Y-%m-%d %H:%M')})"
        filename_date_range = f"{earliest_date.strftime('%Y%m%d')}_to_{run_time.strftime('%Y%m%d_%H%M')}"
    else:
        earliest_date = datetime.datetime.now() - datetime.timedelta(days=days)
        run_time = datetime.datetime.now()
        date_range = f"## Week of {earliest_date.strftime('%B %d')} to {run_time.strftime('%B %d, %Y, %H:%M')} (summary run at {run_time.strftime('%Y-%m-%d %H:%M')})"
        filename_date_range = f"{earliest_date.strftime('%Y%m%d')}_to_{run_time.strftime('%Y%m%d_%H%M')}"
    very_recent_newsletters = []
    cutoff_date = latest_date - datetime.timedelta(days=1)
    for i, nl, date_obj in newsletter_with_dates:
        if date_obj >= cutoff_date:
            very_recent_newsletters.append(nl)
    breaking_news_section = ""
    if very_recent_newsletters:
        breaking_news_section = "\n## JUST IN: LATEST DEVELOPMENTS\n\n"
        breaking_news_section += "These items are from the most recent newsletters (last 24 hours) and may represent emerging trends:\n\n"
        breaking_news_indicators = ['breaking', 'just in', 'just announced', 'new release', 
                                   'launches', 'launched', 'announces', 'announced', 
                                   'releases', 'released', 'introduces', 'introduced',
                                   'unveils', 'unveiled', 'debuts', 'just now']
        for nl in very_recent_newsletters:
            subject = nl['subject']
            clean_subject = re.sub(r'^\[.*?\]', '', subject).strip()
            clean_subject = re.sub(r'^.*?:', '', clean_subject).strip()
            highlight = any(indicator in subject.lower() for indicator in breaking_news_indicators)
            if highlight:
                breaking_news_section += f"- 🔥 **{clean_subject}** (via {nl['sender'].split('<')[0].strip()})\n"
            else:
                breaking_news_section += f"- {clean_subject} (via {nl['sender'].split('<')[0].strip()})\n"
    report = f"""
# AI NEWSLETTER SUMMARY
{date_range}

## TOP 5 AI DEVELOPMENTS THIS WEEK

{llm_analysis}
"""
    if breaking_news_section:
        report += breaking_news_section
    # Load or initialize website cache
    website_cache_path = 'newsletter_websites.json'
    if os.path.exists(website_cache_path):
        with open(website_cache_path, 'r') as f:
            website_cache = json.load(f)
    else:
        website_cache = {}
    # Curated mapping for known newsletters (extend as needed)
    curated_websites = {
        'the neuron': 'https://www.theneurondaily.com',
        'tldr ai': 'https://www.tldrnewsletter.com',
        'tldr': 'https://www.tldrnewsletter.com',
        'the rundown ai': 'https://www.therundown.ai',
        'ai breakfast': 'https://aibreakfast.substack.com',
        "ben's bites": 'https://www.bensbites.co',
        'alpha signal': 'https://alphasignal.ai',
        'unwind ai': 'https://unwindai.com',
        'simon willison': 'https://simonwillison.net',
        'peter yang': 'https://creatoreconomy.so',
        # Add more as needed
    }
    def normalize(text):
        return re.sub(r'[^a-z0-9]', '', text.lower())
    def domain_from_email(email):
        domain = email.split('@')[-1]
        domain = re.sub(r'^(mail|news|info|newsletter)\.', '', domain)
        return domain
    def plausible_homepage_from_body(body, newsletter_name=None):
        urls = re.findall(r'https?://[\w\.-]+(?:/[\w\-\./?%&=]*)?', body)
        # Filter out forms, tracking, deep paths, etc.
        filtered = [u for u in urls if not any(x in u for x in ['form', 'track', 'unsubscribe', 'pixel', 'img', 'logo', 'pricing', 'cdn-cgi', 'utm_', 'jwt_token', 'viewform'])]
        # Prefer root domains
        for url in filtered:
            parsed = urlparse(url)
            if parsed.path in ('', '/', '/home'):
                return url
        # As fallback, return first filtered
        if filtered:
            return filtered[0]
        return None
    report += f"""
## NEWSLETTER SOURCES

This week's insights were gathered from {len(newsletters)} newsletters across {len(newsletter_sources)} sources:

"""
    for source, count in newsletter_sources.most_common():
        matching_nl = next((nl for nl in newsletters if nl['sender'] == source), None)
        if matching_nl:
            match = re.match(r'(.*?)\s*<(.+?)>', source)
            if match:
                name, email = match.groups()
            else:
                name = source
                email = None
            cache_key = name.strip().lower()
            cache_entry = website_cache.get(cache_key)
            website_url = None
            verified = False
            # 1. Curated mapping
            norm_name = normalize(name)
            curated_match = None
            for k, v in curated_websites.items():
                if normalize(k) in norm_name:
                    curated_match = v
                    break
            if cache_entry and cache_entry.get('verified'):
                website_url = cache_entry['url']
                verified = True
            elif curated_match:
                website_url = curated_match
                verified = True
            # 2. Sender domain if it matches newsletter name
            if not website_url and email:
                domain = domain_from_email(email)
                if any(part in domain for part in norm_name.split() if len(part) > 3):
                    website_url = f"https://{domain}"
                    verified = False
            # 3. Fallback: plausible homepage from body
            if not website_url:
                website_url = plausible_homepage_from_body(matching_nl['body'], newsletter_name=name)
                verified = False
            # Update cache
            if website_url:
                # If from curated, always mark as verified
                if curated_match and website_url == curated_match:
                    website_cache[cache_key] = {"url": website_url, "verified": True}
                else:
                    website_cache[cache_key] = {"url": website_url, "verified": verified}
            # Format: - [Newsletter Name](Website URL) - N issues
            if website_url:
                report += f"- [{name.strip()}]({website_url}) - {count} issues\n"
            else:
                report += f"- {name.strip()} - {count} issues\n"
    # Save updated cache
    with open(website_cache_path, 'w') as f:
        json.dump(website_cache, f, indent=2)
    report += "\n## METHODOLOGY\n"
    report += "This report was generated by analyzing AI newsletters tagged in Gmail. "
    report += "Key topics were identified using frequency analysis and natural language processing, "
    report += "with a focus on practical implications for regular users rather than industry competition."
    return report, filename_date_range 