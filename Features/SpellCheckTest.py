import re
import sys
import json
from spellchecker import SpellChecker
import nltk


def download_nltk_data():

    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        print("Downloading necessary NLTK data (punkt, averaged_perceptron_tagger)...")
        nltk.download('punkt', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        print("NLTK data downloaded.")

def spell_check_test(body_text: str) -> dict:
    """
    Performs a spell check on the body text, intelligently ignoring proper nouns.
    """
    result = {
        "total_words": 0,
        "words_checked": 0,
        "misspelled_count": 0,
        "misspelled_words": [],
    }

    if not body_text:
        return result

    # Ensure NLTK data is ready
    download_nltk_data()

    # 1. Tokenize the text into words
    words = nltk.word_tokenize(body_text)
    result["total_words"] = len(words)

    # 2. Use Part-of-Speech (POS) tagging to identify proper nouns
    tagged_words = nltk.pos_tag(words)

    # 3. Filter out proper nouns, numbers, and single-letter words
    words_to_check = [
        word.lower() for word, tag in tagged_words
        if tag not in ('NNP', 'NNPS') and word.isalpha() and len(word) > 1
    ]
    result["words_checked"] = len(words_to_check)
    
    if not words_to_check:
        return result

    # 4. Run the spell check on the filtered list
    spell = SpellChecker()
    misspelled = spell.unknown(words_to_check)
    
    result["misspelled_count"] = len(misspelled)
    result["misspelled_words"] = sorted(list(misspelled))

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python Features/SpellCheckTest.py \"<text to check>\"")
        sys.exit(1)

    input_text = sys.argv[1]
    print(f"Running intelligent spell check on the provided text...")

    test_result = spell_check_test(input_text)

    print("\n--- Test Results ---")
    print(json.dumps(test_result, indent=2))
    
    if test_result["misspelled_count"] > 0:
        print(f"\n⚠️ Found {test_result['misspelled_count']} potential misspellings out of {test_result['words_checked']} words checked.")
    else:
        print("\n✅ No misspellings found.")
