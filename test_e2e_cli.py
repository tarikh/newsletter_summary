import subprocess
import sys
import os
import tempfile
import pytest
import json

def test_e2e_cli_report_generation():
    # Use a temp output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        env['NEWSLETTER_SUMMARY_OUTPUT_DIR'] = tmpdir
        # Provide mock data as JSON
        mock_newsletters = [
            {
                'subject': 'E2E Test Subject',
                'date': 'Mon, 1 Jan 2024 10:00:00 +0000',
                'sender': 'sender@example.com',
                'body': 'This is a test body for E2E.'
            }
        ]
        env['NEWSLETTER_SUMMARY_MOCK_DATA'] = json.dumps(mock_newsletters)
        # Run the CLI in the project root
        result = subprocess.run([sys.executable, 'main.py', '--days', '1'], capture_output=True, text=True, env=env)
        assert result.returncode == 0
        # Find the output file
        files = os.listdir(tmpdir)
        report_files = [f for f in files if f.startswith('ai_newsletter_summary_') and f.endswith('.md')]
        assert report_files, 'No report file generated.'
        # Check content
        with open(os.path.join(tmpdir, report_files[0]), 'r') as f:
            content = f.read()
        assert 'E2E Test Subject' in content

def test_e2e_cli_report_generation_no_label():
    # Use a temp output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        env['NEWSLETTER_SUMMARY_OUTPUT_DIR'] = tmpdir
        # Provide mock data as JSON
        mock_newsletters = [
            {
                'subject': 'NoLabel E2E Subject',
                'date': 'Mon, 1 Jan 2024 10:00:00 +0000',
                'sender': 'sender@example.com',
                'body': 'This is a test body for no-label E2E.'
            }
        ]
        env['NEWSLETTER_SUMMARY_MOCK_DATA'] = json.dumps(mock_newsletters)
        # Run the CLI with --no-label
        result = subprocess.run([sys.executable, 'main.py', '--days', '1', '--no-label'], capture_output=True, text=True, env=env)
        assert result.returncode == 0
        # Find the output file
        files = os.listdir(tmpdir)
        report_files = [f for f in files if f.startswith('ai_newsletter_summary_') and f.endswith('.md')]
        assert report_files, 'No report file generated.'
        # Check content
        with open(os.path.join(tmpdir, report_files[0]), 'r') as f:
            content = f.read()
        assert 'NoLabel E2E Subject' in content 