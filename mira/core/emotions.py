# -*- coding: utf-8 -*-
"""Mira 4.0: Dynamic Emotional State using Circumplex Model."""
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Tuple

from ..config import DATA_DIR

EMOTION_FILE = DATA_DIR / "emotional_state.json"

# Decay rate: how fast emotions return to baseline per minute
DECAY_RATE = 0.02  # 2% per minute

# Sensitivity: how much user sentiment shifts emotions
SENSITIVITY = 0.15

@dataclass
class EmotionalState:
    """
    3D Emotional State using Circumplex Model of Affect.
    
    - valence: -1 (sad) to 1 (happy)
    - arousal: -1 (calm) to 1 (excited)
    - dominance: -1 (submissive/insecure) to 1 (dominant/confident)
    """
    valence: float = 0.3      # Slightly positive baseline
    arousal: float = 0.0      # Neutral arousal
    dominance: float = 0.2    # Slightly confident baseline
    last_update: float = 0.0  # Unix timestamp
    
    def drift(self) -> None:
        """Apply temporal decay towards baseline (0, 0, 0.2)."""
        now = time.time()
        if self.last_update == 0:
            self.last_update = now
            return
        
        elapsed_minutes = (now - self.last_update) / 60.0
        decay = DECAY_RATE * elapsed_minutes
        
        # Drift towards baseline
        self.valence = self._decay_towards(self.valence, 0.3, decay)
        self.arousal = self._decay_towards(self.arousal, 0.0, decay)
        self.dominance = self._decay_towards(self.dominance, 0.2, decay)
        self.last_update = now
    
    def _decay_towards(self, current: float, target: float, rate: float) -> float:
        """Move current value towards target by rate."""
        diff = target - current
        return current + diff * min(rate, 1.0)
    
    def update(self, user_sentiment: float, engagement: float = 0.0) -> None:
        """
        Update emotional state based on user interaction.
        
        Args:
            user_sentiment: -1 (negative) to 1 (positive) sentiment from user message
            engagement: 0 to 1 (how engaged the user seems, based on message length etc.)
        """
        # Positive sentiment makes Mira happier
        self.valence = self._clamp(self.valence + user_sentiment * SENSITIVITY)
        
        # Engagement increases arousal (excitement)
        self.arousal = self._clamp(self.arousal + engagement * SENSITIVITY * 0.5)
        
        # Positive sentiment increases confidence
        self.dominance = self._clamp(self.dominance + user_sentiment * SENSITIVITY * 0.3)
        
        self.last_update = time.time()
    
    def _clamp(self, value: float) -> float:
        """Clamp value to [-1, 1]."""
        return max(-1.0, min(1.0, value))
    
    def to_mood_label(self) -> str:
        """Convert state to a human-readable mood label."""
        # Map the 3D space to discrete moods
        if self.valence > 0.5:
            if self.arousal > 0.3:
                return "excited" if self.dominance > 0 else "enthusiastic"
            else:
                return "serene" if self.dominance > 0 else "content"
        elif self.valence < -0.3:
            if self.arousal > 0.3:
                return "agitated" if self.dominance > 0 else "anxious"
            else:
                return "melancholy" if self.dominance > 0 else "sad"
        else:
            if self.arousal > 0.3:
                return "playful"
            elif self.arousal < -0.3:
                return "tired"
            return "neutral"
    
    def to_prompt_context(self) -> str:
        """Generate context for LLM prompts."""
        mood = self.to_mood_label()
        return f"[EMOTIONAL STATE]: {mood} (valence: {self.valence:.2f}, arousal: {self.arousal:.2f}, confidence: {self.dominance:.2f})"


# Global state instance
_state: EmotionalState = None

def load_state() -> EmotionalState:
    """Load emotional state from disk, or create new."""
    global _state
    if _state is not None:
        return _state
    
    if EMOTION_FILE.exists():
        try:
            with open(EMOTION_FILE, "r") as f:
                data = json.load(f)
                _state = EmotionalState(**data)
        except Exception:
            _state = EmotionalState()
    else:
        _state = EmotionalState()
    
    return _state

def save_state() -> None:
    """Persist emotional state to disk."""
    global _state
    if _state is None:
        return
    with open(EMOTION_FILE, "w") as f:
        json.dump(asdict(_state), f)

def get_mood() -> str:
    """Get current mood label."""
    state = load_state()
    state.drift()  # Apply temporal decay
    save_state()
    return state.to_mood_label()

def update_emotion(sentiment: float, engagement: float = 0.0) -> None:
    """Update emotional state based on user interaction."""
    state = load_state()
    old_mood = state.to_mood_label()
    
    state.drift()
    state.update(sentiment, engagement)
    save_state()
    
    new_mood = state.to_mood_label()
    
    # Trigger self-reflection if mood changed significantly
    if old_mood != new_mood:
        try:
            from .self_narrative import self_reflect
            emotion_context = state.to_prompt_context()
            # Run asynchronously to not block response
            import threading
            t = threading.Thread(target=self_reflect, args=(emotion_context,))
            t.daemon = True
            t.start()
        except Exception as e:
            print(f"[Emotions] Self-reflection skipped: {e}")

def get_emotion_context() -> str:
    """Get emotional context for prompts."""
    state = load_state()
    state.drift()
    save_state()
    return state.to_prompt_context()

