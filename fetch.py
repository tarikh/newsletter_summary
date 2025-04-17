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
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    body = re.sub('<[^<]+?>', ' ', html)
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        newsletters.append({
            'subject': subject,
            'date': date,
            'sender': sender,
            'body': body
        })
    return newsletters 