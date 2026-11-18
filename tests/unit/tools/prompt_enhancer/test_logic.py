from kikotools.tools.prompt_enhancer.logic import (
    cap_words,
    clean_output,
    prepend_triggers,
    split_thinking,
    tokens_include_image,
)


def test_split_thinking_removes_block():
    assert split_thinking("<think>x</think>\nAnswer") == "Answer"


def test_split_thinking_cut_off():
    assert split_thinking("<think>never closed") == ""


def test_split_thinking_no_think_passes_through():
    assert split_thinking(" plain answer ") == "plain answer"


def test_clean_output_strips_preamble_and_quotes():
    assert clean_output('Here is the enhanced prompt:\n"A red fox."') == "A red fox."


def test_clean_output_keeps_inner_quotes():
    text = 'A sign reading "OPEN".'
    assert clean_output(text) == text


def test_clean_output_removes_code_fence():
    assert clean_output("```\nA red fox.\n```") == "A red fox."


def test_cap_words_trims_at_sentence():
    assert cap_words("One two. Three four five.", 4) == "One two."


def test_cap_words_hard_cut_without_sentence_end():
    assert cap_words("a b c d e", 3) == "a b c"


def test_cap_words_none_is_noop():
    assert cap_words("a b c d e", None) == "a b c d e"


def test_prepend_triggers_normalises_separators():
    assert prepend_triggers("A fox.", " mabes9sans, ,vito ") == "mabes9sans, vito, A fox."


def test_prepend_triggers_empty_is_noop():
    assert prepend_triggers("A fox.", " , ") == "A fox."


def test_tokens_include_image_true_and_false():
    assert tokens_include_image({"qwen35": [[({"type": "image"}, 1.0)]]}) is True
    assert tokens_include_image([[(1, 1.0)]]) is False


def test_cap_words_ignores_mid_token_punctuation():
    text = "Use 3.5 mm lens and a very wide angle shot here"
    assert cap_words(text, 5) == "Use 3.5 mm lens and"
