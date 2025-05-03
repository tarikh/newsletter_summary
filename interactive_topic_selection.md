# Implementation Plan: Interactive Topic Selection Feature

## 1. Command-Line Option

Add a new CLI option to enable interactive mode:

```python
# In main.py - argument parser section
parser.add_argument('--interactive', '-i', action='store_true',
                    help='Enable interactive mode to review and select topics before summarization')
```

## 2. Topic Extraction Enhancement

Modify the topic extraction functions to return both topics and their importance scores:

```python
# In nlp.py - modify KeyBERT function
def extract_key_topics_keybert(newsletters, num_topics=5, ngram_range=(1,3), top_n_candidates=30, return_scores=False):
    """Extract key topics using KeyBERT and semantic clustering with dynamic adjustment and fallback."""
    text = " ".join(clean_body(nl['body']) + " " + nl['subject'] for nl in newsletters)
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
    
    # Rest of the function remains the same...
    
    # At the end, return the topics with their scores if requested
    if return_scores:
        # Create a list of (topic, score) tuples
        return [(topics[i], keyphrases_with_scores[i][1]) for i in range(len(topics))]
    else:
        return topics[:num_topics]

# Similarly modify the classic method
def extract_key_topics(newsletters, num_topics=5, return_scores=False):
    # Existing implementation...
    
    # At the end, return with scores if requested
    if return_scores:
        return [(topic, combined_freq[topic]) for topic, _ in candidate_topics[:num_topics]]
    else:
        return [topic for topic, _ in candidate_topics[:num_topics]]
```

## 3. Interactive Selection Module

Create a new module `interactive.py`:

```python
# interactive.py
import re
from nltk.tokenize import sent_tokenize
from nlp import clean_body

def present_and_select_topics(topics_with_scores, newsletters):
    """
    Present extracted topics to the user and let them select which ones to include.
    
    Args:
        topics_with_scores: List of (topic, score) tuples ordered by importance
        newsletters: List of newsletter objects (for context)
    
    Returns:
        List of selected topics for analysis
    """
    print("\n" + "="*60)
    print("TOPIC SELECTION")
    print("="*60)
    print("\nThe following topics were identified in your newsletters (ranked by importance):\n")
    
    # Display topics with scores and example context
    for i, (topic, score) in enumerate(topics_with_scores, 1):
        # Find a relevant sentence for context
        context = find_topic_context(topic, newsletters)
        print(f"{i}. {topic} (score: {score:.2f})")
        print(f"   Example: \"{context}\"")
    
    # By default, select the top 5 topics (or all if less than 5)
    default_count = min(5, len(topics_with_scores))
    selected_indices = list(range(1, default_count + 1))
    
    while True:
        print("\nCurrently selected topics:", ", ".join([topics_with_scores[i-1][0] for i in selected_indices]))
        print(f"({len(selected_indices)} topics selected)")
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
                if 1 <= idx <= len(topics_with_scores) and idx not in selected_indices:
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
    return [topics_with_scores[i-1][0] for i in selected_indices]

def find_topic_context(topic, newsletters):
    """Find a representative sentence containing the topic for context."""
    # Extract topic terms, including any that might be in parentheses
    topic_terms = topic.lower().split()
    if '(' in topic and ')' in topic:
        related_terms = re.findall(r'\((.*?)\)', topic)
        if related_terms:
            for term in related_terms[0].split(','):
                topic_terms.extend(term.strip().lower().split())
    
    # Look for sentences containing the topic terms
    for nl in newsletters:
        cleaned_body = clean_body(nl['body'], nl.get('body_format'))
        sentences = sent_tokenize(cleaned_body)
        for sentence in sentences:
            if any(term in sentence.lower() for term in topic_terms):
                # Truncate if too long
                if len(sentence) > 100:
                    return sentence[:97] + "..."
                return sentence
    
    # Fallback if no good example found
    return "No clear example found"
```

## 4. Main Flow Integration

Modify the main function in `main.py`:

```python
# In main.py - add import
from interactive import present_and_select_topics

# In main.py - inside the main function, after topic extraction
if args.nlp_method == 'keybert':
    print("  - Using KeyBERT + semantic clustering")
    if args.interactive:
        topics_with_scores = extract_key_topics_keybert(newsletters, return_scores=True)
        topics = present_and_select_topics(topics_with_scores, newsletters)
    else:
        topics = extract_key_topics_keybert(newsletters)
else:
    print("  - Using classic n-gram frequency method")
    if args.interactive:
        topics_with_scores = extract_key_topics(newsletters, return_scores=True)
        topics = present_and_select_topics(topics_with_scores, newsletters)
    else:
        topics = extract_key_topics(newsletters)

print(f"Using topics: {', '.join(topics)}")
```

## 5. Helper Functions for Finding Better Topic Context

Add this to the NLP module:

```python
# In nlp.py
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
```

## 6. Testing

Create a test file for the interactive module:

```python
# test_interactive.py
import pytest
from unittest.mock import patch
from interactive import present_and_select_topics, find_topic_context

def test_find_topic_context():
    """Test the function to find context sentences for topics."""
    newsletters = [
        {
            'body': 'OpenAI released a new model today. It has better performance.',
            'body_format': 'plain',
            'subject': 'AI News'
        }
    ]
    
    context = find_topic_context('new model', newsletters)
    assert 'OpenAI released a new model today' in context

def test_topic_selection():
    """Test the interactive topic selection with mocked input."""
    topics_with_scores = [
        ("AI research", 0.9),
        ("Machine learning tools", 0.8),
        ("Tech regulations", 0.7),
        ("Industry trends", 0.6),
        ("New product launches", 0.5)
    ]
    
    newsletters = [{
        'body': 'AI research is advancing rapidly. Machine learning tools are getting better.',
        'body_format': 'plain',
        'subject': 'Tech Update'
    }]
    
    # Mock user selecting the 1st and 3rd topics
    mock_inputs = [
        "remove 2",  # Remove second topic
        "remove 4",  # Remove fourth topic
        "remove 5",  # Remove fifth topic
        "done"       # Finish selection
    ]
    
    with patch('builtins.input', side_effect=mock_inputs):
        with patch('builtins.print'):  # Suppress print output
            selected_topics = present_and_select_topics(topics_with_scores, newsletters)
    
    assert selected_topics == ["AI research", "Tech regulations"]
    assert "Machine learning tools" not in selected_topics
    assert "Industry trends" not in selected_topics
    assert "New product launches" not in selected_topics
```

## 7. Documentation Updates

Update the README.md:

```markdown
### Interactive Topic Selection

You can enable interactive mode to review and select topics before generating the summary:

```bash
python main.py --interactive
```

In interactive mode:
- You'll see all identified topics with their importance scores
- Each topic is shown with an example sentence from the newsletters for context
- The top 5 topics are pre-selected by default
- You can add or remove topics from your selection 
- Only after confirming your selection will the summary be generated

This gives you more control over which topics are covered in your summary and helps you focus on what's most relevant to you.
```

## 8. Implementation Timeline

1. **Day 1**:
   - Add command-line option for interactive mode
   - Modify topic extraction functions to return importance scores
   - Create the interactive module with topic selection UI

2. **Day 2**:
   - Implement context finding functions for better examples
   - Integrate interactive selection into the main flow
   - Write tests for the new functionality

3. **Day 3**:
   - Complete documentation updates
   - Final testing and bug fixes
   - Code review and polish

## 9. Requirements.txt Update

Ensure all necessary dependencies are in `requirements.txt`:

```
# Existing dependencies...

# For interactive features
nltk>=3.6.0
tqdm>=4.61.0
yaspin>=2.1.0
```

This comprehensive plan addresses all aspects of implementing the interactive topic selection feature, enabling users to have more control over their newsletter summaries by selecting which auto-identified topics to include.