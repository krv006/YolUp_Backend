"""Fan va ko'nikma profillari — RJalol'ning AI-home-checker (AI-home-checker-multi-model-qwen-gemini-, `prompts.py`,
2026-11-21, `main`) dan OLINGAN: har fan uchun rol, mavzular, tekshirish maqsadlari, xato turkumlari va ball mezoni;
til fanlari uchun reading/writing/listening/speaking shablonlari.

Ma'lumot RJalol'niki, shu yerda o'zgartirilmagan holda turadi (yangilanganda `prompts.py` dan shu qismni qayta ko'chiring).
Bizning tomonimiz: `ai_prompt.py` shu profillardan baholovchi ko'rsatmasini yig'adi (`ai_grader.py` ishlatadi).
"""
from dataclasses import dataclass
from typing import List


@dataclass
class SubjectProfile:
    key: str
    label: str                 # shown in the UI dropdown
    role: str                  # "You are an expert ... "
    topics: List[str]          # typical topics for the CONTEXT section
    objectives: List[str]      # what to check for, per question
    error_categories: List[str]
    score_rubric: str          # multi-line description of what scores mean
    concept_word: str = "concept"  # e.g. "mathematical concept", "grammar rule", "argument"


MATH = SubjectProfile(
    key="math",
    label="Mathematics",
    role="an expert Mathematics Teacher, University Lecturer, and Assessment Specialist with over 20 years of experience evaluating student assignments",
    topics=[
        "Algebra", "Calculus", "Geometry", "Probability", "Statistics",
        "Linear Algebra", "Differential Equations", "Discrete Mathematics",
        "Mathematical Logic", "Numerical Analysis", "Any university-level mathematics",
    ],
    objectives=[
        "Read the student's solution carefully.",
        "Understand the student's reasoning.",
        "Determine whether the final answer is correct.",
        "Check every intermediate step.",
        "Identify mathematical mistakes.",
        "Identify arithmetic mistakes.",
        "Identify notation mistakes.",
        "Identify missing steps.",
        "Identify logical inconsistencies.",
        "Evaluate mathematical rigor.",
    ],
    error_categories=[
        "Conceptual Error", "Calculation Error", "Algebra Error", "Derivative Error",
        "Integration Error", "Notation Error", "Unit Error", "Formula Error",
        "Logic Error", "Missing Step", "Incorrect Assumption", "Arithmetic Error",
        "Sign Error", "Formatting Issue",
    ],
    score_rubric=(
        "100 = perfect\n"
        "90-99 = minor notation issues\n"
        "70-89 = mostly correct but contains mathematical mistakes\n"
        "40-69 = partially correct\n"
        "1-39 = major conceptual misunderstanding\n"
        "0 = no valid attempt"
    ),
    concept_word="mathematical concept",
)

PHYSICS = SubjectProfile(
    key="physics",
    label="Physics",
    role="an expert Physics Teacher and University Lecturer with over 20 years of experience evaluating student problem sets",
    topics=[
        "Mechanics", "Thermodynamics", "Electromagnetism", "Optics", "Waves",
        "Modern Physics", "Quantum Mechanics", "Kinematics and Dynamics",
        "Circuits", "Any university-level physics",
    ],
    objectives=[
        "Read the student's solution carefully.",
        "Understand the student's physical reasoning and setup.",
        "Determine whether the final answer and its units are correct.",
        "Check every intermediate step and equation used.",
        "Identify conceptual physics mistakes.",
        "Identify calculation/arithmetic mistakes.",
        "Identify unit and dimensional-analysis mistakes.",
        "Identify missing free-body diagrams or setup steps where relevant.",
        "Identify incorrect assumptions about the physical system.",
        "Evaluate rigor and clarity of the derivation.",
    ],
    error_categories=[
        "Conceptual Error", "Calculation Error", "Unit Error", "Formula Error",
        "Sign Error", "Missing Step", "Incorrect Assumption", "Diagram Error",
        "Significant Figures Error", "Logic Error", "Formatting Issue",
    ],
    score_rubric=(
        "100 = perfect, correct units and reasoning\n"
        "90-99 = minor unit or rounding issues\n"
        "70-89 = mostly correct physics but contains calculation mistakes\n"
        "40-69 = partially correct setup or reasoning\n"
        "1-39 = major conceptual misunderstanding of the physics involved\n"
        "0 = no valid attempt"
    ),
    concept_word="physics concept",
)

CHEMISTRY = SubjectProfile(
    key="chemistry",
    label="Chemistry",
    role="an expert Chemistry Teacher and University Lecturer with over 20 years of experience evaluating student assignments",
    topics=[
        "Stoichiometry", "Chemical Equilibrium", "Thermochemistry", "Kinetics",
        "Organic Chemistry", "Acid-Base Chemistry", "Electrochemistry",
        "Atomic Structure", "Periodic Trends", "Any university-level chemistry",
    ],
    objectives=[
        "Read the student's solution carefully.",
        "Understand the student's chemical reasoning.",
        "Determine whether the final answer, units, and significant figures are correct.",
        "Check every intermediate calculation and balanced equation.",
        "Identify conceptual chemistry mistakes.",
        "Identify stoichiometry/calculation mistakes.",
        "Identify errors in chemical formulas, equations, or nomenclature.",
        "Identify missing steps (e.g. unbalanced equations, missing units).",
        "Identify incorrect assumptions.",
        "Evaluate rigor and clarity of the explanation.",
    ],
    error_categories=[
        "Conceptual Error", "Calculation Error", "Stoichiometry Error", "Formula Error",
        "Nomenclature Error", "Unit Error", "Unbalanced Equation", "Missing Step",
        "Incorrect Assumption", "Significant Figures Error", "Formatting Issue",
    ],
    score_rubric=(
        "100 = perfect, correctly balanced and reasoned\n"
        "90-99 = minor unit, rounding, or nomenclature issues\n"
        "70-89 = mostly correct chemistry but contains calculation mistakes\n"
        "40-69 = partially correct reasoning or setup\n"
        "1-39 = major conceptual misunderstanding of the chemistry involved\n"
        "0 = no valid attempt"
    ),
    concept_word="chemistry concept",
)

BIOLOGY = SubjectProfile(
    key="biology",
    label="Biology",
    role="an expert Biology Teacher and University Lecturer with over 20 years of experience evaluating student assignments",
    topics=[
        "Cell Biology", "Genetics", "Evolution", "Ecology", "Physiology",
        "Molecular Biology", "Microbiology", "Anatomy", "Any university-level biology",
    ],
    objectives=[
        "Read the student's answer carefully.",
        "Understand the student's biological reasoning.",
        "Determine whether the answer is scientifically accurate.",
        "Check that terminology and processes are described correctly.",
        "Identify conceptual/factual biology mistakes.",
        "Identify missing steps in a described process or pathway.",
        "Identify incorrect assumptions about biological mechanisms.",
        "Evaluate clarity, completeness, and use of correct terminology.",
    ],
    error_categories=[
        "Conceptual Error", "Factual Error", "Terminology Error", "Missing Step",
        "Incorrect Assumption", "Logic Error", "Incomplete Explanation", "Formatting Issue",
    ],
    score_rubric=(
        "100 = perfect, scientifically accurate and complete\n"
        "90-99 = minor terminology issues\n"
        "70-89 = mostly correct but contains factual or conceptual mistakes\n"
        "40-69 = partially correct understanding\n"
        "1-39 = major conceptual misunderstanding\n"
        "0 = no valid attempt"
    ),
    concept_word="biological concept",
)

COMPUTER_SCIENCE = SubjectProfile(
    key="computer_science",
    label="Computer Science / Programming",
    role="an expert Computer Science Instructor and University Lecturer with over 20 years of experience evaluating student code and CS assignments",
    topics=[
        "Algorithms", "Data Structures", "Complexity Analysis", "Programming Logic",
        "Object-Oriented Design", "Databases", "Discrete Mathematics for CS",
        "Any university-level computer science coursework or code submission",
    ],
    objectives=[
        "Read the student's code or written answer carefully.",
        "Understand the student's algorithmic approach and logic.",
        "Determine whether the solution is correct and would work on typical/edge-case inputs.",
        "Check time and space complexity where relevant.",
        "Identify logic errors and bugs.",
        "Identify inefficient or incorrect algorithm choices.",
        "Identify missing edge-case handling.",
        "Identify style, naming, or documentation issues.",
        "Evaluate overall code/solution quality and clarity.",
    ],
    error_categories=[
        "Logic Error", "Algorithm Error", "Complexity Error", "Edge Case Missing",
        "Syntax Error", "Style Issue", "Incorrect Assumption", "Missing Step",
        "Inefficient Solution", "Formatting Issue",
    ],
    score_rubric=(
        "100 = correct, efficient, and well-structured\n"
        "90-99 = correct but minor style/efficiency issues\n"
        "70-89 = mostly correct but contains logic or edge-case bugs\n"
        "40-69 = partially correct approach\n"
        "1-39 = major misunderstanding of the required algorithm/logic\n"
        "0 = no valid attempt"
    ),
    concept_word="CS concept",
)

ESSAY = SubjectProfile(
    key="essay",
    label="Essay / Literature",
    role="an expert Language Arts and Literature Teacher with over 20 years of experience evaluating student essays and written analysis",
    topics=[
        "Argumentative Essays", "Literary Analysis", "Narrative Writing",
        "Persuasive Writing", "Thesis Development", "Textual Evidence and Citation",
        "Any secondary or university-level writing assignment",
    ],
    objectives=[
        "Read the student's essay carefully.",
        "Understand the student's thesis and argument.",
        "Determine whether the thesis is clear and well-supported.",
        "Check that evidence is used correctly and cited appropriately.",
        "Identify weaknesses in structure, organization, or transitions.",
        "Identify grammar, punctuation, and style issues.",
        "Identify unclear, unsupported, or logically inconsistent claims.",
        "Evaluate overall clarity, voice, and persuasiveness.",
    ],
    error_categories=[
        "Weak Thesis", "Unsupported Claim", "Structure Issue", "Grammar Error",
        "Punctuation Error", "Citation Error", "Logic Error", "Clarity Issue",
        "Style Issue", "Missing Evidence",
    ],
    score_rubric=(
        "100 = excellent thesis, argument, evidence, and mechanics\n"
        "90-99 = strong essay with minor style or grammar issues\n"
        "70-89 = solid essay with some structural or evidentiary weaknesses\n"
        "40-69 = underdeveloped argument or significant organizational issues\n"
        "1-39 = thesis unclear or largely unsupported\n"
        "0 = no valid attempt"
    ),
    concept_word="writing or argumentation concept",
)

HISTORY = SubjectProfile(
    key="history",
    label="History / Social Studies",
    role="an expert History and Social Studies Teacher with over 20 years of experience evaluating student essays and short-answer responses",
    topics=[
        "Historical Analysis", "Cause and Effect", "Primary Source Interpretation",
        "Comparative History", "Political and Social Movements",
        "Any secondary or university-level history/social studies assignment",
    ],
    objectives=[
        "Read the student's answer carefully.",
        "Understand the student's historical argument or interpretation.",
        "Determine whether facts, dates, and events are accurate.",
        "Check that evidence and sources are used and interpreted correctly.",
        "Identify factual errors.",
        "Identify weaknesses in argument, causation, or context.",
        "Identify missing important evidence or perspectives.",
        "Evaluate clarity and quality of historical reasoning.",
    ],
    error_categories=[
        "Factual Error", "Chronology Error", "Weak Argument", "Missing Context",
        "Source Misinterpretation", "Logic Error", "Missing Evidence", "Clarity Issue",
    ],
    score_rubric=(
        "100 = accurate, well-argued, and well-supported\n"
        "90-99 = strong response with very minor factual gaps\n"
        "70-89 = mostly accurate with some argument or evidence weaknesses\n"
        "40-69 = partially accurate or underdeveloped reasoning\n"
        "1-39 = largely inaccurate or unsupported\n"
        "0 = no valid attempt"
    ),
    concept_word="historical concept",
)

GENERAL = SubjectProfile(
    key="general",
    label="General / Other (type a subject below)",
    role="an expert Teacher, University Lecturer, and Assessment Specialist with over 20 years of experience evaluating student assignments across many subjects",
    topics=["Any topic the teacher specifies for this assignment."],
    objectives=[
        "Read the student's answer carefully.",
        "Understand the student's reasoning and approach.",
        "Determine whether the answer is correct or well-argued for this subject.",
        "Check every intermediate step or supporting point.",
        "Identify factual, conceptual, or logical mistakes.",
        "Identify missing steps or missing evidence.",
        "Evaluate overall rigor, clarity, and completeness.",
    ],
    error_categories=[
        "Conceptual Error", "Factual Error", "Logic Error", "Missing Step",
        "Incorrect Assumption", "Clarity Issue", "Formatting Issue",
    ],
    score_rubric=(
        "100 = perfect\n"
        "90-99 = minor issues only\n"
        "70-89 = mostly correct but contains notable mistakes\n"
        "40-69 = partially correct\n"
        "1-39 = major misunderstanding\n"
        "0 = no valid attempt"
    ),
    concept_word="concept",
)

SUBJECTS = {
    s.key: s for s in [
        MATH, PHYSICS, CHEMISTRY, BIOLOGY, COMPUTER_SCIENCE, ESSAY, HISTORY, GENERAL
    ]
}
DEFAULT_SUBJECT_KEY = MATH.key


# ---------------------------------------------------------------------------
# Language skill assessment (English / Russian / Turkish x Writing / Reading
# / Listening / Speaking). Unlike the fixed subjects above, these profiles
# are built dynamically from (language, skill) so adding a 4th language
# later only means adding one line to LANGUAGES.
# ---------------------------------------------------------------------------
LANGUAGES = {
    "english": "English",
    "russian": "Russian",
    "turkish": "Turkish",
    "french": "French",
    "german": "German",
    "uzbek": "Uzbek",
}
DEFAULT_LANGUAGE_KEY = "english"

# Each skill template describes what to check, what counts as a mistake,
# and what the uploaded file/recording actually represents for that skill.
SKILL_TEMPLATES = {
    "writing": {
        "label": "Writing",
        "role_suffix": "Writing Skills",
        "submission_note": (
            "The submission is a piece of student writing (essay, letter, email, "
            "report, or short answer) submitted as PDF, image, or Word document."
        ),
        "topics": [
            "Essays", "Letters and Emails", "Reports", "Short Answer Responses",
            "Paragraph and Sentence Structure", "CEFR-level Writing Tasks (A1-C2)",
        ],
        "objectives": [
            "Read the student's written response carefully.",
            "Determine whether the task/prompt was fully addressed (task achievement).",
            "Check grammar, verb tenses, and sentence structure.",
            "Check vocabulary range and appropriateness for the level.",
            "Check spelling and punctuation.",
            "Evaluate coherence, cohesion, and paragraph organization.",
            "Evaluate overall register and tone for the task.",
        ],
        "error_categories": [
            "Grammar Error", "Verb Tense Error", "Vocabulary Error", "Spelling Error",
            "Punctuation Error", "Coherence Issue", "Task Achievement Issue",
            "Register/Tone Issue", "Word Order Error",
        ],
        "score_rubric": (
            "100 = fully addresses the task with excellent grammar, vocabulary, and coherence\n"
            "90-99 = very strong response with very minor language slips\n"
            "70-89 = task mostly achieved but contains noticeable grammar/vocabulary errors\n"
            "40-69 = partially addresses the task or has frequent language errors\n"
            "1-39 = task barely addressed or overwhelmed by language errors\n"
            "0 = no valid attempt"
        ),
        "concept_word": "grammar or vocabulary rule",
    },
    "reading": {
        "label": "Reading",
        "role_suffix": "Reading Comprehension",
        "submission_note": (
            "The submission is a completed reading-comprehension worksheet: a "
            "passage plus the student's answers to comprehension questions, "
            "submitted as PDF, image, or Word document."
        ),
        "topics": [
            "Reading Comprehension Passages", "Vocabulary in Context",
            "Inference Questions", "Main Idea and Detail Questions",
            "True/False/Not Given Questions", "CEFR-level Reading Tasks (A1-C2)",
        ],
        "objectives": [
            "Read the passage and the student's answers carefully.",
            "Determine whether each answer is factually/textually correct.",
            "Check whether the student correctly identified the main idea and details.",
            "Check whether inference-based answers are logically supported by the text.",
            "Identify misunderstandings of vocabulary in context.",
            "Identify answers that misread or ignore part of the passage.",
        ],
        "error_categories": [
            "Comprehension Error", "Incorrect Answer", "Missing Detail",
            "Inference Error", "Vocabulary Misunderstanding", "Misread Question",
        ],
        "score_rubric": (
            "100 = all answers correct and well-supported by the text\n"
            "90-99 = almost all correct, one very minor slip\n"
            "70-89 = mostly correct but some comprehension or detail errors\n"
            "40-69 = several answers incorrect or unsupported\n"
            "1-39 = most answers incorrect, little understanding shown\n"
            "0 = no valid attempt"
        ),
        "concept_word": "reading strategy",
    },
    "listening": {
        "label": "Listening",
        "role_suffix": "Listening Comprehension",
        "submission_note": (
            "The submission is the student's completed listening-comprehension "
            "answer sheet (submitted as PDF, image, or Word document), based on "
            "audio material the student listened to separately. If an audio file "
            "is attached instead, use it as the source material the questions "
            "are based on."
        ),
        "topics": [
            "Listening Comprehension Worksheets", "Note-taking Tasks", "Dictation",
            "Gap-fill Listening Exercises", "CEFR-level Listening Tasks (A1-C2)",
        ],
        "objectives": [
            "Review the student's answers to the listening exercise carefully.",
            "Determine whether each answer matches what was almost certainly said or asked.",
            "Check spelling of any dictated words or names.",
            "Identify answers that suggest a mishearing or misunderstanding.",
            "Identify missing or blank answers.",
        ],
        "error_categories": [
            "Comprehension Error", "Incorrect Answer", "Spelling Error",
            "Missed Detail", "Blank Answer", "Misheard Word",
        ],
        "score_rubric": (
            "100 = all answers correct, well-spelled and complete\n"
            "90-99 = almost all correct, very minor spelling slip\n"
            "70-89 = mostly correct but a few details missed or misheard\n"
            "40-69 = several answers incorrect or incomplete\n"
            "1-39 = most answers incorrect, little comprehension shown\n"
            "0 = no valid attempt"
        ),
        "concept_word": "listening strategy",
    },
    "speaking": {
        "label": "Speaking",
        "role_suffix": "Speaking Skills",
        "submission_note": (
            "The submission is an AUDIO RECORDING of the student speaking "
            "(answering a prompt, describing a picture, having a conversation, "
            "or giving a short presentation). Listen to the recording directly."
        ),
        "topics": [
            "Picture Description", "Conversational Response", "Short Presentations",
            "Role-play Dialogues", "CEFR-level Speaking Tasks (A1-C2)",
        ],
        "objectives": [
            "Listen to the student's spoken response carefully.",
            "Transcribe (briefly, in your analysis) what the student actually said.",
            "Determine whether the task/prompt was fully addressed.",
            "Evaluate pronunciation and intelligibility.",
            "Evaluate fluency and pace (hesitations, self-corrections, pauses).",
            "Check grammar and sentence structure used in speech.",
            "Check vocabulary range used in speech.",
            "Evaluate intonation, stress, and overall naturalness.",
        ],
        "error_categories": [
            "Pronunciation Error", "Fluency Issue", "Grammar Error", "Vocabulary Error",
            "Intonation/Stress Issue", "Task Achievement Issue", "Hesitation/Filler Overuse",
        ],
        "score_rubric": (
            "100 = fully addresses the task with excellent pronunciation, fluency, and grammar; "
            "zero noticeable errors\n"
            "90-99 = very strong response with at most one truly trivial slip; still counts as an error\n"
            "70-89 = task mostly achieved but contains clear pronunciation, grammar, vocabulary, "
            "or fluency issues -- if you listed 2+ items in \"mistakes\", do not exceed this band\n"
            "40-69 = partially addresses the task, frequent errors, noticeable hesitation/filler "
            "overuse, or limited vocabulary that a listener would clearly notice\n"
            "1-39 = task barely addressed, very difficult to understand, or errors dominate the response\n"
            "0 = no valid attempt / no audio content detected\n\n"
            "IMPORTANT: A calm, confident, or fluent-sounding delivery does NOT by itself justify "
            "a high score. Count the actual pronunciation/grammar/vocabulary errors first, then pick "
            "the band that matches that count -- do not let overall impression override the count."
        ),
        "concept_word": "pronunciation or grammar pattern",
    },
}
DEFAULT_SKILL_KEY = "writing"


def build_language_profile(language_key: str, skill_key: str) -> SubjectProfile:
    """Dynamically builds a SubjectProfile for a given (language, skill) pair."""
    language_name = LANGUAGES.get(language_key, language_key.title())
    skill = SKILL_TEMPLATES.get(skill_key, SKILL_TEMPLATES[DEFAULT_SKILL_KEY])

    return SubjectProfile(
        key=f"lang_{language_key}_{skill_key}",
        label=f"{language_name} - {skill['label']}",
        role=(
            f"an expert {language_name} Language Teacher and Examiner with over 20 "
            f"years of experience assessing student {skill['role_suffix']}"
        ),
        topics=skill["topics"],
        objectives=skill["objectives"],
        error_categories=skill["error_categories"],
        score_rubric=skill["score_rubric"],
        concept_word=skill["concept_word"],
    )
