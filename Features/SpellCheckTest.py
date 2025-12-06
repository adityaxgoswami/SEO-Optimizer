import sys
import json
import logging

try:
    import language_tool_python
except ImportError:
    language_tool_python = None
    print("⚠️ language-tool-python is not installed. Run 'pip install language-tool-python'")

def spell_check_test(body_text: str) -> dict:
    """
    Performs a smart grammar and spell check using LanguageTool.
    Categorizes issues into 'Spelling', 'Grammar', and 'Style'.
    """
    result = {
        "total_words": 0,
        "words_checked": 0,
        "misspelled_count": 0,
        "grammar_issues_count": 0,
        "style_issues_count": 0,
        "misspelled_words": [],
        "grammar_issues": [],
        "style_issues": []
    }

    if not body_text:
        return result

    # Basic word count approximation
    words = body_text.split()
    result["total_words"] = len(words)
    result["words_checked"] = len(words)

    if not language_tool_python:
        result["error"] = "Library not installed"
        return result

    try:
        # Initialize the tool (downloads the Java server on first run automatically)
        tool = language_tool_python.LanguageTool('en-US')
        
        # Limit text length to prevent timeouts on massive pages
        checked_text = body_text[:20000]
        matches = tool.check(checked_text) 

        for match in matches:
            # --- ROBUST ATTRIBUTE FETCHING ---
            
            # 1. Get Offset
            offset = getattr(match, 'offset', getattr(match, 'fromx', 0))
            
            # 2. Get Length (Check ALL casing variations)
            error_length = getattr(match, 'errorLength', None)
            if error_length is None: error_length = getattr(match, 'error_length', None) # snake_case
            if error_length is None: error_length = getattr(match, 'len', None)
            if error_length is None: error_length = getattr(match, 'length', None)
            
            # 3. Calculate from positions if explicit length is missing
            if error_length is None:
                tox = getattr(match, 'tox', None)
                fromx = getattr(match, 'fromx', None)
                if tox is not None and fromx is not None:
                    error_length = tox - fromx
            
            # 4. Final Fallback
            if error_length is None:
                error_length = 0

            # 5. Extract other attributes
            rule_id = getattr(match, 'ruleId', getattr(match, 'rule_id', 'UNKNOWN'))
            message = getattr(match, 'message', getattr(match, 'msg', ''))
            context = getattr(match, 'context', '')
            replacements = getattr(match, 'replacements', [])

            issue = {
                "message": message,
                "context": context,
                "replacements": replacements[:3], # Top 3 suggestions
                "offset": offset,
                "length": error_length,
                "rule_id": rule_id
            }
            
            # --- Categorization ---
            rule_type = getattr(match, 'ruleIssueType', getattr(match, 'rule_issue_type', ''))
            category = getattr(match, 'category', '')
            
            # Extract the actual word from the text using offset
            bad_word = ""
            if error_length > 0:
                bad_word = checked_text[offset : offset + error_length]
            
            # Fallback: if bad_word is still empty but we have context, try to guess (rare edge case)
            if not bad_word and context:
                bad_word = "(See context)"

            if rule_type == 'misspelling' or rule_id.startswith('MORFOLOGIK_RULE'):
                result["misspelled_count"] += 1
                result["misspelled_words"].append({
                    "word": bad_word,
                    "suggestions": replacements[:3]
                })
            elif rule_type == 'style' or category == 'STYLE':
                result["style_issues_count"] += 1
                result["style_issues"].append(issue)
            else:
                # Default everything else (typographical, grammar, etc.) to Grammar
                result["grammar_issues_count"] += 1
                result["grammar_issues"].append(issue)

        # close the tool to free memory
        tool.close()

    except Exception as e:
        logging.error(f"Error in SpellCheckTest: {e}")
        result["error"] = str(e)

    return result

if __name__ == "__main__":
    # Test block
    if len(sys.argv) < 2:
        test_text = "Thier is a problem with this sentance. I wants to go there."
    else:
        test_text = sys.argv[1]

    print(f"Running Grammarly-like check on: '{test_text[:50]}...'")
    test_result = spell_check_test(test_text)
    print(json.dumps(test_result, indent=2))