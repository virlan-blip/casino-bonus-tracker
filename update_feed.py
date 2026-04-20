import os
import json
import time
import re
import feedparser
from google import genai
from datetime import datetime

# Setup Gemini API using the modern SDK
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# The Global Promo Query + Crypto Casino News Feeds
RSS_FEEDS = [
    # Highly targeted Google News query for global & US/UK bonuses
    "https://news.google.com/rss/search?q=(%22casino+bonus%22+OR+%22bonus+code%22+OR+%22no+deposit%22+OR+%22crypto+casino%22+OR+%22free+spins%22)+when:1d&hl=en-US&gl=US&ceid=US:en",
    # Crypto casino news sources
    "https://cointelegraph.com/rss/tag/casino",
    "https://www.newsbtc.com/feed/"
]

def fetch_and_process():
    if os.path.exists('live_data.json'):
        with open('live_data.json', 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    existing_links = {item['link'] for item in data}
    new_items = []

    # Fetch the raw feeds
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        
        articles_added = 0
        for entry in feed.entries:
            if articles_added >= 3:
                break
                
            # --- STRICT PROMO FILTER ---
            text_to_check = entry.title + " " + entry.get('summary', '')
            
            # We only want articles that actually mention bonuses or promos
            promo_keywords = r'\b(bonus|promo|code|deposit|spins|welcome offer|crypto casino|betmgm|bet365)\b'
            if not re.search(promo_keywords, text_to_check, re.IGNORECASE):
                continue
            # ---------------------------

            if entry.link not in existing_links:
                source_name = feed.feed.get('title', 'Industry Source')
                if "news.google.com" in url:
                    if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                        source_name = entry.source.title
                    elif " - " in entry.title:
                        source_name = entry.title.rsplit(" - ", 1)[-1]

                new_items.append({
                    'link': entry.link,
                    'raw_title': entry.title,
                    'raw_summary': entry.get('summary', ''),
                    'source': source_name,
                    'timestamp': datetime.utcnow().strftime('%I:%M %p UTC')
                })
                articles_added += 1

    if not new_items:
        print("No new bonus offers found. Exiting.")
        return

    # Process new items through Gemini
    for item in new_items:
        prompt = f"""
        You are an expert Casino Affiliate Manager and Copywriter. 
        Review this raw RSS feed item about a casino bonus, crypto casino, or promotional code:
        Title: {item['raw_title']}
        Summary: {item['raw_summary']}

        Your task is to extract the value of the offer and write a compelling, 3-paragraph promotional update.
        
        Follow this strict affiliate structure:
        - Paragraph 1 (The Hook & Offer): State the casino brand and the exact value of the bonus (e.g., "$1000 Deposit Match", "50 Free Spins", "No Deposit Crypto Bonus"). Make it exciting.
        - Paragraph 2 (The Details & Codes): Highlight any specific Promo Codes needed (e.g., "Use code BETMGM..."), the target audience (US, UK, Global), or key wagering requirements if mentioned. 
        - Paragraph 3 (Call to Action): A brief closing sentence encouraging the reader to claim the offer before it expires.

        CRITICAL INSTRUCTION: You must format the output using HTML paragraph tags inside the JSON content string to create visual spacing. Example: "<p>First paragraph text.</p><p>Second paragraph text.</p>"
        
        Determine if the content is an 'Offer' or 'News'. (Use 'Offer' if it is a specific bonus).
        
        Return ONLY a valid JSON object in exactly this format, nothing else:
        {{"type": "Offer" or "News", "headline": "A high-converting, click-worthy headline including the bonus amount", "content": "<p>First paragraph here.</p><p>Second paragraph here.</p><p>Third paragraph here.</p>"}}
        """
        
        try:
            print(f"Asking Gemini to analyze offer: {item['raw_title']}")
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            res_text = response.text.replace('```json', '').replace('```', '').strip()
            ai_data = json.loads(res_text)
            
            item['type'] = ai_data.get('type', 'Offer')
            item['headline'] = ai_data.get('headline', item['raw_title'])
            item['content'] = ai_data.get('content', '<p>Click the link to view the full bonus details and terms.</p>')
            
            data.insert(0, item)
            time.sleep(30)
            
        except Exception as e:
            print(f"Error processing {item['link']} with Gemini: {e}")
            
    data = data[:15]
    
    with open('live_data.json', 'w') as f:
        json.dump(data, f, indent=2)
        print("Successfully updated live_data.json")

if __name__ == "__main__":
    fetch_and_process()
