import re


class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = ''.join(c for c in text if c.isprintable() or c in (' ', '\n', '\t'))
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
