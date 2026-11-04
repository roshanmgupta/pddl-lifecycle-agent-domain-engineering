from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class LifecycleTaskType(str, Enum):
    ELICITATION = "ELICITATION"
    SYNTHETIC_FAULT_REPAIR = "SYNTHETIC_FAULT_REPAIR"

class BenchmarkTask(BaseModel):
    """Schema for individual benchmark evaluation tasks in the canonical benchmark suite."""
    task_id: str = Field(
        description="Unique identifier for the benchmark task, e.g. 'blocksworld_repair_missing_precondition_01'"
    )
    domain_family: str = Field(
        description="IPC Domain family name: 'blocksworld', 'logistics', 'rovers', 'depots', 'satellite'"
    )
    task_type: LifecycleTaskType = Field(
        description="Lifecycle task category: ELICITATION or SYNTHETIC_FAULT_REPAIR"
    )
    title: str = Field(
        default="",
        description="Short human-readable summary of the evaluation scenario"
    )
    natural_language_requirements: str = Field(
        description="Natural language description of the domain rules or requirements"
    )
    initial_domain_pddl: Optional[str] = Field(
        default=None,
        description="Starting domain PDDL text containing a fault (for REPAIR)"
    )
    initial_problem_pddl: Optional[str] = Field(
        default=None,
        description="Starting problem PDDL text (for REPAIR)"
    )
    fault_category: Optional[str] = Field(
        default=None,
        description="Injected fault category for REPAIR tasks: 'SYNTAX_PARSE', 'TYPE_SIGNATURE', 'GROUNDING_UNSOLVABILITY'"
    )
    gold_fault_element: Optional[str] = Field(
        default=None,
        description="Exact ground-truth AST node/element that contains the fault (e.g., 'pick_up', 'clear', '(on ?x ?y)') for Top-k fault localization"
    )
    gold_fault_category: Optional[str] = Field(
        default=None,
        description="Formal ErrorCategory ground truth (e.g. 'ACTION_PRECONDITION_INSUFFICIENT')"
    )
    expected_repair_behavior: Optional[str] = Field(
        default=None,
        description="Description or specification of the intended behavior to be restored"
    )
    ground_truth_domain_pddl: str = Field(
        default="",
        description="Reference correct domain PDDL string for evaluation comparison"
    )
    ground_truth_problem_pddl: str = Field(
        default="",
        description="Reference correct problem PDDL string for evaluation comparison"
    )
