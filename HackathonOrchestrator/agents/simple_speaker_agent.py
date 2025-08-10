import argparse
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re

# Google Sheets integration
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


class SimpleSpeakerSourcingAgent:
    def __init__(self):
        self.sheets_service = None
        self.drive_service = None
        self._setup_google_services()
    
    def _setup_google_services(self):
        """Initialize Google Sheets and Drive services."""
        creds = None
        token_path = Path(__file__).parent.parent / "token_sheets.json"
        credentials_path = Path(__file__).parent.parent / "credentials.json"
        
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        
        self.sheets_service = build("sheets", "v4", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)
    
    def search_speakers_web(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search the web for speakers using various sources."""
        speakers = []
        
        print(f"🔍 Searching for speakers with query: '{query}'")
        
        # Try multiple search strategies
        search_strategies = [
            self._search_google_experts,
            self._search_conference_speakers,
            self._search_industry_leaders,
            self._search_academic_experts
        ]
        
        for strategy in search_strategies:
            try:
                results = strategy(query, max_results // len(search_strategies))
                speakers.extend(results)
                print(f"✅ Found {len(results)} speakers from {strategy.__name__}")
                if len(speakers) >= max_results:
                    break
            except Exception as e:
                print(f"⚠️  Error with {strategy.__name__}: {e}")
                continue
        
        # Remove duplicates and limit results
        unique_speakers = []
        seen_names = set()
        for speaker in speakers:
            name = speaker.get("name", "").lower().strip()
            if name and name not in seen_names and len(unique_speakers) < max_results:
                unique_speakers.append(speaker)
                seen_names.add(name)
        
        return unique_speakers
    
    def _search_google_experts(self, query: str, max_results: int) -> List[Dict]:
        """Search Google for industry experts and thought leaders."""
        speakers = []
        try:
            search_queries = [
                f'"{query}" expert speaker',
                f'"{query}" thought leader',
                f'"{query}" industry specialist',
                f'"{query}" keynote speaker'
            ]
            
            for search_query in search_queries:
                if len(speakers) >= max_results:
                    break
                    
                search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract search results
                search_results = soup.find_all("div", class_="g")
                for result in search_results[:5]:
                    if len(speakers) >= max_results:
                        break
                        
                    title_element = result.find("h3")
                    snippet_element = result.find("div", class_="VwiC3b")
                    
                    if title_element:
                        title = title_element.text.strip()
                        snippet = snippet_element.text.strip() if snippet_element else ""
                        
                        # Look for names and titles in the result
                        potential_name = self._extract_name_from_title(title, snippet)
                        if potential_name:
                            speakers.append({
                                "name": potential_name,
                                "title": title[:100],  # Truncate long titles
                                "location": self._extract_location(snippet),
                                "source": "Google Search",
                                "query": query,
                                "snippet": snippet[:200]  # Truncate long snippets
                            })
                
                time.sleep(1)  # Be respectful to Google
                
        except Exception as e:
            print(f"Error in Google expert search: {e}")
        
        return speakers
    
    def _search_conference_speakers(self, query: str, max_results: int) -> List[Dict]:
        """Search for conference speakers and presenters."""
        speakers = []
        try:
            search_queries = [
                f'"{query}" conference speaker',
                f'"{query}" event presenter',
                f'"{query}" summit speaker'
            ]
            
            for search_query in search_queries:
                if len(speakers) >= max_results:
                    break
                    
                search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for conference-related results
                search_results = soup.find_all("div", class_="g")
                for result in search_results[:5]:
                    if len(speakers) >= max_results:
                        break
                        
                    title_element = result.find("h3")
                    if title_element:
                        title = title_element.text.strip()
                        if any(keyword in title.lower() for keyword in ["speaker", "presenter", "conference", "event"]):
                            potential_name = self._extract_name_from_title(title, "")
                            if potential_name:
                                speakers.append({
                                    "name": potential_name,
                                    "title": title[:100],
                                    "location": "Conference/Event",
                                    "source": "Conference Search",
                                    "query": query
                                })
                
                time.sleep(1)
                
        except Exception as e:
            print(f"Error in conference speaker search: {e}")
        
        return speakers
    
    def _search_industry_leaders(self, query: str, max_results: int) -> List[Dict]:
        """Search for industry leaders and executives."""
        speakers = []
        try:
            search_queries = [
                f'"{query}" CEO founder',
                f'"{query}" executive director',
                f'"{query}" industry leader'
            ]
            
            for search_query in search_queries:
                if len(speakers) >= max_results:
                    break
                    
                search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                search_results = soup.find_all("div", class_="g")
                for result in search_results[:5]:
                    if len(speakers) >= max_results:
                        break
                        
                    title_element = result.find("h3")
                    if title_element:
                        title = title_element.text.strip()
                        if any(keyword in title.lower() for keyword in ["ceo", "founder", "executive", "director"]):
                            potential_name = self._extract_name_from_title(title, "")
                            if potential_name:
                                speakers.append({
                                    "name": potential_name,
                                    "title": title[:100],
                                    "location": "Industry",
                                    "source": "Industry Search",
                                    "query": query
                                })
                
                time.sleep(1)
                
        except Exception as e:
            print(f"Error in industry leader search: {e}")
        
        return speakers
    
    def _search_academic_experts(self, query: str, max_results: int) -> List[Dict]:
        """Search for academic experts and researchers."""
        speakers = []
        try:
            search_queries = [
                f'"{query}" professor researcher',
                f'"{query}" academic expert',
                f'"{query}" university faculty'
            ]
            
            for search_query in search_queries:
                if len(speakers) >= max_results:
                    break
                    
                search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                search_results = soup.find_all("div", class_="g")
                for result in search_results[:5]:
                    if len(speakers) >= max_results:
                        break
                        
                    title_element = result.find("h3")
                    if title_element:
                        title = title_element.text.strip()
                        if any(keyword in title.lower() for keyword in ["professor", "researcher", "university", "academic"]):
                            potential_name = self._extract_name_from_title(title, "")
                            if potential_name:
                                speakers.append({
                                    "name": potential_name,
                                    "title": title[:100],
                                    "location": "Academic",
                                    "source": "Academic Search",
                                    "query": query
                                })
                
                time.sleep(1)
                
        except Exception as e:
            print(f"Error in academic expert search: {e}")
        
        return speakers
    
    def _extract_name_from_title(self, title: str, snippet: str) -> Optional[str]:
        """Extract potential names from search result titles and snippets."""
        # Look for patterns like "Name - Title" or "Name: Title"
        name_patterns = [
            r'^([A-Z][a-z]+ [A-Z][a-z]+)',  # First Last
            r'^([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)',  # First Middle Last
            r'([A-Z][a-z]+ [A-Z][a-z]+) -',  # Name - Title
            r'([A-Z][a-z]+ [A-Z][a-z]+):',  # Name: Title
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, title)
            if match:
                name = match.group(1).strip()
                # Basic validation - should be 2-4 words, mostly letters
                if 2 <= len(name.split()) <= 4 and name.replace(' ', '').isalpha():
                    return name
        
        return None
    
    def _extract_location(self, snippet: str) -> str:
        """Extract potential location from snippet."""
        # Look for common location patterns
        location_patterns = [
            r'([A-Z][a-z]+, [A-Z]{2})',  # City, State
            r'([A-Z][a-z]+ [A-Z][a-z]+)',  # City State
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, snippet)
            if match:
                return match.group(1)
        
        return "Unknown"
    
    def create_speakers_spreadsheet(self, speakers: List[Dict], title: str = "Hackathon Speakers") -> str:
        """Create a Google Sheets spreadsheet with speaker information."""
        try:
            print(f"📊 Creating Google Sheets spreadsheet...")
            
            # Create new spreadsheet
            body = {"properties": {"title": title}}
            spreadsheet = self.sheets_service.spreadsheets().create(body=body).execute()
            spreadsheet_id = spreadsheet["spreadsheetId"]
            
            # Prepare data for writing
            headers = ["Name", "Title", "Location", "Source", "Query", "Contact Status", "Notes", "Snippet"]
            data = [headers]
            
            for speaker in speakers:
                row = [
                    speaker.get("name", ""),
                    speaker.get("title", ""),
                    speaker.get("location", ""),
                    speaker.get("source", ""),
                    speaker.get("query", ""),
                    "Not Contacted",  # Default status
                    "",  # Notes column
                    speaker.get("snippet", "")  # Snippet column
                ]
                data.append(row)
            
            # Write data to sheet
            range_name = "Sheet1!A1:H" + str(len(data))
            body = {"values": data}
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
            
            # Format headers
            self._format_headers(spreadsheet_id)
            
            print(f"✅ Spreadsheet created successfully!")
            return spreadsheet_id
            
        except HttpError as e:
            print(f"❌ Error creating spreadsheet: {e}")
            return None
    
    def _format_headers(self, spreadsheet_id: str):
        """Format the header row to make it stand out."""
        try:
            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 0,
                            "endRowIndex": 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
                                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                }
            ]
            
            body = {"requests": requests}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
        except Exception as e:
            print(f"⚠️  Error formatting headers: {e}")
    
    def search_and_create_sheet(self, requirements: str, max_results: int = 20) -> Optional[str]:
        """Main method: search for speakers and create Google Sheets."""
        print(f"🚀 Starting speaker search for: '{requirements}'")
        print(f"📈 Target: {max_results} speakers")
        print("-" * 50)
        
        # Search for speakers
        speakers = self.search_speakers_web(requirements, max_results)
        
        if not speakers:
            print("❌ No speakers found from any source.")
            return None
        
        print(f"\n🎯 Found {len(speakers)} potential speakers!")
        print("-" * 50)
        
        # Show summary of found speakers
        for i, speaker in enumerate(speakers[:5], 1):  # Show first 5
            print(f"{i}. {speaker['name']} - {speaker['title'][:50]}...")
        
        if len(speakers) > 5:
            print(f"... and {len(speakers) - 5} more")
        
        print("-" * 50)
        
        # Create Google Sheets
        spreadsheet_id = self.create_speakers_spreadsheet(speakers, f"Speakers - {requirements}")
        
        if spreadsheet_id:
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            print(f"🔗 Spreadsheet URL: {spreadsheet_url}")
            return spreadsheet_url
        else:
            print("❌ Failed to create spreadsheet")
            return None


def main():
    parser = argparse.ArgumentParser(description="Simple Speaker Sourcing Agent for Hackathon")
    parser.add_argument("--requirements", required=True, help="Requirements for speakers/jury members")
    parser.add_argument("--max-results", type=int, default=20, help="Maximum number of results to find")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode for testing")
    
    args = parser.parse_args()
    
    if args.interactive:
        requirements = input("Enter speaker requirements: ")
        max_results = int(input("Enter max results (default 20): ") or "20")
    else:
        requirements = args.requirements
        max_results = args.max_results
    
    agent = SimpleSpeakerSourcingAgent()
    
    try:
        spreadsheet_url = agent.search_and_create_sheet(requirements, max_results)
        if spreadsheet_url:
            print(f"\n🎉 SUCCESS! Your speakers spreadsheet is ready!")
            print(f"📋 View and manage your speakers here: {spreadsheet_url}")
        else:
            print("❌ Failed to create spreadsheet")
    except KeyboardInterrupt:
        print("\n⚠️  Search interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
