from kikotools.tools.prompt_enhancer.logic import (
    cap_words,
    clean_output,
    prepend_triggers,
    split_thinking,
    strip_triggers,
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


def test_cap_words_falls_back_to_last_comma():
    assert cap_words("a b, c d, e f", 5) == "a b, c d"


def test_clean_output_keeps_text_with_several_quoted_parts():
    text = '"A" and "B"'
    assert clean_output(text) == text


def test_clean_output_drops_fence_language_tag():
    assert clean_output("```text\nA fox.\n```") == "A fox."


def test_strip_triggers_removes_trigger():
    assert strip_triggers("mabes9sans walks a dog", "mabes9sans") == "walks a dog"


def test_strip_triggers_ignores_case():
    assert strip_triggers("Mabes9sans walks", "mabes9sans") == "walks"


def test_strip_triggers_keeps_longer_words():
    assert strip_triggers("mabes9sansX walks", "mabes9sans") == "mabes9sansX walks"


def test_strip_triggers_cleans_punctuation():
    assert (
        strip_triggers("mabes9sans, a woman, vito , , in the rain,", "mabes9sans, vito")
        == "a woman, in the rain"
    )


def test_strip_triggers_handles_non_word_characters():
    assert strip_triggers("a fox, v1.0-style, snow", "v1.0-style") == "a fox, snow"


def test_strip_triggers_empty_is_noop():
    assert strip_triggers("a fox", " , ") == "a fox"
