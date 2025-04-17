import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from tqdm import tqdm
from yaspin import yaspin

def extract_key_topics(newsletters, num_topics=5):
    """Extract key topics from newsletters using more advanced NLP techniques."""
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
        all_text += " ".join([nl['body']] * content_weight) + " "
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
    for cluster in topic_clusters:
        if len(final_topics) >= num_topics:
            break
        main_topic, _ = max(cluster, key=lambda x: x[1])
        related_terms = [t for t, _ in sorted(cluster, key=lambda x: x[1], reverse=True)[1:4] 
                        if t != main_topic]
        if related_terms:
            final_topics.append(f"{main_topic} ({', '.join(related_terms)})")
        else:
            final_topics.append(main_topic)
    if len(final_topics) < num_topics:
        remaining_topics = [t for t, _ in candidate_topics if t not in ' '.join(final_topics)]
        final_topics.extend(remaining_topics[:num_topics - len(final_topics)])
    return final_topics[:num_topics]

def extract_key_topics_keybert(newsletters, num_topics=5, ngram_range=(1,3), top_n_candidates=30):
    """Extract key topics using KeyBERT and semantic clustering with dynamic adjustment and fallback."""
    text = " ".join(nl['body'] + " " + nl['subject'] for nl in newsletters)
    kw_model = KeyBERT(model='all-MiniLM-L6-v2')
    msg = "Extracting keyphrases with KeyBERT (this may take a moment)..."
    print(msg, flush=True)
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
        return []
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = embedder.encode(keyphrases)
    n_clusters = min(num_topics, len(keyphrases))
    if n_clusters < 2:
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
    used_indices = set()
    for phrases in cluster_to_phrases.values():
        phrases.sort(key=lambda x: x[1], reverse=True)
        top_phrase = phrases[0][0]
        topics.append(top_phrase)
        # Mark all indices in this cluster as used
        for phrase, _ in phrases:
            if phrase in keyphrases:
                used_indices.add(keyphrases.index(phrase))
    # If we have fewer than num_topics, fill in with next best unclustered keyphrases
    if len(topics) < num_topics:
        for idx, (phrase, _) in enumerate(keyphrases_with_scores):
            if idx not in used_indices and phrase not in topics:
                topics.append(phrase)
            if len(topics) >= num_topics:
                break
    # If still not enough, fall back to classic method
    if len(topics) < num_topics:
        classic_topics = extract_key_topics(newsletters, num_topics=num_topics)
        for topic in classic_topics:
            if topic not in topics:
                topics.append(topic)
            if len(topics) >= num_topics:
                break
    return topics[:num_topics] 