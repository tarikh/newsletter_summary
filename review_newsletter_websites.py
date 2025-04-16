import json
import os

CACHE_PATH = 'newsletter_websites.json'

def main():
    if not os.path.exists(CACHE_PATH):
        print('No cache file found.')
        return
    with open(CACHE_PATH, 'r') as f:
        cache = json.load(f)
    changed = False
    for name, entry in list(cache.items()):
        url = entry.get('url')
        verified = entry.get('verified', False)
        if verified:
            continue
        print(f"\nNewsletter: {name}")
        print(f"  Cached website: {url}")
        action = input("[a]ccept, [e]dit, [d]elete, [s]kip? (a/e/d/s): ").strip().lower()
        if action == 'a':
            cache[name]['verified'] = True
            changed = True
        elif action == 'e':
            new_url = input("Enter correct website URL: ").strip()
            cache[name]['url'] = new_url
            cache[name]['verified'] = True
            changed = True
        elif action == 'd':
            del cache[name]
            changed = True
        elif action == 's':
            continue
    if changed:
        with open(CACHE_PATH, 'w') as f:
            json.dump(cache, f, indent=2)
        print("\nCache updated.")
    else:
        print("\nNo changes made.")

if __name__ == "__main__":
    main() 