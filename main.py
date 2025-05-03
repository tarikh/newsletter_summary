import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv
load_dotenv('.env.local')

import argparse
from auth import authenticate_gmail
from fetch import get_ai_newsletters
from nlp import extract_key_topics_keybert, extract_key_topics, clean_body, extract_key_topics_direct_llm
from llm import analyze_with_llm, analyze_newsletters_unified
from report import generate_report
import json

def main():
    parser = argparse.ArgumentParser(description='Summarize AI newsletters from Gmail.')
    parser.add_argument('--days', type=int, default=7, 
                        help='Number of days to look back for newsletters (default: 7)')
    parser.add_argument('--prioritize-recent', action='store_true',
                        help='Give higher weight to more recent newsletters (default: enabled)')
    parser.add_argument('--no-prioritize-recent', dest='prioritize_recent', action='store_false',
                        help='Do not give higher weight to more recent newsletters')
    parser.add_argument('--breaking-news-section', action='store_true',
                        help='Add a separate "Just In" section for latest newsletters (default: enabled)')
    parser.add_argument('--no-breaking-news-section', dest='breaking_news_section', action='store_false',
                        help='Do not add a separate "Just In" section')
    parser.add_argument('--nlp-method', choices=['keybert', 'classic'], default='keybert',
                        help='NLP technique for topic extraction: keybert (default) or classic')
    parser.add_argument('--llm-provider', choices=['claude', 'openai'], default='openai',
                        help='LLM provider for summarization: claude (Claude 3.7 Sonnet) or openai (default, GPT-4.1)')
    parser.add_argument('--label', type=str, default='ai-newsletter',
                        help='Gmail label to filter newsletters (default: ai-newsletter)')
    parser.add_argument('--no-label', action='store_true',
                        help='Do not use any Gmail label as a search criteria (overrides --label)')
    parser.add_argument('--from-email', type=str, default=None,
                        help='Only include emails from this sender email address (optional)')
    parser.add_argument('--to-email', type=str, default=None,
                        help='Only include emails sent to this recipient email address (optional)')
    parser.add_argument('--debug-key-topics', action='store_true',
                        help='Debug mode: only extract and display key topics and the cleaned text used for topic extraction')
    parser.add_argument('--num-topics', type=int, default=10,
                        help='Number of topics to extract and summarize (default: 10)')
    parser.add_argument('--direct-llm', action='store_true',
                        help='Use direct-to-LLM approach for both topic extraction and summarization')
    parser.set_defaults(prioritize_recent=True, breaking_news_section=True)
    args = parser.parse_args()
    try:
        print("Authenticating with Gmail...")
        service = authenticate_gmail()
        label_arg = None if args.no_label else args.label
        print(f"Retrieving AI newsletters from the past {args.days} days... (label: {label_arg if label_arg else 'none'})")
        mock_data_env = os.environ.get("NEWSLETTER_SUMMARY_MOCK_DATA")
        if mock_data_env:
            newsletters = json.loads(mock_data_env)
        else:
            newsletters = get_ai_newsletters(
                service,
                days=args.days,
                label=label_arg,
                from_email=args.from_email,
                to_email=args.to_email
            )
        print(f"Found {len(newsletters)} newsletters.")
        if not newsletters:
            print("No newsletters found. Check your Gmail labels or date range.")
            return
        if args.debug_key_topics:
            print("\n--- DEBUG: Cleaned text used for topic extraction ---\n")
            cleaned_text = "\n\n".join([clean_body(nl['body'], nl.get('body_format')) + "\n" + nl['subject'] for nl in newsletters])
            print(cleaned_text)
            print("\n--- DEBUG: Key topics identified ---\n")
            if args.direct_llm:
                topics = extract_key_topics_direct_llm(newsletters, num_topics=args.num_topics, provider=args.llm_provider)
            elif args.nlp_method == 'keybert':
                topics = extract_key_topics_keybert(newsletters, num_topics=args.num_topics)
            else:
                topics = extract_key_topics(newsletters, num_topics=args.num_topics)
            print(f"Identified {len(topics)} key topics: {', '.join(topics)}")
            return
        
        if args.direct_llm:
            # Direct LLM approach - combined topic extraction and summarization
            print(f"Using direct LLM approach with {args.llm_provider} to extract and summarize {args.num_topics} topics...")
            
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
        
        print("Generating report...")
        if not args.breaking_news_section:
            def generate_report_without_breaking(newsletters, topics, llm_analysis, days):
                report, filename = generate_report(newsletters, topics, llm_analysis, days)
                import re
                report = re.sub(r'\n## JUST IN: LATEST DEVELOPMENTS\n\n.*?\n\n## ', '\n\n## ', report, flags=re.DOTALL)
                return report, filename
            report, filename_date_range = generate_report_without_breaking(newsletters, topics, llm_analysis, args.days)
        else:
            report, filename_date_range = generate_report(newsletters, topics, llm_analysis, args.days)
        report_filename = f"ai_newsletter_summary_{filename_date_range}.md"
        output_dir = os.environ.get("NEWSLETTER_SUMMARY_OUTPUT_DIR", "")
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            report_filename = os.path.join(output_dir, report_filename)
        with open(report_filename, 'w') as f:
            f.write(report)
        print(f"Report saved to {report_filename}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 