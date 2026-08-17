from app.prompts.conclusion_synthesis import CONCLUSION_SYNTHESIS_SYSTEM_PROMPT
from app.prompts.contradiction_detection import CONTRADICTION_DETECTION_SYSTEM_PROMPT
from app.prompts.finding_extraction import FINDING_EXTRACTION_SYSTEM_PROMPT
from app.prompts.question_decomposition import DECOMPOSITION_SYSTEM_PROMPT

PROMPT_VERSIONS = {
    "decomposition": "v2",
    "finding_extraction": "v2",
    "contradiction_detection": "v1",
    "conclusion_synthesis": "v2",
}
