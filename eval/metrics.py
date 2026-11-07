from typing import Optional
from pydantic import BaseModel, Field

class EvaluationMetrics(BaseModel):
    """Standardized metrics recorded during benchmark evaluation."""
    task_id: str = Field(
        description="Unique ID of the benchmark task evaluated"
    )
    domain_family: str = Field(
        description="IPC domain family, e.g., 'blocksworld', 'logistics', 'rovers'"
    )
    task_type: str = Field(
        description="Lifecycle task category: 'ELICITATION', 'SYNTHETIC_FAULT_REPAIR'"
    )
    agent_type: str = Field(
        description="Evaluated agent architecture: 'ZERO_SHOT', 'UNSTRUCTURED_RETRY', 'CLOSED_LOOP_AST_AGENT', etc."
    )
    
    # -------------------------------------------------------------
    # 1. Operational Verification Metrics (Multi-Stage Funnel)
    # -------------------------------------------------------------
    is_syntax_valid: bool = Field(
        default=False,
        description="Stage 1: Syntax Valid: VAL parser and type-checker pass"
    )
    is_solvable: bool = Field(
        default=False,
        description="Stage 2a: Fast Downward found a valid plan within search budget"
    )
    planner_timeout: bool = Field(
        default=False,
        description="Stage 2b: Search budget exhausted without proving unsolvability"
    )
    executability_valid: bool = Field(
        default=False,
        description="Stage 2c: Internal Consistency: VAL(D_gen, P_gen, pi_gen) == PASS"
    )
    feasibility_valid: bool = Field(
        default=False,
        description="Stage 3a: Forward Soundness: VAL(D_gold, P_gold, pi_gen) == PASS"
    )
    interpretability_valid: bool = Field(
        default=False,
        description="Stage 3b: Inverse Completeness: VAL(D_gen, P_gold, pi_gold) == PASS"
    )
    semantic_soundness: bool = Field(
        default=False,
        description="Stage 3c: Non-Circular Semantic Transfer: feasibility_valid and interpretability_valid"
    )
    e2e_gate_success: bool = Field(
        default=False,
        description="Strict E2E Gate: is_syntax_valid and is_solvable and executability_valid and semantic_soundness"
    )
    problems_evaluated: int = Field(
        default=1,
        description="Total number of ground-truth problem instances evaluated for this task"
    )
    problems_passed: int = Field(
        default=0,
        description="Number of ground-truth problem instances passing Soundness and Completeness"
    )

    # -------------------------------------------------------------
    # 2. Hierarchical Fault Localization Diagnostics
    # -------------------------------------------------------------
    top1_element: Optional[str] = Field(
        default=None,
        description="Diagnosed AST element (Action Schema, 'types', or 'predicates')"
    )
    top1_repair_op: Optional[str] = Field(
        default=None,
        description="Diagnosed Causal Repair Operation Type"
    )

    # -------------------------------------------------------------
    # 3. Plan Quality Metrics
    # -------------------------------------------------------------
    plan_length: Optional[int] = Field(
        default=None,
        description="|Plan|: Total sequential action steps in verified plan"
    )
    plan_cost: Optional[float] = Field(
        default=None,
        description="Total action cost of verified plan"
    )
    search_time: Optional[float] = Field(
        default=None,
        description="Planner search time in seconds"
    )

    # -------------------------------------------------------------
    # 4. Computational Efficiency & Telemetry
    # -------------------------------------------------------------
    iterations_used: int = Field(
        default=1,
        description="k: Discrete repair iterations consumed"
    )
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total wall-clock runtime in seconds"
    )
    total_tokens: int = Field(
        default=0,
        description="Total LLM prompt + completion tokens consumed"
    )
    estimated_cost_usd: float = Field(
        default=0.0,
        description="Estimated API cost in USD"
    )
    error_summary: Optional[str] = Field(
        default=None,
        description="Summary of remaining oracle diagnostic error if verification failed"
    )

    @property
    def is_plan_valid(self) -> bool:
        return self.is_solvable

    @property
    def e2e_success(self) -> bool:
        """
        Canonical Tri-Criteria End-to-End Success Gate:
        True ONLY if:
          1. Syntax validation passes (VAL parser and type-checker)
          2. Planner solvability passes (Fast Downward found plan)
          3. Executability passes (VAL certifies generated plan on generated domain)
          4. Feasibility passes (VAL certifies generated plan on ground-truth domain)
          5. Interpretability passes (VAL certifies ground-truth plan on generated domain)
        """
        return self.e2e_gate_success
