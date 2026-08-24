"""Deterministic lexical and metadata retrieval over curated knowledge."""

from typing import Dict, Iterable, List, Set

from config.job_match_config import TEXT_STOP_WORDS
from config.knowledge_config import CATEGORY_PRIORITY
from config.roles import ROLE_DEFINITIONS
from utils.normalization import extract_matched_skills, normalize_text

from .models import KnowledgeCategory, KnowledgeItem, RetrievalQuery, RetrievalResult, TrustLevel
from .provenance import provenance_for
from .repository import KnowledgeRepository
from .text_utils import canonical_role_reference, tokenize


class KnowledgeRetriever:
    """Rank curated items using stable lexical, skill, role, and metadata signals."""

    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    def retrieve(self, query: RetrievalQuery | dict) -> List[RetrievalResult]:
        query = RetrievalQuery.model_validate(query)
        query_terms = self._query_terms(query.query)
        query_skills = set(query.skills)
        query_skills.update(extract_matched_skills(query.query).keys())
        query_roles = set(query.roles)
        query_roles.update(self._roles_from_text(query.query))

        if not query_terms and not query.categories and not query_skills and not query_roles:
            return []

        candidates = self.repository.list(minimum_trust=query.minimum_trust)
        ranked = []
        for item in candidates:
            if query.categories and item.category not in set(query.categories):
                continue
            if query.skills and not query_skills.intersection(self._item_skills(item)):
                continue
            if query.roles and not query_roles.intersection(set(item.roles)):
                continue
            score, matched_terms = self._score_item(item, query_terms, query_skills, query_roles)
            if score == 0 and (query.categories or query.skills or query.roles):
                score = 0.10
            if score > 0:
                ranked.append((score, item, matched_terms))

        ranked.sort(
            key=lambda value: (
                -round(value[0], 6),
                CATEGORY_PRIORITY.get(value[1].category.value, 999),
                value[1].knowledge_id,
            )
        )
        return [
            RetrievalResult(
                knowledge_id=item.knowledge_id,
                title=item.title,
                category=item.category,
                content=item.content,
                score=round(score, 6),
                matched_terms=matched_terms,
                knowledge_version=item.version,
                source=provenance_for(item),
            )
            for score, item, matched_terms in ranked[: query.max_results]
        ]

    def _score_item(
        self,
        item: KnowledgeItem,
        query_terms: Set[str],
        query_skills: Set[str],
        query_roles: Set[str],
    ) -> tuple[float, List[str]]:
        title_terms = set(tokenize(item.title))
        keyword_terms = set(tokenize(" ".join(item.keywords)))
        content_terms = set(tokenize(item.content))
        document_terms = title_terms | keyword_terms | content_terms
        matched_terms = set(query_terms.intersection(document_terms))

        item_skills = self._item_skills(item)
        direct_skill_matches = self._direct_skill_matches(item, query_skills)
        related_skill_matches = query_skills.intersection(item_skills) - direct_skill_matches
        skill_matches = direct_skill_matches | related_skill_matches
        matched_terms.update(skill.casefold() for skill in skill_matches)
        role_matches = query_roles.intersection(set(item.roles))

        if not query_terms:
            score = 0.10 if (skill_matches or role_matches) else 0.0
        else:
            denominator = float(len(query_terms))
            term_coverage = len(query_terms.intersection(document_terms)) / denominator
            title_coverage = len(query_terms.intersection(title_terms)) / denominator
            keyword_coverage = len(query_terms.intersection(keyword_terms)) / denominator
            content_coverage = len(query_terms.intersection(content_terms)) / denominator
            skill_coverage = (
                len(direct_skill_matches) + (0.35 * len(related_skill_matches))
            ) / max(len(query_skills), 1)
            role_coverage = len(role_matches) / max(len(query_roles), 1)
            score = (
                0.30 * term_coverage
                + 0.25 * title_coverage
                + 0.15 * keyword_coverage
                + 0.10 * content_coverage
                + 0.15 * skill_coverage
                + 0.05 * role_coverage
            )
            if query_skills and not skill_matches and not role_matches:
                score *= 0.45

        exact_title = bool(set(tokenize(item.title)).issubset(query_terms))
        if exact_title:
            score += 0.15
        if item.category is KnowledgeCategory.ROLE and role_matches and exact_title:
            score += 0.15
        if item.category is KnowledgeCategory.ROLE and skill_matches and "backend" in query_terms:
            score += 0.15
        if item.category is KnowledgeCategory.SKILL and direct_skill_matches:
            score += 0.10
        if "interview" in query_terms:
            if item.category is KnowledgeCategory.INTERVIEW_TOPIC:
                score += 0.15
            elif item.category is KnowledgeCategory.ROLE:
                score *= 0.50
        if "resume" in query_terms and item.category is KnowledgeCategory.RESUME_GUIDANCE:
            score += 0.15
        return min(round(score, 6), 1.0), sorted(matched_terms)

    def _query_terms(self, query: str) -> Set[str]:
        return {
            term
            for term in tokenize(query)
            if term not in TEXT_STOP_WORDS and len(term) > 1
        }

    def _roles_from_text(self, query: str) -> Set[str]:
        query_terms = self._query_terms(query)
        query_text = normalize_text(query).casefold()
        roles = set()
        for title in ROLE_DEFINITIONS:
            title_terms = set(self._query_terms(title))
            slug = title.lower().replace("/", " ")
            if title.casefold() in query_text or slug.casefold() in query_text:
                roles.add(title)
            elif len(query_terms.intersection(title_terms)) >= max(2, len(title_terms) // 2):
                roles.add(canonical_role_reference(title))
        return roles

    def _item_skills(self, item: KnowledgeItem) -> Set[str]:
        skills = set(item.related_skills)
        if item.category is KnowledgeCategory.SKILL:
            skills.add(item.title)
        return skills

    def _direct_skill_matches(self, item: KnowledgeItem, query_skills: Set[str]) -> Set[str]:
        if item.category is not KnowledgeCategory.SKILL:
            return set()
        return query_skills.intersection({item.title})
