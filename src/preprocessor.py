import re
import spacy

nlp = spacy.load("en_core_web_sm")


class TextPreprocessor:

    def clean_text(self, text):

        text = text.lower()

        text = re.sub(r"http\S+", "", text)

        text = re.sub(r"\S+@\S+", "", text)

        text = re.sub(r"[^a-zA-Z0-9\s:/-]", " ", text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def preprocess(self, text):

        text = self.clean_text(text)

        doc = nlp(text)

        tokens = []

        for token in doc:

            if token.is_stop:
                continue

            if token.is_punct:
                continue

            if token.is_space:
                continue

            tokens.append(token.lemma_)

        return " ".join(tokens)


if __name__ == "__main__":

    sample = """
    Congratulations!

    Your coding assessment is on 18 October 2026.

    Technical Interview after 3 days.

    HR Interview one week later.
    """

    processor = TextPreprocessor()

    result = processor.preprocess(sample)

    print(result)