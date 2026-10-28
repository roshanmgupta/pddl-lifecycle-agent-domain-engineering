from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class EvaluationMetrics(BaseModel):
    """
    Standardized metrics recorded during a single benchmark task evaluation pass.
    Derives from Classical PDDL 2.1 Formal Semantics & Symbolic Oracles (VAL + Fast Downward).
    Literature Grounding:
      - SVR: Fox & Long (2003), VAL Parser
      - TPV: Howey, Long, & Fox (2004), VAL Plan Validator
      - Cov_ref: Helmert (2006), IPC Reference Problem Solvability Coverage
      - Macro Structural F1 & ARE: Oswald et al. (ICAPS 2024)
      - STRIPS Component F1: Aineto, Jiménez, & Onaindia (JAIR 2022)
    """
    task_id: str = Field(
        description="Unique ID of the benchmark task evaluated"
    )
    domain_family: str = Field(
        description="IPC domain family, e.g., 'blocksworld', 'logistics', 'rovers'"
    )
    task_type: str = Field(
        description="Lifecycle task category: 'ELICITATION', 'SYNTHETIC_FAULT_REPAIR', 'DOMAIN_EVOLUTION'"
    )
    agent_type: str = Field(
        description="Evaluated agent architecture: 'ZERO_SHOT', 'UNSTRUCTURED_RETRY', 'CLOSED_LOOP_AST_AGENT', etc."
    )
    
    # -------------------------------------------------------------
    # 1. Operational Verification Metrics (Multi-Stage Funnel)
    # -------------------------------------------------------------
    svr_syntax_valid_rate: float = Field(
        default=0.0,
        description="Stage 1: SVR: 1.0 if domain and problem pass VAL syntactic and typing parser; else 0.0"
    )
    is_solvable: bool = Field(
        default=False,
        description="Stage 2a: Fast Downward found a valid plan within search budget"
    )
    planner_timeout: bool = Field(
        default=False,
        description="Stage 2b: Search budget exhausted (30s) without proving unsolvability"
    )
    executability_valid: bool = Field(
        default=False,
        description="Stage 2c: Internal Consistency / Self-Certification: VAL(D_gen, P_gen, pi_gen) == PASS"
    )
    tpv_target_plan_valid: bool = Field(
        default=False,
        description="TPV: True iff Fast Downward exits 0 and VAL certifies plan execution validity on target task; else False"
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
        description="Strict E2E Gate: SVR and is_solvable and executability_valid and semantic_soundness"
    )
    cov_ref_coverage_rate: Optional[float] = Field(
        default=None,
        description="Cov_ref: Reference Suite Coverage percentage (0.0 to 100.0) on baseline benchmark suite"
    )
    reference_instances_passed: Optional[int] = Field(
        default=None,
        description="Passed instances in reference problem suite"
    )
    reference_instances_total: Optional[int] = Field(
        default=None,
        description="Total instances in reference problem suite"
    )

    # -------------------------------------------------------------
    # 2. Structural Reconstruction Metrics (Oswald 2024 / Aineto 2022)
    # -------------------------------------------------------------
    macro_structural_f1: Optional[float] = Field(
        default=None,
        description="Macro Structural F1 via Kuhn-Munkres maximum weight bipartite matching"
    )
    precondition_f1: Optional[float] = Field(
        default=None,
        description="Pre_F1: F1 score on precondition predicate sets across aligned operators"
    )
    add_effect_f1: Optional[float] = Field(
        default=None,
        description="Add_F1: F1 score on add-effect predicate sets across aligned operators"
    )
    delete_effect_f1: Optional[float] = Field(
        default=None,
        description="Del_F1: F1 score on delete-effect predicate sets across aligned operators"
    )
    action_f1: Optional[float] = Field(
        default=None,
        description="Action_F1: Harmonic mean of operator precision and recall (Level 1 AST Element F1)"
    )
    parameter_arity_match: Optional[float] = Field(
        default=None,
        description="Level 2: Parameter count and signature alignment rate"
    )

    # -------------------------------------------------------------
    # 2b. Hierarchical Multi-Granular Fault Localization (H-MGFL) Metrics
    # -------------------------------------------------------------
    fla_top1: Optional[bool] = Field(
        default=None,
        description="Level 1: Top-1 Fault Localization Accuracy against gold fault element"
    )
    fla_top3: Optional[bool] = Field(
        default=None,
        description="Level 1: Top-3 Fault Localization Accuracy against gold fault element"
    )
    fla_mrr: Optional[float] = Field(
        default=None,
        description="Level 1: Mean Reciprocal Rank (MRR) of gold fault element"
    )
    top1_element: Optional[str] = Field(
        default=None,
        description="Level 1: Top-1 diagnosed AST element (Action Schema, 'types', or 'predicates')"
    )
    top1_repair_op: Optional[str] = Field(
        default=None,
        description="Level 2: Top-1 diagnosed Causal Repair Operation Type"
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
    # 4. Computational & Diagnostic Efficiency
    # -------------------------------------------------------------
    iterations_used: int = Field(
        default=1,
        description="k: Discrete repair iterations consumed in {0, ..., K_max}"
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
    behavioral_code: Optional[str] = Field(
        default=None,
        description="Behavioral classification code (e.g., E.1, E.2, E.B, E.T, E.S, S.1, S.2, S.T, S.S)"
    )
    error_summary: Optional[str] = Field(
        default=None,
        description="Summary of remaining oracle diagnostic error if verification failed"
    )

    @property
    def is_syntax_valid(self) -> bool:
        return self.svr_syntax_valid_rate >= 1.0

    @property
    def is_plan_valid(self) -> bool:
        return self.is_solvable

    @property
    def e2e_success(self) -> bool:
        if self.e2e_gate_success:
            if self.cov_ref_coverage_rate is not None:
                return self.cov_ref_coverage_rate >= 100.0
            return True
        if self.cov_ref_coverage_rate is not None:
            return self.tpv_target_plan_valid and (self.cov_ref_coverage_rate >= 100.0)
        return self.tpv_target_plan_valid
