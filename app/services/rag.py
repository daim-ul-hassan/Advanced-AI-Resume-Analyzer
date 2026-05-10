from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from typing import Any

from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+\-#.]{1,}")
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "your",
    "you",
    "are",
    "our",
    "into",
    "will",
    "their",
    "about",
    "using",
    "use",
    "has",
    "had",
    "was",
    "were",
    "but",
    "not",
    "job",
    "resume",
}


def build_vector_payload(resume_text: str) -> dict[str, Any]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
    raw_chunks = [chunk.strip() for chunk in splitter.split_text(resume_text) if chunk.strip()]
    documents = [
        Document(page_content=chunk, metadata={"chunk_id": index + 1})
        for index, chunk in enumerate(raw_chunks)
    ]
    return {
        "chunks": [
            {
                "chunk_id": doc.metadata["chunk_id"],
                "content": doc.page_content,
                "vector": _embed_text(doc.page_content),
            }
            for doc in documents
        ]
    }


def retrieve_relevant_chunks(vector_payload: dict[str, Any], query: str, limit: int = 4) -> list[str]:
    chunks = vector_payload.get("chunks", [])
    if not chunks:
        return []

    query_vector = _embed_text(query)
    scored = []
    for item in chunks:
        score = _cosine_similarity(query_vector, item["vector"])
        scored.append((score, item["content"]))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [content for score, content in scored[:limit] if score > 0]


def analyze_resume(
    *,
    resume_text: str,
    vector_payload: dict[str, Any],
    job_description: str,
    provider: str,
    gemini_key: str | None,
    groq_key: str | None,
    gemini_model: str,
    groq_model: str,
) -> dict[str, Any]:
    retrieved_chunks = retrieve_relevant_chunks(vector_payload, job_description)
    heuristic = _heuristic_analysis(resume_text, retrieved_chunks, job_description)

    if provider == "gemini" and gemini_key:
        try:
            llm_payload = _llm_analysis(
                provider="gemini",
                api_key=gemini_key,
                model_name=gemini_model,
                retrieved_chunks=retrieved_chunks,
                job_description=job_description,
                heuristic=heuristic,
            )
            llm_payload["provider_used"] = "gemini"
            llm_payload["retrieved_chunks"] = retrieved_chunks[:3]
            return llm_payload
        except Exception:
            pass

    if provider == "groq" and groq_key:
        try:
            llm_payload = _llm_analysis(
                provider="groq",
                api_key=groq_key,
                model_name=groq_model,
                retrieved_chunks=retrieved_chunks,
                job_description=job_description,
                heuristic=heuristic,
            )
            llm_payload["provider_used"] = "groq"
            llm_payload["retrieved_chunks"] = retrieved_chunks[:3]
            return llm_payload
        except Exception:
            pass

    heuristic["provider_used"] = "heuristic"
    heuristic["retrieved_chunks"] = retrieved_chunks[:3]
    return heuristic


def _llm_analysis(
    *,
    provider: str,
    api_key: str,
    model_name: str,
    retrieved_chunks: list[str],
    job_description: str,
    heuristic: dict[str, Any],
) -> dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an ATS-style resume analyst. Return valid JSON only. "
                "Use keys: score, strengths, weaknesses, recommendations, matching_keywords, summary. "
                "score must be an integer from 0 to 100. Each list should contain concise strings.",
            ),
            (
                "human",
                "Job description:\n{job_description}\n\n"
                "Retrieved resume evidence:\n{retrieved_chunks}\n\n"
                "Heuristic baseline:\n{heuristic_json}\n\n"
                "Improve the baseline carefully and keep the output realistic.",
            ),
        ]
    )

    if provider == "gemini":
        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.2,
        )
    else:
        model = ChatGroq(
            model=model_name,
            groq_api_key=api_key,
            temperature=0.2,
        )

    chain = prompt | model
    response = chain.invoke(
        {
            "job_description": job_description,
            "retrieved_chunks": "\n\n---\n\n".join(retrieved_chunks) or "No matching chunks were found.",
            "heuristic_json": json.dumps(heuristic, indent=2),
        }
    )
    content = _strip_code_fences(response.content if isinstance(response.content, str) else str(response.content))
    payload = json.loads(content)

    return {
        "score": int(max(0, min(100, payload.get("score", heuristic["score"])))),
        "strengths": _clean_list(payload.get("strengths"), heuristic["strengths"]),
        "weaknesses": _clean_list(payload.get("weaknesses"), heuristic["weaknesses"]),
        "recommendations": _clean_list(payload.get("recommendations"), heuristic["recommendations"]),
        "matching_keywords": _clean_list(payload.get("matching_keywords"), heuristic["matching_keywords"]),
        "summary": str(payload.get("summary", heuristic["summary"])).strip(),
    }


def _heuristic_analysis(
    resume_text: str,
    retrieved_chunks: list[str],
    job_description: str,
) -> dict[str, Any]:
    resume_tokens = [token for token in _tokenize(resume_text) if token not in STOP_WORDS]
    jd_tokens = [token for token in _tokenize(job_description) if token not in STOP_WORDS]

    resume_counts = Counter(resume_tokens)
    jd_counts = Counter(jd_tokens)
    matching_keywords = [word for word, _count in jd_counts.most_common(12) if word in resume_counts][:8]
    missing_keywords = [word for word, _count in jd_counts.most_common(12) if word not in resume_counts][:6]

    overlap_ratio = (len(matching_keywords) / max(1, min(len(jd_counts), 8))) * 100
    length_bonus = 8 if len(resume_text) > 1200 else 0
    evidence_bonus = min(12, len(retrieved_chunks) * 3)
    score = round(max(38, min(96, overlap_ratio + length_bonus + evidence_bonus)))

    strengths = []
    if matching_keywords:
        strengths.append(f"Relevant keywords appear in the resume: {', '.join(matching_keywords[:5])}.")
    if len(resume_text) > 1200:
        strengths.append("The resume has enough content depth to support role matching.")
    if retrieved_chunks:
        strengths.append("Several resume sections align with the provided job description.")

    weaknesses = []
    if missing_keywords:
        weaknesses.append(f"Important job terms are not clearly visible: {', '.join(missing_keywords[:5])}.")
    if "project" not in resume_counts:
        weaknesses.append("Project-based evidence is not strongly signposted.")
    if "impact" not in resume_text.lower() and "%" not in resume_text:
        weaknesses.append("Measured outcomes or impact metrics could be stronger.")

    recommendations = []
    if missing_keywords:
        recommendations.append("Add missing role-specific tools, skills, and domain words where they are truthful.")
    recommendations.append("Use sharper bullet points that connect actions to outcomes.")
    recommendations.append("Mirror the language of the target job description more closely.")

    summary = (
        "The analyzer found moderate alignment between the resume and the job description. "
        "Better keyword coverage and clearer proof of impact would likely improve the match."
        if score < 75
        else "The resume appears reasonably aligned with the target role, with a few opportunities to sharpen relevance."
    )

    if not strengths:
        strengths.append("The resume includes enough text to perform retrieval and comparison.")
    if not weaknesses:
        weaknesses.append("No major gaps were detected by the heuristic pass, but a live LLM review may be more nuanced.")

    return {
        "score": score,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "recommendations": recommendations[:3],
        "matching_keywords": matching_keywords[:8],
        "summary": summary,
    }


def _embed_text(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % dimensions
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        weight = 1.0 + (digest[3] / 255.0)
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def _clean_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if cleaned:
            return cleaned[:5]
    return fallback[:5]


def _strip_code_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped
