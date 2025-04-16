from dotenv import load_dotenv
load_dotenv('.env.local')

import argparse
from auth import authenticate_gmail
from fetch import get_ai_newsletters
from nlp import extract_key_topics
from llm import analyze_with_llm
from report import generate_report

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
    parser.set_defaults(prioritize_recent=True, breaking_news_section=True)
    args = parser.parse_args()
    try:
        print("Authenticating with Gmail...")
        service = authenticate_gmail()
        print(f"Retrieving AI newsletters from the past {args.days} days...")
        newsletters = get_ai_newsletters(service, days=args.days)
        print(f"Found {len(newsletters)} newsletters.")
        if not newsletters:
            print("No newsletters found. Check your Gmail labels or date range.")
            return
        print("Extracting key topics...")
        if args.prioritize_recent:
            print("  - Giving priority to recent content")
            topics = extract_key_topics(newsletters)
        else:
            all_text = " ".join([nl['body'] for nl in newsletters])
            subjects_text = " ".join([nl['subject'] for nl in newsletters])
            weighted_subjects = " ".join([subjects_text] * 5)
            combined_text = all_text + " " + weighted_subjects
            from nltk.corpus import stopwords
            from nltk.tokenize import word_tokenize
            stop_words = set(stopwords.words('english'))
            additional_stops = {'ai', 'artificial', 'intelligence', 'ml', 'model', 'models', 'news', 
                             'newsletter', 'week', 'weekly', 'new'}
            stop_words.update(additional_stops)
            words = word_tokenize(combined_text.lower())
            filtered_words = [word for word in words if word.isalpha() and word not in stop_words and len(word) > 3]
            from collections import Counter
            word_freq = Counter(filtered_words)
            topics = [topic for topic, _ in word_freq.most_common(5)]
        print(f"Identified {len(topics)} key topics: {', '.join(topics)}")
        print("Analyzing newsletter content...")
        llm_analysis = analyze_with_llm(newsletters, topics)
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
        with open(report_filename, 'w') as f:
            f.write(report)
        print(f"Report saved to {report_filename}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 