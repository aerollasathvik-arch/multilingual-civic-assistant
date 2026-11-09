"""Machine translation with NLLB-200 (facebook/nllb-200-distilled-600M, CC-BY-NC-4.0).

Used in week 5 to translate questions into English before retrieval, and in week 6
for answers going back into the user's language. Non-commercial licence: fine for
this research prototype, not for a production service.
"""
import re

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL = "facebook/nllb-200-distilled-600M"
NLLB_CODES = {"en": "eng_Latn", "pl": "pol_Latn", "ro": "ron_Latn", "ar": "arb_Arab", "ur": "urd_Arab"}


class Translator:
    def __init__(self, model_name=MODEL):
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"  # GPU on Colab, CPU elsewhere
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).eval().to(self.device)

    @torch.inference_mode()
    def _translate_sentences(self, sentences, src, tgt, max_length):
        self.tok.src_lang = NLLB_CODES[src]
        batch = self.tok(sentences, return_tensors="pt", padding=True, truncation=True, max_length=400).to(self.device)
        out = self.model.generate(
            **batch, max_length=max_length, num_beams=4,
            forced_bos_token_id=self.tok.convert_tokens_to_ids(NLLB_CODES[tgt]))
        return self.tok.batch_decode(out, skip_special_tokens=True)

    def translate(self, texts, src, tgt="en", max_length=256):
        """Translate a list of strings from language `src` to `tgt` (project codes, e.g. 'pl').

        NLLB is trained on single sentences and silently drops later sentences of a
        multi-sentence input, so each text is split into sentences first and rejoined.
        """
        if src == tgt:
            return list(texts)
        split = [split_sentences(t) for t in texts]
        flat = [s for parts in split for s in parts]
        done = iter(self._translate_sentences(flat, src, tgt, max_length))
        return [" ".join(next(done) for _ in parts) for parts in split]


def split_sentences(text):
    """Split on sentence-final punctuation, including Arabic ؟ and Urdu ۔ ."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?؟۔])\s+", text.strip())]
    return [p for p in parts if p] or [text]
