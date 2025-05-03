import re
from nltk.tokenize import sent_tokenize
from nlp import clean_body, find_representative_sentences

def present_and_select_topics(topics_with_scores, newsletters, max_topics_to_display=10):
    """
    Present extracted topics to the user and let them select which ones to include.
    
    Args:
        topics_with_scores: List of (topic, score) tuples ordered by importance
        newsletters: List of newsletter objects (for context)
        max_topics_to_display: Maximum number of topics to display to the user
    
    Returns:
        List of selected topics for analysis
    """
    print("\n" + "="*60)
    print("TOPIC SELECTION")
    print("="*60)
    
    # Limit the number of topics to display
    topics_to_display = topics_with_scores[:max_topics_to_display]
    
    print(f"\nThe following {len(topics_to_display)} topics were identified in your newsletters (ranked by importance):")
    print("(Higher scores indicate more relevant topics)\n")
    
    # Display topics with scores and example context
    for i, (topic, score) in enumerate(topics_to_display, 1):
        # Find a relevant sentence for context
        context = find_better_context(topic, newsletters)
        # Clean up the context for display
        context = clean_context_for_display(context)
        print(f"{i}. {topic} (score: {score:.2f})")
        print(f"   Example: \"{context}\"")
    
    # By default, select the top 5 topics (or all if less than 5)
    default_count = min(5, len(topics_to_display))
    selected_indices = list(range(1, default_count + 1))
    
    while True:
        print("\nCurrently selected topics:")
        for idx in selected_indices:
            topic, score = topics_to_display[idx-1]
            print(f"  {idx}. {topic} (score: {score:.2f})")
        
        print(f"\n({len(selected_indices)} topics selected)")
        print("\nCommands:")
        print("  add N       - Add topic number N")
        print("  remove N    - Remove topic number N")
        print("  done        - Proceed with current selection")
        
        choice = input("\nEnter command: ").strip().lower()
        
        if choice == "done":
            break
        elif choice.startswith("add "):
            try:
                idx = int(choice.split()[1])
                if 1 <= idx <= len(topics_to_display) and idx not in selected_indices:
                    selected_indices.append(idx)
                    selected_indices.sort()
                else:
                    print("Topic already selected or invalid number.")
            except (ValueError, IndexError):
                print("Invalid index.")
        elif choice.startswith("remove "):
            try:
                idx = int(choice.split()[1])
                if idx in selected_indices:
                    selected_indices.remove(idx)
                else:
                    print("Topic not currently selected.")
            except (ValueError, IndexError):
                print("Invalid index.")
        else:
            print("Unknown command. Use 'add N', 'remove N', or 'done'.")
    
    # Return only the selected topics
    return [topics_to_display[i-1][0] for i in selected_indices]

def clean_context_for_display(text):
    """Clean up a context sentence for display."""
    if not text:
        return "No clear example found"
        
    # Remove HTML tags and entities
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-z]+;', ' ', text)
    
    # Replace escaped HTML and markdown
    text = re.sub(r'\\<', '<', text)
    text = re.sub(r'\\>', '>', text)
    text = re.sub(r'\\\*', '*', text)
    text = re.sub(r'\\`', '`', text)
    text = re.sub(r'\\#', '#', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive punctuation
    text = re.sub(r'[!?.](\s*[!?.])+ *', '. ', text)
    
    # Truncate if too long
    if len(text) > 120:
        text = text[:117] + "..."
        
    return text.strip()

def find_topic_context(topic, newsletters):
    """Find a representative sentence containing the topic for context."""
    # Extract topic terms, including any that might be in parentheses
    topic_terms = topic.lower().split()
    if '(' in topic and ')' in topic:
        related_terms = re.findall(r'\((.*?)\)', topic)
        if related_terms:
            for term in related_terms[0].split(','):
                topic_terms.extend(term.strip().lower().split())
    
    # Clean topic terms to be more flexible in matching
    topic_terms = [term.strip() for term in topic_terms if len(term.strip()) > 2]
    
    # Look for sentences containing the topic terms
    for nl in newsletters:
        cleaned_body = clean_body(nl['body'], nl.get('body_format'))
        
        # Clean extra whitespace
        cleaned_body = re.sub(r'\s+', ' ', cleaned_body)
        
        sentences = sent_tokenize(cleaned_body)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sent_lower = sentence.lower()
            if any(term in sent_lower for term in topic_terms):
                # Filter out HTML artifacts that sometimes remain
                if '|' in sentence and sentence.count('|') > 2:
                    continue
                    
                # Filter out very short sentences
                if len(sentence) < 20:
                    continue
                
                # Filter out sentences with too many special characters
                special_char_count = sum(1 for c in sentence if not c.isalnum() and not c.isspace())
                if special_char_count / len(sentence) > 0.3:  # more than 30% special characters
                    continue
                    
                # Filter out likely job postings or newsletter metadata
                if any(word in sent_lower for word in ['hiring', 'job', 'apply', 'position', 'subscribe', 'unsubscribe', 'email']):
                    continue
                
                # Filter out statements obviously not about the topic
                if sent_lower.startswith('log in') or sent_lower.startswith('sign in'):
                    continue
                
                return sentence
    
    # Fallback if no good example found
    return "No clear example found"

def find_better_context(topic, newsletters):
    """Find better context for a topic by trying multiple strategies."""
    # First try to find a sentence with clear topic relevance
    sentences = find_representative_sentences(topic, newsletters, max_sentences=3)
    
    if sentences:
        # Filter out poor quality sentences
        good_sentences = [s for s in sentences if is_good_context_sentence(s)]
        if good_sentences:
            return good_sentences[0]
    
    # Fall back to the regular method
    return find_topic_context(topic, newsletters)

def is_good_context_sentence(sentence):
    """Determine if a sentence is good for context display."""
    # Clean the sentence
    sentence = sentence.strip()
    
    # Filter out HTML artifacts
    if '|' in sentence and sentence.count('|') > 2:
        return False
        
    # Filter out markdown artifacts
    if sentence.startswith('*') and sentence.endswith('*'):
        return False
        
    # Filter out very short sentences
    if len(sentence) < 20:
        return False
        
    # Filter out sentences with too many special characters
    special_char_count = sum(1 for c in sentence if not c.isalnum() and not c.isspace())
    if special_char_count / len(sentence) > 0.3:  # more than 30% special characters
        return False
    
    # Filter out likely job postings or newsletter metadata
    lower_sent = sentence.lower()
    if any(word in lower_sent for word in ['hiring', 'job', 'apply', 'position', 'subscribe', 'unsubscribe', 'email']):
        return False
    
    # Filter out login/account statements
    if (lower_sent.startswith('log in') or 
        lower_sent.startswith('sign in') or 
        'your account' in lower_sent or 
        'bank account' in lower_sent or
        'payment' in lower_sent or
        'statement' in lower_sent or
        'balance' in lower_sent or
        'bill' in lower_sent or
        'invoice' in lower_sent or
        'directpay' in lower_sent or
        'debit' in lower_sent):
        return False
    
    # Filter out month-specific content that's likely billing/account related
    months = ['january', 'february', 'march', 'april', 'may', 'june', 
              'july', 'august', 'september', 'october', 'november', 'december']
    if any(month in lower_sent for month in months) and any(word in lower_sent for word in 
                                                           ['account', 'payment', 'statement', 'bill']):
        return False
    
    return True 