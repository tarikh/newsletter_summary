import datetime
import base64
import re
from tqdm import tqdm

def get_ai_newsletters(service, days=7, label='ai-newsletter', from_email=None, to_email=None):
    """Get emails matching label, date, and optional from/to filters."""
    date_from = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y/%m/%d')
    query_parts = [f"after:{date_from}"]
    if label:
        query_parts.insert(0, f"label:{label}")
    if from_email:
        query_parts.append(f"from:{from_email}")
    if to_email:
        query_parts.append(f"to:{to_email}")
    query = ' '.join(query_parts)
    result = service.users().messages().list(userId='me', q=query).execute()
    messages = result.get('messages', [])
    newsletters = []
    for message in tqdm(messages, desc="Fetching newsletters", unit="email"):
        msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        payload = msg['payload']
        headers = payload['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No Date')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown Sender')
        body = ""
        body_format = None
        if 'parts' in payload:
            html_body = None
            text_body = None
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/plain':
                    text_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            if html_body is not None:
                body = html_body
                body_format = 'html'
            elif text_body is not None:
                body = text_body
                body_format = 'plain'
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            body_format = 'plain'
        newsletters.append({
            'subject': subject,
            'date': date,
            'sender': sender,
            'body': body,
            'body_format': body_format
        })
    return newsletters 