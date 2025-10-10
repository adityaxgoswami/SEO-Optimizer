# Features/RelatedKeywordsTest.py
import spacy
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    nlp = None

def related_keywords_test(body_text: str, target_keyword: str) -> dict:
    results = {
        "model_loaded": bool(nlp),
        "target_keyword": target_keyword,
        "related_keywords_found": [],
        "error": None
    }

    if not nlp:
        results["error"] = "spaCy model 'en_core_web_md' not found. Please run: python -m spacy download en_core_web_md"
        return results

    if not target_keyword:
        results["error"] = "No target keyword provided for analysis."
        return results

    if not body_text:
        results["error"] = "No body text available for analysis."
        return results

    # Process both the body text and the target keyword with spaCy
    doc = nlp(body_text.lower())
    target_token = nlp(target_keyword.lower())

    related_words = set()#using a set to avoid duplicate words 
  
    for token in doc:
        # We only want to compare meaningful words (nouns, adjectives, verbs)
        # and avoid stopwords (like 'the', 'is', 'a') and punctuation.
        if token.pos_ in ["NOUN", "ADJ", "VERB"] and not token.is_stop and token.has_vector:  
            similarity = target_token.similarity(token)
            if similarity > 0.5:
                related_words.add(token.lemma_)


    if target_keyword.lower() in related_words:
        related_words.remove(target_keyword.lower())

    results["related_keywords_found"] = sorted(list(related_words))

    return results