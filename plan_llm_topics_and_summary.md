# Implementation Plan: Streamlined Newsletter Summarization

This plan will:
1. Remove interactive mode completely
2. Combine topic extraction and summarization into a single step
3. Output up to 10 topics ordered by importance in both modes

## 1. Code Removals

1. **Remove Interactive Mode Components**:
   - Delete the `interactive.py` file
   - Remove all references to `--interactive` and `-i` flags in `main.py`
   - Remove any code blocks that handle interactive mode logic

## 2. Create Unified LLM Analysis Module

Create a new function in `llm.py` that handles end-to-end processing:

```python
# Add to llm.py

def analyze_newsletters_unified(newsletters, num_topics=10, provider='openai'):
    """
    Process newsletters in a single step - identifying topics and generating summaries.
    
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
    
    # Call the appropriate LLM
    analysis_text = ""
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
    import re
    topic_titles = re.findall(r'###\s*\d+\.\s*(.*?)\n', analysis_text)
    
    return analysis_text, topic_titles
```

## 3. Update Original NLP-Based Approach

Modify the existing `extract_key_topics_keybert` and `extract_key_topics` functions in `nlp.py` to support up to 10 topics:

```python
# In nlp.py, modify the relevant functions:

def extract_key_topics_keybert(newsletters, num_topics=10, ngram_range=(1,3), top_n_candidates=50, return_scores=False):
    """Extract key topics using KeyBERT and semantic clustering with dynamic adjustment and fallback.
    Now supports up to 10 topics by default."""
    
    # The rest of the code remains the same, just the default num_topics changes to 10
    # and increase top_n_candidates to 50 to ensure enough candidates for 10 topics
    
    # ...existing implementation...
    
    return topics_with_scores if return_scores else topics

def extract_key_topics(newsletters, num_topics=10, return_scores=False):
    """Extract key topics from newsletters using more advanced NLP techniques.
    Now supports up to 10 topics by default."""
    
    # The rest of the code remains the same, just the default num_topics changes to 10
    
    # ...existing implementation...
    
    return filtered_topics_with_scores[:num_topics] if return_scores else filtered_topics[:num_topics]
```

## 4. Create New LLM-Direct Approach

Add a new function in `nlp.py` that delegates directly to the LLM for topic extraction:

```python
# Add to nlp.py

def extract_key_topics_direct_llm(newsletters, num_topics=10, provider='openai'):
    """Extract topics directly using an LLM without NLP preprocessing."""
    from llm import analyze_newsletters_unified
    
    # Get analysis and topic titles
    _, topic_titles = analyze_newsletters_unified(newsletters, num_topics, provider)
    
    # Return just the topic titles for compatibility with existing code
    return topic_titles
```

## 5. Update `main.py`

Modify `main.py` to incorporate these changes:

```python
# main.py modifications

# Remove interactive-related arguments
# Remove: parser.add_argument('--interactive', '-i', action='store_true', ...)

# Add argument for number of topics
parser.add_argument('--num-topics', type=int, default=10,
                    help='Number of topics to extract and summarize (default: 10)')

# Add argument for direct LLM approach
parser.add_argument('--direct-llm', action='store_true',
                    help='Use direct-to-LLM approach for both topic extraction and summarization')

# Then in the main function, replace the topic extraction and LLM analysis code:

if args.direct_llm:
    # Direct LLM approach - combined topic extraction and summarization
    print(f"Using direct LLM approach with {args.llm_provider} to extract and summarize {args.num_topics} topics...")
    from llm import analyze_newsletters_unified
    
    llm_analysis, topics = analyze_newsletters_unified(
        newsletters, 
        num_topics=args.num_topics,
        provider=args.llm_provider
    )
    
    print(f"Identified and analyzed {len(topics)} topics")
    
else:
    # Original approach with separate NLP and LLM steps
    print("Extracting key topics...")
    if args.nlp_method == 'keybert':
        print(f"  - Using KeyBERT + semantic clustering to identify {args.num_topics} topics")
        topics = extract_key_topics_keybert(newsletters, num_topics=args.num_topics)
    else:
        print(f"  - Using classic n-gram frequency method to identify {args.num_topics} topics")
        topics = extract_key_topics(newsletters, num_topics=args.num_topics)
    
    # Limit to num_topics
    topics = topics[:args.num_topics]
    
    if not topics:
        print("Error: No topics could be extracted. Please try a different date range or method.")
        return
    
    print(f"Using topics: {', '.join(topics)}")
    print("Analyzing newsletter content...")
    llm_analysis = analyze_with_llm(newsletters, topics, provider=args.llm_provider)

# The rest of the code remains the same for report generation, etc.
```

## 6. Update Report Generation

Ensure the report generation works with both approaches:

```python
# Update in generate_report function in report.py to mention 10 topics

def generate_report(newsletters, topics, llm_analysis, days):
    # Existing code...
    
    # Update the title to reflect up to 10 topics
    report = f"""
# AI NEWSLETTER SUMMARY
{date_range}

## TOP AI DEVELOPMENTS THIS WEEK

{llm_analysis}
"""
    # Rest of the function remains the same...
```

## 7. Implementation Steps

1. **First Phase: Code Cleanup**
   - Remove `interactive.py`
   - Remove all interactive mode references in `main.py`
   - Update argument parser to remove interactive flags and add new flags

2. **Second Phase: Core Functionality Updates**
   - Add the unified analysis function to `llm.py`
   - Update NLP functions to support 10 topics
   - Add direct-LLM approach to `nlp.py`

3. **Third Phase: Logic Implementation**
   - Update the main function in `main.py` to implement both approaches
   - Add appropriate logging and error handling

4. **Fourth Phase: Report Generation**
   - Update report generation to handle the new approach and topic count

5. **Testing**
   - Test original NLP+LLM approach with increased topic count
   - Test direct-LLM approach
   - Compare output quality and performance

## 8. Example Usage

```bash
# Use original approach with KeyBERT and 10 topics
python main.py --nlp-method keybert --num-topics 10 --llm-provider openai

# Use direct-to-LLM approach with 8 topics
python main.py --direct-llm --num-topics 8 --llm-provider claude
```

## 9. Benefits of This Implementation

1. **Simplicity**: Removes interactive complexity while maintaining core functionality
2. **Flexibility**: Offers both the original approach and a streamlined direct-to-LLM option
3. **Expanded Coverage**: Provides up to 10 topics for more comprehensive summaries
4. **Efficiency**: Direct-LLM approach reduces processing steps and API calls
5. **Consistency**: Maintains backward compatibility with existing report generation

This implementation preserves the strengths of your original codebase while adding a simplified and potentially more effective approach. The user can choose between approaches based on their specific needs and preferences.