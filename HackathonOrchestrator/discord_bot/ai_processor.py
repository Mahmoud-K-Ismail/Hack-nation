"""
AI Processing utilities for Discord bot
Handles embeddings, sentiment analysis, and response generation.
"""

import os
import asyncio
import json
from typing import Optional, List, Dict, Any
import numpy as np
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
import logging

from .database import SessionLocal
from .models import FAQEmbedding

logger = logging.getLogger(__name__)


class AIProcessor:
    """AI processing for Discord bot functionality"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.model_name = "gpt-3.5-turbo"
        self.embedding_model = "text-embedding-3-small"
        self.max_retries = 3
        
    async def analyze_message(self, content: str) -> Dict[str, Any]:
        """Analyze message for sentiment, urgency, and category"""
        try:
            if not self.openai_client.api_key:
                # Return mock analysis if no API key
                return self._mock_analysis(content)
            
            prompt = f"""
Analyze the following Discord message from a hackathon participant and provide:
1. Sentiment score (-1.0 to 1.0, where -1 is very negative, 0 is neutral, 1 is very positive)
2. Urgency score (0.0 to 1.0, where 0 is not urgent, 1 is very urgent)
3. Category (one of: "faq", "complaint", "social", "spam", "unknown")

Message: "{content}"

Respond with valid JSON only:
{{"sentiment_score": 0.0, "urgency_score": 0.0, "category": "unknown"}}
"""

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            return {
                "sentiment_score": float(result.get("sentiment_score", 0.0)),
                "urgency_score": float(result.get("urgency_score", 0.0)),
                "category": result.get("category", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
            return self._mock_analysis(content)
    
    def _mock_analysis(self, content: str) -> Dict[str, Any]:
        """Mock analysis for when OpenAI is unavailable"""
        # Simple heuristic analysis
        content_lower = content.lower()
        
        # Sentiment analysis (basic)
        negative_words = ["bad", "terrible", "awful", "broken", "fail", "problem", "issue", "bug"]
        positive_words = ["good", "great", "awesome", "works", "thanks", "love", "perfect"]
        
        negative_count = sum(1 for word in negative_words if word in content_lower)
        positive_count = sum(1 for word in positive_words if word in content_lower)
        
        sentiment_score = (positive_count - negative_count) / max(1, len(content_lower.split()))
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        # Urgency analysis (basic)
        urgent_words = ["urgent", "emergency", "asap", "immediately", "help", "broken", "crash"]
        urgency_score = min(1.0, sum(1 for word in urgent_words if word in content_lower) * 0.3)
        
        # Category analysis (basic)
        question_words = ["how", "what", "when", "where", "why", "can", "could", "should"]
        complaint_words = ["broken", "bug", "error", "problem", "issue", "wrong"]
        
        if any(word in content_lower for word in complaint_words):
            category = "complaint"
        elif any(word in content_lower for word in question_words) or "?" in content:
            category = "faq"
        elif len(content) < 10:
            category = "social"
        else:
            category = "unknown"
        
        return {
            "sentiment_score": sentiment_score,
            "urgency_score": urgency_score,
            "category": category
        }
    
    async def find_faq_match(self, question: str, hackathon_id: str, threshold: float = 0.78) -> Optional[Dict[str, str]]:
        """Find the best FAQ match for a question using embeddings"""
        try:
            if not self.openai_client.api_key:
                return self._mock_faq_match(question, hackathon_id)
            
            # Generate embedding for the question
            question_embedding = await self.get_embedding(question)
            if not question_embedding:
                return None
            
            # Search for similar FAQs in database
            with SessionLocal() as db:
                faqs = db.query(FAQEmbedding).filter(
                    FAQEmbedding.hackathon_id == hackathon_id
                ).all()
                
                if not faqs:
                    logger.info(f"No FAQ embeddings found for hackathon {hackathon_id}")
                    return None
                
                best_match = None
                best_similarity = 0.0
                
                for faq in faqs:
                    if faq.embedding:
                        similarity = self.cosine_similarity(question_embedding, faq.embedding)
                        
                        if similarity > best_similarity and similarity >= threshold:
                            best_similarity = similarity
                            best_match = {
                                "question": faq.question_text,
                                "answer": faq.answer_text,
                                "similarity": similarity
                            }
                
                if best_match:
                    logger.info(f"Found FAQ match with similarity {best_similarity:.3f}")
                    return best_match
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding FAQ match: {e}")
            return None
    
    def _mock_faq_match(self, question: str, hackathon_id: str) -> Optional[Dict[str, str]]:
        """Mock FAQ matching for when OpenAI is unavailable"""
        # Simple keyword-based matching
        mock_faqs = {
            "wifi": {
                "question": "What's the WiFi password?",
                "answer": "The WiFi network is 'HackathonGuest' with password 'hack2024'. If you're having trouble connecting, please ask an organizer for help."
            },
            "food": {
                "question": "When is food served?",
                "answer": "Meals are served at:\n• Breakfast: 8:00 AM\n• Lunch: 12:30 PM\n• Dinner: 6:30 PM\n• Snacks available 24/7 in the main hall."
            },
            "submission": {
                "question": "How do I submit my project?",
                "answer": "Project submissions are due by 11:59 PM on Sunday. Submit via the hackathon platform at [platform-url]. Include your team name, project description, and GitHub repository link."
            },
            "schedule": {
                "question": "What's the schedule?",
                "answer": "Check the complete schedule on our platform or the #announcements channel. Key events:\n• Opening Ceremony: Friday 6 PM\n• Hacking Begins: Friday 8 PM\n• Final Presentations: Sunday 2 PM"
            }
        }
        
        question_lower = question.lower()
        
        for keyword, faq in mock_faqs.items():
            if keyword in question_lower:
                return {
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "similarity": 0.85
                }
        
        return None
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using OpenAI"""
        try:
            if not self.openai_client.api_key:
                return None
            
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text.strip()
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            a_np = np.array(a)
            b_np = np.array(b)
            
            dot_product = np.dot(a_np, b_np)
            norm_a = np.linalg.norm(a_np)
            norm_b = np.linalg.norm(b_np)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def summarize_flood(self, messages: List[str]) -> str:
        """Summarize repeated messages for flood response"""
        try:
            if not self.openai_client.api_key or not messages:
                return self._mock_flood_summary(messages)
            
            messages_text = "\n".join([f"- {msg}" for msg in messages[-10:]])  # Last 10 messages
            
            prompt = f"""
Summarize the following repeated questions from hackathon participants into one clear, helpful announcement. 
Focus on the main issue or question being asked repeatedly.

Messages:
{messages_text}

Provide a helpful summary response that addresses the common concern.
"""

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error summarizing flood: {e}")
            return self._mock_flood_summary(messages)
    
    def _mock_flood_summary(self, messages: List[str]) -> str:
        """Mock flood summary when OpenAI is unavailable"""
        if not messages:
            return "Multiple similar questions detected. Please check the FAQ or ask an organizer for help."
        
        # Find most common words
        all_words = []
        for msg in messages:
            all_words.extend(msg.lower().split())
        
        from collections import Counter
        common_words = Counter(all_words).most_common(3)
        
        if common_words:
            topic = common_words[0][0]
            return f"I noticed several questions about '{topic}'. Please check the FAQ section or reach out to organizers for assistance."
        
        return "Multiple similar questions detected. Please check the FAQ or ask an organizer for help."
    
    async def create_escalation_summary(self, content: str) -> str:
        """Create a summary for escalation to organizers"""
        try:
            if not self.openai_client.api_key:
                return self._mock_escalation_summary(content)
            
            prompt = f"""
A hackathon participant has sent a message that requires organizer attention. 
Create a brief, professional summary for the organizers explaining the issue.

Original message: "{content}"

Provide a 1-2 sentence summary focusing on the key issue or concern.
"""

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error creating escalation summary: {e}")
            return self._mock_escalation_summary(content)
    
    def _mock_escalation_summary(self, content: str) -> str:
        """Mock escalation summary when OpenAI is unavailable"""
        content_preview = content[:100] + "..." if len(content) > 100 else content
        return f"Participant reported an issue requiring attention: {content_preview}"
    
    async def sync_faq_embeddings(self, hackathon_id: str, faqs: List[Dict[str, str]]) -> int:
        """Sync FAQ embeddings for a hackathon"""
        try:
            updated_count = 0
            
            with SessionLocal() as db:
                # Remove existing embeddings
                db.query(FAQEmbedding).filter(
                    FAQEmbedding.hackathon_id == hackathon_id
                ).delete()
                
                # Add new embeddings
                for faq in faqs:
                    question = faq.get("question", "")
                    answer = faq.get("answer", "")
                    faq_id = faq.get("id")
                    
                    if not question or not answer:
                        continue
                    
                    # Get embedding for question
                    embedding = await self.get_embedding(question)
                    
                    faq_embedding = FAQEmbedding(
                        hackathon_id=hackathon_id,
                        faq_id=faq_id,
                        question_text=question,
                        answer_text=answer,
                        embedding=embedding
                    )
                    
                    db.add(faq_embedding)
                    updated_count += 1
                
                db.commit()
                
                logger.info(f"Synced {updated_count} FAQ embeddings for hackathon {hackathon_id}")
                return updated_count
                
        except Exception as e:
            logger.error(f"Error syncing FAQ embeddings: {e}")
            return 0
    
    async def generate_response(self, question: str, context: str = "") -> str:
        """Generate a helpful response to a question"""
        try:
            if not self.openai_client.api_key:
                return "I'm here to help! Please check the FAQ section or ask an organizer for assistance."
            
            prompt = f"""
You are a helpful assistant for a hackathon event. A participant has asked a question.
Provide a friendly, helpful response. If you don't know the answer, suggest they ask an organizer.

Question: "{question}"
{f"Additional context: {context}" if context else ""}

Keep your response concise and helpful.
"""

            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm here to help! Please check the FAQ section or ask an organizer for assistance."
