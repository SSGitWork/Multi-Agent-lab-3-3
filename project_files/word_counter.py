"""
word_counter.py
===============
Counts word frequencies in a given text string.
"""

import string


def count_words(text: str) -> dict[str, int]:
    """Count the frequency of each word in the input text.

    Parameters
    ----------
    text:
        A string of natural language text.

    Returns
    -------
    dict[str, int]
        Mapping of word to frequency count. Words are deduplicated
        and counted case-insensitively, with punctuation stripped.

    Examples
    --------
    >>> count_words("The cat sat on the mat.")
    {'the': 2, 'cat': 1, 'sat': 1, 'on': 1, 'mat': 1}
    """
    counts = {}
    for word in text.split():
        # Strip punctuation and make lowercase
        word = word.strip(string.punctuation).lower()
        if word:
            counts[word] = counts.get(word, 0) + 1
    return counts


def top_n_words(counts: dict[str, int], n: int) -> dict[str, int]:
    """Return the n most frequent words from a frequency count dict.

    Parameters
    ----------
    counts:
        Output of count_words().
    n:
        Number of top words to return.

    Returns
    -------
    dict[str, int]
        The n most frequent words, sorted descending by count.

    Examples
    --------
    >>> top_n_words({'the': 3, 'cat': 2, 'sat': 1}, 2)
    {'the': 3, 'cat': 2}
    """
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_words[:n])