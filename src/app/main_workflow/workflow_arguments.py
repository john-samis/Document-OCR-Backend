"""
Model the arguments to the workflow
 - pdf -> jpg -> ocr -> text + math/OMML -> docx

Keep extensible for local running and exapnading for

"""

from dataclasses import dataclass, field


@dataclass
class WorkflowArguments:
    input_filename: str
    output_filename: str



    
