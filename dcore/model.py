"""The deliberation file: what Claude writes, and what every script reads.

One file per deliberation (`claims/<id>/claims.json`). It holds the
front half of the core (collected and normalised claims, the research, each
side's case, values, actions) in a form a person can read and edit by hand.
`dcore.compile` turns it into argkit graphs for the back half.

Vocabulary, kept close to the Deliberation Core doc:

  question     the claim as it was heard, plus its plain, neutral restatement
  sub_claim    one checkable part of the question (fact, interpretation, intent)
  argument     one side's case on a sub-claim: reasoning over evidence
  evidence     a single checkable statement, backed by one or more sources
  attack       a typed challenge from one argument onto another
  preference   a stated judgment that one argument outweighs another
  priority     a value people weigh; never true or false
  action       a step both sides could accept that would move things forward
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from argkit.schema import AttackType, CurationStatus


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceKind(str, Enum):
    COURT = "court"          # a judgment, order, or court report
    OFFICIAL = "official"    # a government or ECI document or statement
    RESEARCH = "research"    # an academic paper or dataset
    NEWS = "news"            # reporting by a news outlet
    PARTY = "party"          # a party's or campaigner's own claim


class SubClaimKind(str, Enum):
    FACT = "fact"                    # did this happen?
    INTERPRETATION = "interpretation"  # what does it mean or cause?
    INTENT = "intent"                # why did someone do it?


class Stance(str, Enum):
    SUPPORTS = "supports"
    CHALLENGES = "challenges"


class Role(str, Enum):
    CASE = "case"            # a direct case for or against the sub-claim
    OBJECTION = "objection"  # only challenges another argument's reasoning or evidence


class Source(_Strict):
    id: str
    title: str
    publisher: str
    url: str
    date: str = Field(description="ISO date of publication, as precise as known")
    kind: SourceKind


class Question(_Strict):
    original: str = Field(description="the claim exactly as it was brought in")
    plain: str = Field(description="a neutral restatement that both sides would accept as fair")
    reframe_note: str = Field(description="what changed from the original wording, and why")


class SubClaim(_Strict):
    id: str
    text: str
    kind: SubClaimKind
    merged_from: list[str] = Field(default_factory=list,
                                   description="other wordings of this claim that were merged into it")
    settle_by: str = Field(description="what evidence or event would settle this part")


class Evidence(_Strict):
    id: str
    text: str
    sources: list[str]


class Argument(_Strict):
    id: str
    sub_claim: str
    stance: Stance
    role: Role = Field(default=Role.CASE, description=(
        "an objection only acts through its attacks; it does not count toward the "
        "sub-claim's signal on its own"))
    title: str
    reasoning: str = Field(description="the inference: why the evidence bears on the sub-claim")
    evidence: list[Evidence]
    status: CurationStatus = CurationStatus.CANDIDATE
    check_note: str | None = Field(default=None, description="what verified or rejected it")


class Attack(_Strict):
    id: str
    source: str = Field(description="attacking argument id")
    target: str = Field(description="attacked argument id")
    type: AttackType
    target_evidence: str | None = Field(default=None, description="required for undermine")
    note: str


class Preference(_Strict):
    id: str
    preferred: str
    over: str
    rationale: str


class Priority(_Strict):
    id: str
    text: str
    emphasised_by: str = Field(description="who tends to stress it, described without judging them")


class Action(_Strict):
    id: str
    text: str
    settles: list[str] = Field(description="sub-claim ids this would help settle")
    why_both_sides: str
    who: str


class Generation(_Strict):
    generator: str = Field(description="who drafted it, e.g. 'claude (deliberate skill)'")
    cross_checker: str | None = None
    created_at: str = Field(description="ISO timestamp; supplied, never now(), so builds reproduce")


class Deliberation(_Strict):
    id: str
    version: int = 1
    based_on: str | None = Field(default=None, description="sha256 of the artifact this one extends")
    as_of: str
    question: Question
    sources: list[Source]
    sub_claims: list[SubClaim]
    arguments: list[Argument]
    attacks: list[Attack] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
    priorities: list[Priority] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    generation: Generation

    def argument(self, argument_id: str) -> Argument | None:
        return next((a for a in self.arguments if a.id == argument_id), None)

    def source(self, source_id: str) -> Source | None:
        return next((s for s in self.sources if s.id == source_id), None)

    def arguments_for(self, sub_claim_id: str) -> list[Argument]:
        return [a for a in self.arguments if a.sub_claim == sub_claim_id]
