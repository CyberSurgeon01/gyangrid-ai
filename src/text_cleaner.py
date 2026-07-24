import re


def clean_text(text):
    # de-hyphenate words broken across a line-wrap
    text = re.sub(r"-\n", "", text)

    # collapse 3+ blank lines down to exactly one blank line (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # collapse repeated spaces/tabs, but leave newlines alone
    text = re.sub(r"[ \t]+", " ", text)

    # trim trailing/leading spaces on each line without merging lines together
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text.strip()