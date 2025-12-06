# -*- coding: utf-8 -*-
"""Simple sentiment analyzer using keyword matching."""

# Positive keywords
POSITIVE = {
    "love", "great", "awesome", "amazing", "wonderful", "happy", "good", "nice",
    "thanks", "thank", "appreciate", "helpful", "excellent", "fantastic",
    "yes", "yeah", "yep", "sure", "ok", "okay", "agree", "right", "correct",
    "haha", "lol", "funny", "cool", "wow", "dear", "sweet", "beautiful"
}

# Negative keywords
NEGATIVE = {
    "hate", "bad", "terrible", "awful", "horrible", "sad", "angry", "upset",
    "no", "wrong", "disagree", "not", "never", "can't", "cannot", "won't",
    "sucks", "stupid", "dumb", "useless", "boring", "annoying", "frustrated"
}

def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of text.
    Returns a value from -1 (very negative) to 1 (very positive).
    """
    words = text.lower().split()
    
    pos_count = sum(1 for w in words if w in POSITIVE)
    neg_count = sum(1 for w in words if w in NEGATIVE)
    
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    
    # Score from -1 to 1
    score = (pos_count - neg_count) / total
    return score

def analyze_engagement(text: str) -> float:
    """
    Analyze user engagement based on message characteristics.
    Returns 0 to 1 (low to high engagement).
    """
    # Longer messages = more engagement
    word_count = len(text.split())
    
    # Normalize to 0-1 (cap at 50 words)
    engagement = min(word_count / 50.0, 1.0)
    
    # Questions indicate engagement
    if "?" in text:
        engagement = min(engagement + 0.2, 1.0)
    
    # Exclamations indicate excitement
    if "!" in text:
        engagement = min(engagement + 0.1, 1.0)
    
    return engagement
