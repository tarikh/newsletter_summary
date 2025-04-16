import datetime
import base64
import re

def get_ai_newsletters(service, days=7):
    """Get emails tagged with 'ai newsletter' from the past week."""
    date_from = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y/%m/%d')
    query = f"label:ai-newsletter after:{date_from}"
    result = service.users().messages().list(userId='me', q=query).execute()
    messages = result.get('messages', [])
    newsletters = []
    for message in messages:
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