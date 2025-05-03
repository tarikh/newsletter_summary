import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from tqdm import tqdm
from yaspin import yaspin
import datetime
from bs4 import BeautifulSoup
from html_to_markdown import convert_to_markdown

LAYOUT_STOPWORDS = {
    'table', 'body', 'img', 'icon', 'h6', 'h1', 'h2', 'h3', 'h4', 'h5', 'div', 'span', 'header', 'footer', 'section', 'article', 'main', 'aside', 'nav', 'ul', 'li', 'ol', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot', 'responsive', 'container', 'row', 'col', 'cell', 'content', 'block', 'wrapper', 'panel', 'title', 'link', 'caption', 'figure', 'figcaption', 'hr', 'br', 'input', 'form', 'label', 'button', 'select', 'option', 'textarea', 'fieldset', 'legend', 'menu', 'item', 'list', 'card', 'media', 'meta', 'footer', 'sidebar', 'widget', 'banner', 'ad', 'promo', 'newsletter', 'subscribe', 'unsubscribe', 'view', 'online', 'email', 'address', 'logo', 'avatar', 'profile', 'author', 'date', 'time', 'read', 'more', 'click', 'here', 'update', 'preferences', 'privacy', 'policy', 'terms', 'service', 'copyright', 'minute', 'minutes', 'hour', 'hours', 'second', 'seconds', 'image', 'photo', 'picture', 'thumbnail', 'gif', 'alt', 'alt text', 'view image', 'image caption', 'caption', 'view', 'view online', 'view in browser', 'browser', 'web', 'site', 'website', 'unsubscribe', 'update', 'preferences', 'profile', 'contact', 'privacy', 'policy', 'terms', 'service', 'copyright', 'minute', 'minutes', 'hour', 'hours', 'second', 'seconds', 'like', 'such', 'similar', 'compared', 'example'
}

# Additional words to filter out that are related to newsletter-specific content
NEWSLETTER_METADATA = {
    'daily', 'weekly', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'journalist', 'curate', 'curator', 'welcome', 'subscribe', 'subscription', 'unsubscribe', 
    'download', 'follow', 'hiring', 'job', 'career', 'vacancy', 'position', 'apply', 
    'hey', 'hello', 'hi', 'dear', 'morning', 'afternoon', 'evening', 'thanks', 'thank', 
    'editor', 'join', 'team', 'forwarded', 'newsletter', 'sponsor', 'paid', 'advertise',
    'advertising', 'promotion', 'promotional', 'click', 'signup', 'sign-up', 'tldr',
    'account', 'login', 'log-in', 'statement', 'password', 'username', 'signin', 'sign-in',
    'authentication', 'bank', 'billing', 'bill', 'invoice', 'payment', 'directpay', 'debit',
    'credit', 'balance', 'withdraw', 'withdrawal', 'deposit', 'authorization', 'calendar',
    'calendly', 'onboarding', 'direct'
}

def is_layout_topic(topic):
    words = set(topic.lower().split())
    return any(word in LAYOUT_STOPWORDS for word in words)

def is_newsletter_metadata(topic):
    """Check if a topic is just newsletter metadata or self-promotion"""
    words = set(topic.lower().split())
    
    # Check against metadata terms
    metadata_match = any(word in NEWSLETTER_METADATA for word in words)
    
    # Look for day of week patterns
    weekday_pattern = any(day in topic.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
    
    # Look for patterns like "news ..." or "... news"
    news_pattern = 'news' in topic.lower()
    
    # Job/hiring related
    job_pattern = any(word in topic.lower() for word in ['hiring', 'job', 'career', 'position', 'vacancy', 'apply'])
    
    # Welcome/subscription related 
    welcome_pattern = any(word in topic.lower() for word in ['welcome', 'subscribe', 'unsubscribe', 'join', 'signup'])
    
    # Account/login/payment related
    account_pattern = any(word in topic.lower() for word in 
                         ['account', 'login', 'log', 'statement', 'password', 'payment', 'bank', 'billing'])
    
    # Month names which are often part of billing statements
    month_pattern = any(month in topic.lower() for month in 
                       ['january', 'february', 'march', 'april', 'may', 'june', 'july', 
                        'august', 'september', 'october', 'november', 'december'])
    
    return metadata_match or weekday_pattern or news_pattern or job_pattern or welcome_pattern or account_pattern or month_pattern

def clean_body(html, body_format=None):
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(['style', 'script', 'meta', 'link']):
            tag.decompose()
        for tag in soup.find_all(True):
            tag.attrs = {}
        cleaned_html = str(soup)
        cleaned_html = re.sub(r'(?s)@media[^{]+{[^}]+}', '', cleaned_html)
        cleaned_html = re.sub(r'(?s)\.[\w\-]+[^{]*{[^}]+}', '', cleaned_html)
        cleaned_html = re.sub(r'(?s){[^}]+}', '', cleaned_html)
        markdown = convert_to_markdown(cleaned_html, heading_style="atx")
        return markdown
    except Exception as e:
        return "[ERROR: Could not clean/convert this email]"

def extract_key_topics(newsletters, num_topics=10, return_scores=False):
    """Extract key topics from newsletters using more advanced NLP techniques.
    Now supports up to 10 topics by default."""
    newsletter_dates = []
    from email.utils import parsedate_to_datetime
    newsletter_with_dates = []
    for i, nl in enumerate(newsletters):
        try:
            date_obj = parsedate_to_datetime(nl['date'])
            newsletter_with_dates.append((i, nl, date_obj))
        except Exception as e:
            print(f"Warning: Could not parse date '{nl['date']}': {str(e)}")
            newsletter_with_dates.append((i, nl, datetime.datetime.now()))
    newsletter_with_dates.sort(key=lambda x: x[2], reverse=True)
    max_weight = 10
    min_weight = 1
    if len(newsletter_with_dates) > 1:
        newest_date = newsletter_with_dates[0][2]
        oldest_date = newsletter_with_dates[-1][2]
        date_range = (newest_date - oldest_date).total_seconds()
        if date_range == 0:
            recency_weights = {i: max_weight for i, _, _ in newsletter_with_dates}
        else:
            recency_weights = {}
            for i, _, date_obj in newsletter_with_dates:
                recency_factor = (date_obj - oldest_date).total_seconds() / date_range
                weight = min_weight + recency_factor * (max_weight - min_weight)
                recency_weights[i] = weight
    else:
        recency_weights = {i: max_weight for i, _, _ in newsletter_with_dates}
    all_text = ""
    subjects_text = ""
    for i, nl in enumerate(newsletters):
        weight = recency_weights[i]
        content_weight = max(1, int(weight))
        all_text += " ".join([clean_body(nl['body'])] * content_weight) + " "
        subjects_text += " ".join([nl['subject']] * content_weight) + " "
    weighted_subjects = " ".join([subjects_text] * 5)
    combined_text = all_text + " " + weighted_subjects
    stop_words = set(stopwords.words('english'))
    additional_stops = {'ai', 'artificial', 'intelligence', 'ml', 'model', 'models', 'news', 
                        'newsletter', 'week', 'weekly', 'new', 'https', 'com', 'www', 'email',
                        'subscribe', 'click', 'link', 'read', 'more', 'today', 'tomorrow',
                        'yesterday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                        'saturday', 'sunday', 'month', 'year', 'day', 'time', 'latest',
                        'view', 'image', 'caption', 'view image', 'image caption', 
                        'alt', 'alt text', 'photo', 'picture', 'thumbnail', 'gif',
                        'unsubscribe', 'update', 'preferences', 'profile', 'contact',
                        'privacy', 'policy', 'terms', 'service', 'copyright',
                        'minute', 'minutes', 'hour', 'hours', 'second', 'seconds',
                        'like', 'such', 'similar', 'compared', 'example'}
    stop_words.update(additional_stops)
    subject_phrases = []
    breaking_news_indicators = ['breaking', 'just in', 'just announced', 'new release', 
                                'launches', 'launched', 'announces', 'announced', 
                                'releases', 'released', 'introduces', 'introduced',
                                'unveils', 'unveiled', 'debuts', 'just now']
    for i, nl in enumerate(newsletters):
        weight = recency_weights[i]
        subject = nl['subject'].lower()
        has_breaking_indicator = any(indicator in subject for indicator in breaking_news_indicators)
        breaking_multiplier = 3 if has_breaking_indicator else 1
        subject = re.sub(r'^\[.*?\]', '', subject).strip()
        subject = re.sub(r'^.*?:', '', subject).strip()
        subject_words = [w for w in word_tokenize(subject) if w.isalpha() and w not in stop_words and len(w) > 3]
        if len(subject_words) >= 2:
            phrase_weight = int(weight * breaking_multiplier)
            for i in range(len(subject_words)-1):
                if i+1 < len(subject_words):
                    subject_phrases.extend([' '.join(subject_words[i:i+2])] * phrase_weight)
                if i+2 < len(subject_words):
                    subject_phrases.extend([' '.join(subject_words[i:i+3])] * phrase_weight)
                if i+3 < len(subject_words):
                    subject_phrases.extend([' '.join(subject_words[i:i+4])] * phrase_weight)
    words = word_tokenize(combined_text.lower())
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
    from nltk.util import ngrams
    bigrams = list(ngrams(filtered_words, 2))
    trigrams = list(ngrams(filtered_words, 3))
    bigram_phrases = [' '.join(bg) for bg in bigrams]
    trigram_phrases = [' '.join(tg) for tg in trigrams]
    word_freq = Counter(filtered_words)
    bigram_freq = Counter(bigram_phrases)
    trigram_freq = Counter(trigram_phrases)
    subject_phrase_freq = Counter(subject_phrases)
    combined_freq = word_freq.copy()
    for bg, count in bigram_freq.items():
        combined_freq[bg] = count * 2
    for tg, count in trigram_freq.items():
        combined_freq[tg] = count * 3
    for phrase, count in subject_phrase_freq.items():
        if phrase in combined_freq:
            combined_freq[phrase] += count * 10
        else:
            combined_freq[phrase] = count * 10
    candidate_topics = combined_freq.most_common(num_topics * 5)
    def are_related(topic1, topic2):
        words1 = set(topic1.split())
        words2 = set(topic2.split())
        return len(words1.intersection(words2)) > 0
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
    topic_clusters.sort(key=lambda cluster: max(count for _, count in cluster), reverse=True)
    final_topics = []
    final_topics_with_scores = []
    for cluster in topic_clusters:
        if len(final_topics) >= num_topics:
            break
        main_topic, main_count = max(cluster, key=lambda x: x[1])
        related_terms = [t for t, _ in sorted(cluster, key=lambda x: x[1], reverse=True)[1:4] 
                        if t != main_topic]
        if related_terms:
            topic_name = f"{main_topic} ({', '.join(related_terms)})"
            final_topics.append(topic_name)
            final_topics_with_scores.append((topic_name, main_count))
        else:
            final_topics.append(main_topic)
            final_topics_with_scores.append((main_topic, main_count))
    if len(final_topics) < num_topics:
        remaining_topics = [t for t, c in candidate_topics if t not in ' '.join(final_topics)]
        remaining_scores = [c for t, c in candidate_topics if t not in ' '.join(final_topics)]
        for i in range(min(num_topics - len(final_topics), len(remaining_topics))):
            final_topics.append(remaining_topics[i])
            final_topics_with_scores.append((remaining_topics[i], remaining_scores[i]))
    # Filter out layout-related topics and newsletter metadata
    filtered_topics = []
    filtered_topics_with_scores = []
    for i, topic in enumerate(final_topics):
        if not is_layout_topic(topic) and not is_newsletter_metadata(topic):
            filtered_topics.append(topic)
            filtered_topics_with_scores.append(final_topics_with_scores[i])
    if return_scores:
        return filtered_topics_with_scores[:num_topics]
    else:
        return filtered_topics[:num_topics]

def extract_key_topics_keybert(newsletters, num_topics=10, ngram_range=(1,3), top_n_candidates=50, return_scores=False):
    """Extract key topics using KeyBERT and semantic clustering with dynamic adjustment and fallback.
    Now supports up to 10 topics by default."""
    text = " ".join(clean_body(nl['body']) + " " + nl['subject'] for nl in newsletters)
    kw_model = KeyBERT(model='all-MiniLM-L6-v2')
    msg = "Extracting keyphrases with KeyBERT (this may take a moment)..."
    print(msg, flush=True)
    
    # Start with a higher number of candidates if we need many topics
    if num_topics > 5:
        top_n_candidates = max(top_n_candidates, num_topics * 5)
    
    with yaspin(text="", color="cyan") as spinner:
        keyphrases_with_scores = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=ngram_range,
            stop_words='english',
            top_n=top_n_candidates
        )
        spinner.ok("✔")
    
    keyphrases = [phrase for phrase, score in keyphrases_with_scores]
    if not keyphrases:
        return [] if not return_scores else []
    
    # Filter out irrelevant keyphrases before clustering
    filtered_keyphrases_with_scores = [(k, s) for k, s in keyphrases_with_scores 
                                     if not is_layout_topic(k) and not is_newsletter_metadata(k)]
    
    # If we filtered out too many, add back general AI-related ones
    if len(filtered_keyphrases_with_scores) < num_topics:
        for k, s in keyphrases_with_scores:
            if (k, s) not in filtered_keyphrases_with_scores and 'ai' in k.lower():
                filtered_keyphrases_with_scores.append((k, s))
    
    if not filtered_keyphrases_with_scores:
        filtered_keyphrases_with_scores = keyphrases_with_scores
        
    keyphrases_with_scores = filtered_keyphrases_with_scores
    keyphrases = [phrase for phrase, _ in keyphrases_with_scores]
    
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = embedder.encode(keyphrases)
    n_clusters = min(num_topics, len(keyphrases))
    if n_clusters < 2:
        if return_scores:
            return keyphrases_with_scores[:num_topics]
        else:
            return keyphrases[:num_topics]
    
    msg = "Clustering keyphrases (this may take a moment)..."
    print(msg, flush=True)
    with yaspin(text="", color="cyan") as spinner:
        clustering = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clustering.fit_predict(embeddings)
        spinner.ok("✔")
    
    cluster_to_phrases = {i: [] for i in range(n_clusters)}
    for idx, label in enumerate(labels):
        cluster_to_phrases[label].append((keyphrases[idx], keyphrases_with_scores[idx][1]))
    
    topics = []
    topics_with_scores = []
    used_indices = set()
    for phrases in cluster_to_phrases.values():
        phrases.sort(key=lambda x: x[1], reverse=True)
        top_phrase = phrases[0][0]
        top_score = phrases[0][1]
        topics.append(top_phrase)
        topics_with_scores.append((top_phrase, top_score))
        # Mark all indices in this cluster as used
        for phrase, _ in phrases:
            if phrase in keyphrases:
                used_indices.add(keyphrases.index(phrase))
    
    # If we have fewer than num_topics, fill in with next best unclustered keyphrases
    if len(topics) < num_topics:
        for idx, (phrase, score) in enumerate(keyphrases_with_scores):
            if idx not in used_indices and phrase not in topics:
                topics.append(phrase)
                topics_with_scores.append((phrase, score))
            if len(topics) >= num_topics:
                break
    
    # If still not enough, fall back to classic method with different parameters
    if len(topics) < num_topics:
        # Try with different n-gram range
        alt_topics_with_scores = []
        alt_ngram = (1, 2) if ngram_range != (1, 2) else (2, 3)
        
        with yaspin(text="", color="cyan") as spinner:
            alt_keyphrases = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=alt_ngram,
                stop_words='english',
                top_n=top_n_candidates
            )
            spinner.ok("✔")
        
        for phrase, score in alt_keyphrases:
            if phrase not in [t for t, _ in topics_with_scores] and not is_layout_topic(phrase) and not is_newsletter_metadata(phrase):
                alt_topics_with_scores.append((phrase, score))
        
        # Add these alternative topics
        for topic, score in alt_topics_with_scores:
            topics.append(topic)
            topics_with_scores.append((topic, score))
            if len(topics) >= num_topics:
                break
    
    # If still not enough, try classic method
    if len(topics) < num_topics:
        classic_results = extract_key_topics(newsletters, num_topics=num_topics, return_scores=True)
        for topic, score in classic_results:
            if topic not in topics:
                topics.append(topic)
                topics_with_scores.append((topic, score))
            if len(topics) >= num_topics:
                break
    
    # Always tell the user how many topics were actually found
    topic_count = len(topics)
    print(f"Found {topic_count} relevant topics")
    
    # Sort all topics by score in descending order (higher is better)
    topics_with_scores.sort(key=lambda x: x[1], reverse=True)
    topics = [t for t, _ in topics_with_scores]
    
    if return_scores:
        return topics_with_scores
    else:
        return topics

def extract_key_topics_direct_llm(newsletters, num_topics=10, provider='openai'):
    """Extract topics directly using an LLM without NLP preprocessing."""
    from llm import analyze_newsletters_unified
    
    # Get analysis and topic titles
    _, topic_titles = analyze_newsletters_unified(newsletters, num_topics, provider)
    
    # Return just the topic titles for compatibility with existing code
    return topic_titles

def find_representative_sentences(topic, newsletters, max_sentences=3):
    """Find the most representative sentences for a given topic."""
    topic_terms = set(topic.lower().split())
    if '(' in topic:
        # Add related terms if available in the format 'main_topic (related1, related2)'
        related = re.findall(r'\((.*?)\)', topic)
        if related:
            for term in related[0].split(','):
                topic_terms.add(term.strip().lower())
    
    sentences = []
    for nl in newsletters:
        cleaned_body = clean_body(nl['body'], nl.get('body_format'))
        for sentence in sent_tokenize(cleaned_body):
            sent_lower = sentence.lower()
            relevance_score = sum(1 for term in topic_terms if term in sent_lower)
            if relevance_score > 0:
                sentences.append((sentence, relevance_score))
    
    # Sort by relevance score and return top sentences
    sentences.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in sentences[:max_sentences]] 