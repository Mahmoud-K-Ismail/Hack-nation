#!/usr/bin/env python3
"""
Speaker Finder Service for Hackathon Orchestrator
Integrated service for finding speakers and creating Google Sheets
"""

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

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


class SpeakerFinderService:
    def __init__(self):
        self.sheets_service = None
        self.drive_service = None
        self._setup_google_services()
        
        # Demo data for when web scraping fails
        self.demo_speakers = {
            "AI in FinTech": [
                {"name": "Dr. Sarah Chen", "title": "Chief AI Officer at FinTech Innovations", "location": "San Francisco, CA", "email": "sarah.chen@fintechinnovations.com", "source": "Demo Data", "query": "AI in FinTech", "expertise": "Machine Learning, Financial Risk Assessment"},
                {"name": "Marcus Rodriguez", "title": "VP of AI Strategy at Digital Banking Corp", "location": "New York, NY", "email": "marcus.rodriguez@digitalbanking.com", "source": "Demo Data", "query": "AI in FinTech", "expertise": "AI Ethics, Algorithmic Trading"},
                {"name": "Dr. Emily Watson", "title": "Research Director at AI Finance Institute", "location": "Boston, MA", "email": "emily.watson@aifinance.edu", "source": "Demo Data", "query": "AI in FinTech", "expertise": "Neural Networks, Credit Scoring"},
                {"name": "Alex Thompson", "title": "Founder & CEO of AI-Powered Lending", "location": "Austin, TX", "email": "alex.thompson@ailending.com", "source": "Demo Data", "query": "AI in FinTech", "expertise": "Startup Leadership, AI Implementation"},
                {"name": "Dr. James Kim", "title": "Professor of Computer Science & Finance", "location": "Stanford, CA", "email": "james.kim@stanford.edu", "source": "Demo Data", "query": "AI in FinTech", "expertise": "Academic Research, Industry Collaboration"},
                {"name": "Omar Shehab", "title": "AI Research Scientist at NYU", "location": "New York, NY", "email": "oms7891@nyu.edu", "source": "Demo Data", "query": "AI in FinTech", "expertise": "Machine Learning, Natural Language Processing"},
                {"name": "Mahmoud Kassem", "title": "Data Science Engineer at NYU", "location": "New York, NY", "email": "mki4895@nyu.edu", "source": "Demo Data", "query": "AI in FinTech", "expertise": "Data Engineering, AI Systems"}
            ],
            "Cybersecurity": [
                {"name": "Lisa Park", "title": "Chief Security Officer at CyberDefense Inc", "location": "Washington, DC", "email": "lisa.park@cyberdefense.com", "source": "Demo Data", "query": "Cybersecurity", "expertise": "Threat Intelligence, Incident Response"},
                {"name": "David Chen", "title": "Senior Security Architect", "location": "Seattle, WA", "email": "david.chen@securitycorp.com", "source": "Demo Data", "query": "Cybersecurity", "expertise": "Cloud Security, Zero Trust Architecture"},
                {"name": "Dr. Rachel Green", "title": "Cybersecurity Research Lead", "location": "MIT, Cambridge", "email": "rachel.green@mit.edu", "source": "Demo Data", "query": "Cybersecurity", "expertise": "Academic Research, Emerging Threats"},
                {"name": "Omar Shehab", "title": "Cybersecurity Researcher at NYU", "location": "New York, NY", "email": "oms7891@nyu.edu", "source": "Demo Data", "query": "Cybersecurity", "expertise": "Network Security, Cryptography"},
                {"name": "Mahmoud Kassem", "title": "Security Systems Engineer at NYU", "location": "New York, NY", "email": "mki4895@nyu.edu", "source": "Demo Data", "query": "Cybersecurity", "expertise": "System Security, Penetration Testing"}
            ],
            "Blockchain": [
                {"name": "Michael Chang", "title": "Blockchain Technology Director", "location": "Miami, FL", "email": "michael.chang@blockchaintech.com", "source": "Demo Data", "query": "Blockchain", "expertise": "DeFi, Smart Contracts"},
                {"name": "Sofia Rodriguez", "title": "Cryptocurrency Research Analyst", "location": "Chicago, IL", "email": "sofia.rodriguez@cryptoresearch.com", "source": "Demo Data", "query": "Blockchain", "expertise": "Market Analysis, Regulatory Compliance"},
                {"name": "Omar Shehab", "title": "Blockchain Researcher at NYU", "location": "New York, NY", "email": "oms7891@nyu.edu", "source": "Demo Data", "query": "Blockchain", "expertise": "Distributed Systems, Cryptography"},
                {"name": "Mahmoud Kassem", "title": "Blockchain Developer at NYU", "location": "New York, NY", "email": "mki4895@nyu.edu", "source": "Demo Data", "query": "Blockchain", "expertise": "Smart Contracts, Web3 Development"}
            ],
            "Data Science": [
                {"name": "Dr. Robert Wilson", "title": "Head of Data Science at TechCorp", "location": "Seattle, WA", "email": "robert.wilson@techcorp.com", "source": "Demo Data", "query": "Data Science", "expertise": "Big Data, Predictive Analytics"},
                {"name": "Jennifer Lee", "title": "Senior Data Scientist", "location": "San Francisco, CA", "email": "jennifer.lee@datascience.com", "source": "Demo Data", "query": "Data Science", "expertise": "Machine Learning, Data Visualization"},
                {"name": "Omar Shehab", "title": "Data Science Researcher at NYU", "location": "New York, NY", "email": "oms7891@nyu.edu", "source": "Demo Data", "query": "Data Science", "expertise": "Statistical Analysis, Machine Learning"},
                {"name": "Mahmoud Kassem", "title": "Data Engineer at NYU", "location": "New York, NY", "email": "mki4895@nyu.edu", "source": "Demo Data", "query": "Data Science", "expertise": "Data Pipeline, ETL Processes"}
            ]
        }
    
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
    
    def search_speakers(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search for speakers using demo data and web search."""
        speakers = []
        
        # Try web scraping first
        try:
            web_speakers = self._attempt_web_scraping(query, max_results)
            if web_speakers:
                speakers.extend(web_speakers)
        except Exception as e:
            print(f"⚠️  Web scraping failed: {e}")
        
        # If web search didn't find enough speakers, use demo data
        if len(speakers) < max_results:
            demo_speakers = self._get_demo_speakers(query, max_results - len(speakers))
            speakers.extend(demo_speakers)
        
        return speakers[:max_results]
    
    def _attempt_web_scraping(self, query: str, max_results: int) -> List[Dict]:
        """Attempt to scrape speakers from web sources."""
        speakers = []
        
        try:
            # Try a simple search approach
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+speaker+expert"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for any potential speaker information
                potential_speakers = soup.find_all("h3")[:10]
                
                for i, element in enumerate(potential_speakers):
                    if len(speakers) >= max_results:
                        break
                    
                    title = element.text.strip()
                    if title and len(title) > 10:
                        # Create a mock speaker from the search result
                        speaker = {
                            "name": f"Expert Speaker {i+1}",
                            "title": title[:100],
                            "location": "Various",
                            "email": f"speaker{i+1}@example.com",
                            "source": "Web Search",
                            "query": query,
                            "expertise": query
                        }
                        speakers.append(speaker)
        except Exception as e:
            print(f"Web scraping error: {e}")
        
        return speakers
    
    def _get_demo_speakers(self, query: str, max_results: int) -> List[Dict]:
        """Get demo speakers based on query similarity."""
        # Find the best matching category
        best_match = None
        best_score = 0
        
        for category in self.demo_speakers.keys():
            score = 0
            if query.lower() in category.lower():
                score += 3
            if any(word in query.lower() for word in category.lower().split()):
                score += 1
            if score > best_score:
                best_score = score
                best_match = category
        
        if best_match and best_match in self.demo_speakers:
            return self.demo_speakers[best_match][:max_results]
        else:
            # Return generic demo speakers
            return [
                {"name": "Dr. Expert Speaker", "title": "Industry Expert", "location": "Various", "email": "expert@example.com", "source": "Demo Data", "query": query, "expertise": query},
                {"name": "Professional Presenter", "title": "Conference Speaker", "location": "Various", "email": "presenter@example.com", "source": "Demo Data", "query": query, "expertise": query}
            ][:max_results]
    
    def create_speakers_spreadsheet(self, speakers: List[Dict], title: str = "Hackathon Speakers") -> str:
        """Create a Google Sheets spreadsheet with speaker information."""
        try:
            # Create new spreadsheet
            body = {"properties": {"title": title}}
            spreadsheet = self.sheets_service.spreadsheets().create(body=body).execute()
            spreadsheet_id = spreadsheet["spreadsheetId"]
            
            # Prepare data for writing
            headers = ["Name", "Title", "Location", "Email", "Source", "Query", "Expertise", "Contact Status", "Notes", "Last Updated"]
            data = [headers]
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            for speaker in speakers:
                row = [
                    speaker.get("name", ""),
                    speaker.get("title", ""),
                    speaker.get("location", ""),
                    speaker.get("email", ""),
                    speaker.get("source", ""),
                    speaker.get("query", ""),
                    speaker.get("expertise", ""),
                    "Not Contacted",  # Default status
                    "",  # Notes column
                    current_time  # Last updated
                ]
                data.append(row)
            
            # Write data to sheet
            range_name = "Sheet1!A1:J" + str(len(data))
            body = {"values": data}
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
            
            # Format headers and make it look professional
            self._format_spreadsheet(spreadsheet_id)
            
            return spreadsheet_id
            
        except HttpError as e:
            print(f"❌ Error creating spreadsheet: {e}")
            return None
    
    def _format_spreadsheet(self, spreadsheet_id: str):
        """Format the spreadsheet to make it look professional."""
        try:
            requests = [
                # Format headers
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
                },
                # Auto-resize columns
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": 0,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 10
                        }
                    }
                },
                # Add borders to data
                {
                    "updateBorders": {
                        "range": {
                            "sheetId": 0,
                            "startRowIndex": 0,
                            "endRowIndex": 100,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10
                        },
                        "top": {"style": "SOLID"},
                        "bottom": {"style": "SOLID"},
                        "left": {"style": "SOLID"},
                        "right": {"style": "SOLID"}
                    }
                }
            ]
            
            body = {"requests": requests}
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
        except Exception as e:
            print(f"⚠️  Error formatting spreadsheet: {e}")
    
    def find_and_create_sheet(self, requirements: str, max_results: int = 20) -> Optional[str]:
        """Main method: search for speakers and create Google Sheets."""
        # Search for speakers
        speakers = self.search_speakers(requirements, max_results)
        
        if not speakers:
            return None
        
        # Create Google Sheets
        spreadsheet_id = self.create_speakers_spreadsheet(speakers, f"Speakers - {requirements}")
        
        if spreadsheet_id:
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            return spreadsheet_url
        else:
            return None


# Global instance for the service
speaker_finder_service = SpeakerFinderService()
