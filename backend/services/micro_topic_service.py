"""
Micro Topic Extraction Service v2.2

Optimizations:
- Batch processing with spaCy nlp.pipe() (5-10x faster)
- Progress logging for large datasets

Fixes:
- Fix 1: Multi-word NER subsumption (drop unigram components)
- Fix 2: Text sanity for NER (clean artifacts like "#emirates #")
- Fix 3: Weak noun blacklist (drop generic nouns unless in NER)
- Fix 4: Noun sanity (clean "city.#history" -> "city")

Pipeline:
- Only processes events with engagement="active" and type="watch"
- Extracts hashtags -> stored in `hashtags` field
- English: NER (en_core_web_md) -> `ner`, Nouns (POS) -> `nouns`
- Hinglish: Remove Devanagari -> `text_v1`, then apply English pipeline
- Hindi: Stanza NER + Noun extraction
- Final: Aggregate, filter, and deduplicate -> `micro_topics`
"""

import re
import unicodedata
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter

# =========================================================
# STOPWORDS
# =========================================================

ENGLISH_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "also", "now", "and",
    "but", "if", "or", "because", "until", "while", "this", "that", "these",
    "those", "what", "which", "who", "whom", "whose", "i", "you", "he",
    "she", "it", "we", "they", "me", "him", "her", "us", "them", "my",
    "your", "his", "its", "our", "their", "myself", "yourself", "himself",
    "herself", "itself", "ourselves", "themselves", "am", "about", "get",
    "got", "go", "going", "went", "come", "came", "make", "made", "take",
    "took", "see", "saw", "know", "knew", "think", "thought", "want",
    "like", "look", "use", "find", "give", "tell", "say", "said", "video",
    "watch", "watched", "new", "first", "last", "best", "top", "full",
    "part", "episode", "ep", "vs", "ft", "feat", "official", "exclusive",
    "shorts", "short", "movie", "clip", "scene", "trailer", "teaser"
}

HINDI_STOPWORDS = {
    "का", "के", "की", "है", "हैं", "था", "थे", "थी", "में", "से", "को",
    "पर", "ने", "और", "या", "एक", "यह", "वह", "इस", "उस", "जो", "तो",
    "भी", "कर", "हो", "ही", "अब", "जब", "तक", "बहुत", "कुछ", "सब",
    "कोई", "किसी", "अपने", "उनके", "इनके", "वाले", "वाली", "वाला"
}

WEAK_NOUNS = {
    "man", "men", "woman", "women", "person", "people", "guy", "guys",
    "leader", "leaders", "member", "members", "player", "players",
    "team", "teams", "group", "groups", "family", "families",
    "death", "life", "time", "day", "days", "night", "nights",
    "year", "years", "month", "months", "week", "weeks",
    "thing", "things", "stuff", "way", "ways",
    "world", "place", "places", "area", "areas", "country", "countries",
    "city", "cities", "town", "towns", "home", "house",
    "end", "start", "beginning", "part", "parts", "side", "sides",
    "point", "points", "case", "cases", "fact", "facts",
    "news", "update", "updates", "story", "stories",
    "channel", "channels", "subscriber", "subscribers",
    "view", "views", "like", "likes", "comment", "comments",
    "reaction", "reactions", "highlight", "highlights",
    "moment", "moments", "episode", "episodes"
}

# =========================================================
# LAZY MODEL LOADING
# =========================================================

_nlp_en_md = None
_stanza_hi = None


def get_spacy_english_md():
    """Lazy load spaCy English medium model."""
    global _nlp_en_md
    if _nlp_en_md is None:
        try:
            import spacy
            _nlp_en_md = spacy.load("en_core_web_md")
            print("[OK] Loaded en_core_web_md")
        except OSError:
            print("[ERROR] en_core_web_md not found. Run: python -m spacy download en_core_web_md")
            _nlp_en_md = None
    return _nlp_en_md


def get_stanza_hindi():
    """Lazy load Stanza Hindi pipeline."""
    global _stanza_hi
    if _stanza_hi is None:
        try:
            import stanza
            stanza.download('hi', verbose=False)
            _stanza_hi = stanza.Pipeline('hi', processors='tokenize,pos,ner', verbose=False)
            print("[OK] Loaded Stanza Hindi pipeline")
        except Exception as e:
            print(f"[ERROR] Stanza Hindi failed: {e}")
            _stanza_hi = None
    return _stanza_hi


# =========================================================
# TEXT CLEANING UTILITIES
# =========================================================

def normalize_unicode(text: str) -> str:
    """Unicode normalization (NFC) and zero-width character removal."""
    if not text:
        return ""
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def remove_devanagari(text: str) -> str:
    """Remove Devanagari (Hindi) characters from text."""
    return re.sub(r'[\u0900-\u097F]+', ' ', text)


def remove_stopwords(text: str, stopwords: Set[str]) -> str:
    """Remove stopwords from text."""
    words = text.split()
    filtered = [w for w in words if w.lower() not in stopwords]
    return ' '.join(filtered)


def clean_text_v1(text: str) -> str:
    """Clean text for Hinglish processing."""
    text = remove_devanagari(text)
    text = normalize_unicode(text)
    text = remove_stopwords(text, ENGLISH_STOPWORDS)
    text = re.sub(r'[|]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def sanitize_topic(text: str) -> str:
    """
    FIX 2 & 4: Sanitize any topic text (NER, noun, etc).
    Handles cases like:
    - "#emirates #" -> "emirates"
    - "city.#history" -> "city"
    - "world—kuwait" -> "world kuwait"
    """
    if not text:
        return ""
    
    # Remove hashtag patterns (including attached ones like ".#history")
    text = re.sub(r'\.?#\w*', '', text)
    
    # Replace em-dash and other dashes with space
    text = re.sub(r'[—–\-]+', ' ', text)
    
    # Remove leading/trailing punctuation and special chars
    text = text.strip(' #@|[](){}.,!?:;"\'-_')
    
    # Collapse spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# =========================================================
# HASHTAG EXTRACTION
# =========================================================

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text. Returns list of hashtag values (without #)."""
    if not text:
        return []
    
    hashtags = re.findall(r'#(\w+)', text, re.IGNORECASE)
    
    seen = set()
    result = []
    for tag in hashtags:
        tag_lower = tag.lower()
        if tag_lower not in seen and len(tag_lower) >= 2:
            result.append(tag_lower)
            seen.add(tag_lower)
    
    return result


# =========================================================
# BATCH PROCESSING FOR SPACY
# =========================================================

def process_texts_batch_english(texts: List[str], batch_size: int = 100) -> List[Tuple[List[str], List[str]]]:
    """
    Process multiple texts through spaCy using nlp.pipe() for efficiency.
    
    Returns list of (ner_list, noun_list) tuples, one per input text.
    5-10x faster than processing individually.
    """
    nlp = get_spacy_english_md()
    if nlp is None:
        return [([], []) for _ in texts]
    
    # Filter out None/empty texts and track indices
    valid_indices = []
    valid_texts = []
    for i, text in enumerate(texts):
        if text and isinstance(text, str) and text.strip():
            valid_indices.append(i)
            valid_texts.append(text)
    
    # Initialize results for all texts (including empty ones)
    results = [([], []) for _ in texts]
    
    if not valid_texts:
        return results
    
    target_labels = {"PERSON", "ORG", "GPE", "LOC", "EVENT", "NORP", "FAC", "PRODUCT", "WORK_OF_ART"}
    
    # Use nlp.pipe for batch processing on valid texts only
    for idx, doc in enumerate(nlp.pipe(valid_texts, batch_size=batch_size)):
        original_idx = valid_indices[idx]
        
        # Extract NER
        ner = []
        ner_seen = set()
        for ent in doc.ents:
            if ent.label_ in target_labels:
                ent_text = sanitize_topic(ent.text).lower()
                if ent_text and ent_text not in ner_seen and len(ent_text) >= 2:
                    ner.append(ent_text)
                    ner_seen.add(ent_text)
        
        # Create protected set from NER
        protected = set()
        for entity in ner:
            for word in entity.split():
                protected.add(word.lower())
        
        # Extract nouns
        nouns = []
        noun_seen = set()
        for token in doc:
            if token.pos_ in ("NOUN", "PROPN"):
                # FIX 4: Sanitize noun text
                noun_text = sanitize_topic(token.text).lower()
                
                if not noun_text or len(noun_text) < 2:
                    continue
                if noun_text in noun_seen:
                    continue
                if noun_text in ENGLISH_STOPWORDS:
                    continue
                if noun_text.isdigit():
                    continue
                if noun_text in WEAK_NOUNS and noun_text not in protected:
                    continue
                
                nouns.append(noun_text)
                noun_seen.add(noun_text)
        
        results[original_idx] = (ner, nouns)
    
    return results


# =========================================================
# HINDI PIPELINE (Stanza) - Not batched (used less frequently)
# =========================================================

def process_hindi_text(text: str) -> Tuple[List[str], List[str]]:
    """Process Hindi text through Stanza. Returns (ner_list, noun_list)."""
    if not text:
        return [], []
    
    stanza_pipeline = get_stanza_hindi()
    if stanza_pipeline is None:
        return [], []
    
    text = normalize_unicode(text)
    
    try:
        doc = stanza_pipeline(text)
        
        # NER
        ner = []
        ner_seen = set()
        for sentence in doc.sentences:
            for ent in sentence.ents:
                ent_text = sanitize_topic(ent.text)
                if ent_text and ent_text not in ner_seen and len(ent_text) >= 2:
                    ner.append(ent_text)
                    ner_seen.add(ent_text)
        
        # Nouns
        nouns = []
        noun_seen = set()
        for sentence in doc.sentences:
            for word in sentence.words:
                if word.upos in ("NOUN", "PROPN"):
                    noun_text = sanitize_topic(word.text)
                    if (noun_text and 
                        noun_text not in noun_seen and 
                        len(noun_text) >= 2 and
                        noun_text not in HINDI_STOPWORDS):
                        nouns.append(noun_text)
                        noun_seen.add(noun_text)
        
        return ner, nouns
    except Exception as e:
        print(f"[ERROR] Hindi processing failed: {e}")
        return [], []


# =========================================================
# NER SUBSUMPTION
# =========================================================

def apply_ner_subsumption(all_topics: List[str], ner_entities: List[str]) -> List[str]:
    """
    FIX 1: If a multi-word NER exists, drop its unigram components.
    Example: If "greg biffle" in topics -> drop "greg" and "biffle"
    """
    subsumed = set()
    for entity in ner_entities:
        words = entity.split()
        if len(words) > 1:
            for word in words:
                subsumed.add(word.lower())
    
    filtered = []
    for topic in all_topics:
        topic_lower = topic.lower()
        if ' ' in topic_lower or topic_lower not in subsumed:
            filtered.append(topic)
    
    return filtered


# =========================================================
# MAIN BATCH EXTRACTION FUNCTION
# =========================================================

def process_events_batch(events: List[Dict], batch_size: int = 100) -> List[Dict]:
    """
    Process a batch of events with optimized batch NLP processing.
    
    Uses spaCy's nlp.pipe() for 5-10x faster processing.
    """
    # Filter qualifying events
    qualifying_indices = []
    texts_to_process = []
    language_types = []
    
    for i, event in enumerate(events):
        if event.get("type") == "watch" and event.get("engagement") == "active":
            text_clean = event.get("text_clean", "")
            lang = event.get("language_type", "").lower()
            
            if lang == "hinglish":
                # For hinglish, clean the text first
                text_v1 = clean_text_v1(text_clean)
                event["text_v1"] = text_v1
                texts_to_process.append(text_v1 if text_v1 else "")
            elif lang == "hindi":
                texts_to_process.append("")  # Will process separately
            else:
                texts_to_process.append(text_clean)
            
            qualifying_indices.append(i)
            language_types.append(lang)
    
    total = len(qualifying_indices)
    print(f"[TOPIC] Processing {total} qualifying events...")
    
    if total == 0:
        return events
    
    # Batch process English/Hinglish texts through spaCy
    english_indices = []
    english_texts = []
    
    for idx, (i, lang) in enumerate(zip(qualifying_indices, language_types)):
        if lang in ("english", "hinglish", "unknown", ""):
            english_indices.append(idx)
            english_texts.append(texts_to_process[idx])
    
    print(f"[TOPIC] Batch processing {len(english_texts)} English/Hinglish texts...")
    english_results = process_texts_batch_english(english_texts, batch_size)
    
    # Map results back
    english_result_map = {}
    for idx, result in zip(english_indices, english_results):
        english_result_map[idx] = result
    
    # Process each event and add results
    processed_count = 0
    for idx, i in enumerate(qualifying_indices):
        event = events[i]
        text_clean = event.get("text_clean", "")
        lang = language_types[idx]
        
        # Extract hashtags
        hashtags = extract_hashtags(text_clean)
        
        # Get NER and nouns based on language
        if lang == "hindi":
            ner, nouns = process_hindi_text(text_clean)
        else:
            # Get from batch results
            ner, nouns = english_result_map.get(idx, ([], []))
        
        # Aggregate topics
        all_topics = []
        seen = set()
        
        for h in hashtags:
            h_lower = h.lower()
            if h_lower not in seen:
                all_topics.append(h_lower)
                seen.add(h_lower)
        
        for e in ner:
            e_lower = e.lower()
            if e_lower not in seen:
                all_topics.append(e_lower)
                seen.add(e_lower)
        
        for n in nouns:
            n_lower = n.lower()
            if n_lower not in seen:
                all_topics.append(n_lower)
                seen.add(n_lower)
        
        # Apply NER subsumption
        all_topics = apply_ner_subsumption(all_topics, ner)
        
        # Store results
        event["hashtags"] = hashtags
        event["ner"] = ner
        event["nouns"] = nouns
        event["micro_topics"] = all_topics
        
        processed_count += 1
        if processed_count % 1000 == 0:
            print(f"[TOPIC] Processed {processed_count}/{total} events...")
    
    print(f"[TOPIC] Completed processing {total} events.")
    return events


# =========================================================
# LEGACY SINGLE EVENT FUNCTION (for testing)
# =========================================================

def extract_micro_topics_v2(event: Dict) -> Dict:
    """Extract micro topics from a single event. Use process_events_batch for bulk."""
    if event.get("type") != "watch" or event.get("engagement") != "active":
        return event
    
    text_clean = event.get("text_clean", "")
    language_type = event.get("language_type", "").lower()
    
    hashtags = extract_hashtags(text_clean)
    
    if language_type == "english":
        results = process_texts_batch_english([text_clean])
        ner, nouns = results[0] if results else ([], [])
    elif language_type == "hinglish":
        text_v1 = clean_text_v1(text_clean)
        event["text_v1"] = text_v1
        results = process_texts_batch_english([text_v1])
        ner, nouns = results[0] if results else ([], [])
    elif language_type == "hindi":
        ner, nouns = process_hindi_text(text_clean)
    else:
        results = process_texts_batch_english([text_clean])
        ner, nouns = results[0] if results else ([], [])
    
    all_topics = []
    seen = set()
    
    for h in hashtags:
        h_lower = h.lower()
        if h_lower not in seen:
            all_topics.append(h_lower)
            seen.add(h_lower)
    
    for e in ner:
        e_lower = e.lower()
        if e_lower not in seen:
            all_topics.append(e_lower)
            seen.add(e_lower)
    
    for n in nouns:
        n_lower = n.lower()
        if n_lower not in seen:
            all_topics.append(n_lower)
            seen.add(n_lower)
    
    all_topics = apply_ner_subsumption(all_topics, ner)
    
    event["hashtags"] = hashtags
    event["ner"] = ner
    event["nouns"] = nouns
    event["micro_topics"] = all_topics
    
    return event


def get_aggregated_topics(events: List[Dict], top_n: int = 50) -> Dict:
    """Aggregate micro topics across all events."""
    hashtag_counter = Counter()
    ner_counter = Counter()
    noun_counter = Counter()
    topic_counter = Counter()
    
    for event in events:
        hashtag_counter.update(event.get("hashtags", []))
        ner_counter.update(event.get("ner", []))
        noun_counter.update(event.get("nouns", []))
        topic_counter.update(event.get("micro_topics", []))
    
    return {
        "top_hashtags": [{"topic": t, "count": c} for t, c in hashtag_counter.most_common(top_n)],
        "top_ner": [{"topic": t, "count": c} for t, c in ner_counter.most_common(top_n)],
        "top_nouns": [{"topic": t, "count": c} for t, c in noun_counter.most_common(top_n)],
        "top_micro_topics": [{"topic": t, "count": c} for t, c in topic_counter.most_common(top_n)],
        "stats": {
            "total_unique_hashtags": len(hashtag_counter),
            "total_unique_ner": len(ner_counter),
            "total_unique_nouns": len(noun_counter),
            "total_unique_topics": len(topic_counter)
        }
    }
