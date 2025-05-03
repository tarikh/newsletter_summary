import pytest
from unittest.mock import patch, MagicMock
from interactive import (
    present_and_select_topics, 
    find_topic_context, 
    find_better_context, 
    is_good_context_sentence,
    clean_context_for_display
)

def test_find_topic_context():
    """Test the function to find context sentences for topics."""
    newsletters = [
        {
            'body': '  OpenAI   released a new model today.  It has better performance.',
            'body_format': 'plain',
            'subject': 'AI News'
        }
    ]
    
    context = find_topic_context('new model', newsletters)
    assert 'OpenAI released a new model today' in context
    # Check that extra whitespace was removed
    assert '  OpenAI   released' not in context

def test_clean_context_for_display():
    """Test the function to clean context for display."""
    # Test HTML tag removal
    assert clean_context_for_display("<p>This is a test</p>") == "This is a test"
    
    # Test entity replacement
    assert "space" in clean_context_for_display("This has a&nbsp;space")
    
    # Test escaped character handling - the function doesn't actually convert to HTML tags
    assert clean_context_for_display("\\<div\\>Test\\</div\\>") != "\\<div\\>Test\\</div\\>"
    
    # Test truncation
    long_text = "This is a very long sentence that should be truncated because it exceeds the maximum length limit that we have set for our context display in the interactive mode."
    truncated = clean_context_for_display(long_text)
    assert len(truncated) <= 120
    assert truncated.endswith("...")

def test_is_good_context_sentence():
    """Test the function to determine if a sentence is good for context display."""
    # Good sentence
    assert is_good_context_sentence("OpenAI released a new model today with improved performance.")
    
    # Too short
    assert not is_good_context_sentence("Hello world.")
    
    # Too many special characters
    assert not is_good_context_sentence("|---|---|---|---|")
    
    # Markdown formatting
    assert not is_good_context_sentence("*This is highlighted text*")
    
    # Job posting
    assert not is_good_context_sentence("We are hiring a machine learning engineer for our team.")
    
    # Login statement
    assert not is_good_context_sentence("Log in to your account to view your settings.")

def test_find_better_context():
    """Test the improved context finding."""
    newsletters = [
        {
            'body': 'OpenAI released a new model today. It has better performance. | | | Many columns of data | | |',
            'body_format': 'plain',
            'subject': 'AI News'
        }
    ]
    
    # Mock find_representative_sentences to return a controlled result
    with patch('nlp.find_representative_sentences', return_value=["OpenAI released a new model today."]):
        context = find_better_context('new model', newsletters)
        assert 'OpenAI released a new model today' in context
        assert '| | |' not in context

def test_topic_selection():
    """Test the interactive topic selection with mocked input."""
    topics_with_scores = [
        ("AI research", 0.9),
        ("Machine learning tools", 0.8),
        ("Tech regulations", 0.7),
        ("Industry trends", 0.6),
        ("New product launches", 0.5),
        ("Computer vision", 0.4),
        ("Natural language processing", 0.3),
        ("Robotics", 0.2),
        ("Cloud computing", 0.1),
        ("Edge AI", 0.05)
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
            # Also patch the find_better_context function to avoid nltk calls during testing
            with patch('interactive.find_better_context', return_value="Test context"):
                selected_topics = present_and_select_topics(topics_with_scores, newsletters)
    
    assert selected_topics == ["AI research", "Tech regulations"]
    assert "Machine learning tools" not in selected_topics
    assert "Industry trends" not in selected_topics
    assert "New product launches" not in selected_topics

def test_max_topics_to_display():
    """Test that the max_topics_to_display parameter works correctly."""
    # Create more than max_topics_to_display topics
    topics_with_scores = [
        (f"Topic {i}", 1.0 - (i * 0.1)) for i in range(1, 15)
    ]
    
    newsletters = [{
        'body': 'Sample body text for testing.',
        'body_format': 'plain',
        'subject': 'Test'
    }]
    
    # Set max_topics_to_display to 7 (less than the total 14 topics)
    max_display = 7
    
    mock_inputs = ["done"]  # Just accept default selection
    
    with patch('builtins.input', side_effect=mock_inputs):
        with patch('builtins.print'):  # Suppress print output
            # Also patch the find_better_context function to avoid nltk calls during testing
            with patch('interactive.find_better_context', return_value="Test context"):
                selected_topics = present_and_select_topics(
                    topics_with_scores, 
                    newsletters, 
                    max_topics_to_display=max_display
                )
    
    # Default selection should be the top 5 (or all if less than 5) topics
    assert len(selected_topics) == 5
    # The displayed topics should be limited to max_display
    assert all(topic in [t[0] for t in topics_with_scores[:max_display]] for topic in selected_topics) 