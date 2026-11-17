"""Grounded answer generation with an openly licensed LLM (Qwen/Qwen3.5-4B, Apache-2.0).

Why this model (task T26):
  * Apache-2.0 and not gated, so it can be run locally or on a free Colab GPU and user questions
    never leave the machine (see docs/ethics-notes.md: no third-party API without consent).
  * The model card states support for 201 languages and dialects; Polish, Romanian, Arabic and Urdu
    are all needed here.
  * 4B parameters (9.3 GB of weights in 16-bit): fits a 16 GB Colab T4 in float16 and the 24 GB development laptop in bfloat16.
Qwen3.5 "thinks" before answering by default; thinking is switched off (enable_thinking=False) so the
output is the answer only. Decoding is greedy so that every run gives the same answer.
"""
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen3.5-4B"
NO_ANSWER = "NO_ANSWER"
LANGUAGE_NAMES = {"en": "English", "pl": "Polish", "ro": "Romanian", "ar": "Arabic", "ur": "Urdu"}

SYSTEM = """You help people in England understand official guidance on health services, housing and schools.
You are given numbered extracts from official GOV.UK and NHS.uk pages, and a question.

Rules:
1. Use ONLY facts stated in the extracts. Never add facts, dates, places or general remarks from your own knowledge.
2. Every sentence must end with the number of the extract it comes from, in square brackets, for example [1] or [1][2].
   If you cannot point to an extract for a sentence, leave that sentence out.
3. Answer the question first. Write in plain language: short sentences, everyday words, no more than 120 words.
4. If the extracts do not answer the question, reply with exactly NO_ANSWER and nothing else.
5. Do not give medical diagnoses or legal advice about the user's own case; explain what the guidance says.
6. Write the whole answer in {language}."""

# Ungrounded baseline (task T30): same model, same audience and style rules, but no extracts and no citations.
BASELINE = """You help people in England understand official guidance on health services, housing and schools.

Rules:
1. Answer the question first. Write in plain language: short sentences, everyday words, no more than 120 words.
2. If you do not know the answer, say so.
3. Do not give medical diagnoses or legal advice about the user's own case; explain what the guidance says.
4. Write the whole answer in {language}."""

CHECK = """You check whether numbered extracts from official GOV.UK and NHS.uk pages answer a question.
The question may be in any language. Reply YES if the extracts contain the information needed to answer it,
even partly. Reply NO if they do not. Reply with one word: YES or NO."""

CITATION = re.compile(r"\[(\d+)\]")


def format_sources(passages):
    """Number the passages [1]..[k] the way the model will cite them."""
    return "\n\n".join(f"[{n}] {p['title']} - {p['heading']}\n{p['text']}" for n, p in enumerate(passages, 1))


def build_messages(question, passages, answer_lang, pivot=False):
    """pivot=True: the answer is written in English for a question in another language (translate mode).
    The model tends to follow the question's language, so the instruction is repeated after the question."""
    system = SYSTEM.format(language=LANGUAGE_NAMES[answer_lang])
    user = f"Extracts:\n\n{format_sources(passages)}\n\nQuestion: {question}"
    if pivot:
        user += "\n\nWrite the answer in English, even though the question is in another language."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def check_messages(question, passages):
    user = f"Extracts:\n\n{format_sources(passages)}\n\nQuestion: {question}\n\nDo the extracts answer the question?"
    return [{"role": "system", "content": CHECK}, {"role": "user", "content": user}]


def baseline_messages(question, answer_lang):
    return [{"role": "system", "content": BASELINE.format(language=LANGUAGE_NAMES[answer_lang])},
            {"role": "user", "content": question}]


def citations(answer):
    """Citation numbers used in an answer, in order of first use."""
    return list(dict.fromkeys(int(n) for n in CITATION.findall(answer)))


class Generator:
    def __init__(self, model_name=MODEL, device=None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.bfloat16 if device == "mps" else torch.float32
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype).to(device).eval()

    @torch.inference_mode()
    def chat(self, messages, max_new_tokens=300):
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                    enable_thinking=False)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        out = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        return self.tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    def answerable(self, question, passages):
        """Refusal rule 2: a separate yes/no call - do the passages answer the question?"""
        return self.chat(check_messages(question, passages), max_new_tokens=3).strip().upper().startswith("YES")

    def answer_ungrounded(self, question, answer_lang):
        """Baseline: the same model answers from its own knowledge, with no retrieved sources."""
        return self.chat(baseline_messages(question, answer_lang))

    def answer(self, question, passages, answer_lang, pivot=False):
        """Answer from the passages only. Returns the raw model text (may be NO_ANSWER)."""
        return self.chat(build_messages(question, passages, answer_lang, pivot))
