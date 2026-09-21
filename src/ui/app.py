"""Streamlit analyst dashboard for fraud investigations (offline-safe).

Run with: ``streamlit run src/ui/app.py``

Offline safety: ``streamlit`` and all ``src.agent`` imports happen lazily
inside functions, so ``python -m py_compile src/ui/app.py`` passes without
streamlit (or langgraph / TigerGraph) installed. With no live backend the
dashboard falls back to reading ``cases/outputs/*.json``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "cases" / "inputs"
OUTPUTS = ROOT / "cases" / "outputs"


def list_cases() -> list[str]:
    """Return sorted case_ids available under cases/inputs/."""
    if not INPUTS.exists():
        return []
    return sorted(p.stem for p in INPUTS.glob("case_*.json"))


def load_case_input(case_id: str) -> dict[str, Any]:
    """Load one cases/inputs/{case_id}.json (raises FileNotFoundError)."""
    path = INPUTS / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"case input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_saved_output(case_id: str) -> dict[str, Any]:
    """Load one cases/outputs/{case_id}.json (raises FileNotFoundError)."""
    path = OUTPUTS / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"saved output missing: {path} (run benchmark first)")
    return json.loads(path.read_text(encoding="utf-8"))


def run_live_investigation(case: dict[str, Any]) -> dict[str, Any]:
    """Run a live investigation for a case dict.

    Canonical path: ``src.agent.graph.investigate_case`` (LangGraph when
    available, orchestrator fallback otherwise) + ``src.agent.runner``
    ``to_output_json`` (full 16-field output). Older/alternate entry
    points (``run_single_case`` / ``run_case``) are tried as fallbacks so
    the UI keeps working across refactors. Never returns None; raises
    ValueError with a structured message on failure.
    """
    errors: list[str] = []
    try:
        from src.agent.graph import investigate_case
        from src.agent.runner import to_output_json

        state = investigate_case(dict(case))
        out = to_output_json(dict(case), state)
        if isinstance(out, dict):
            try:
                from src.agent.memory import find_similar_cases

                out["memory_matches"] = find_similar_cases(out)
            except Exception:
                pass
            return out
        raise ValueError("to_output_json returned non-dict output")
    except Exception as exc:
        errors.append(f"investigate_case path: {exc}")
    # -- fallbacks for alternate runner shapes --------------------------------
    try:
        from src.agent import runner as runner_mod

        for attr in ("run_single_case", "run_case"):
            fn = getattr(runner_mod, attr, None)
            if fn is None:
                continue
            try:
                try:
                    out = fn(dict(case))
                except TypeError:
                    out = fn(str(case.get("case_id", "")))
                if isinstance(out, dict):
                    out.pop("_memory_matches", None)
                    return out
            except Exception as exc2:
                errors.append(f"{attr}: {exc2}")
    except Exception as exc3:
        errors.append(f"runner fallback import: {exc3}")
    raise ValueError(f"live investigation failed: {'; '.join(errors)}")


def _verdict_color(verdict: str) -> str:
    return {"fraud": "red", "escalate": "orange", "legit": "green"}.get(
        str(verdict).lower(), "gray"
    )


def _render_output(st: Any, output: dict[str, Any], case: dict[str, Any]) -> None:
    """Render one investigation output with streamlit widgets."""
    verdict = output.get("verdict", "escalate")
    confidence = float(output.get("confidence", 0.0) or 0.0)
    risk = float(output.get("risk_score", 0.0) or 0.0)

    st.subheader(f"Verdict: :{_verdict_color(verdict)}[{verdict}]")
    c1, c2, c3 = st.columns(3)
    c1.metric("Risk score", f"{risk:.1f}")
    c2.metric("Confidence", f"{confidence:.3f}")
    c3.metric("Fraud pattern", str(output.get("fraud_pattern") or case.get("pattern")))

    # -- trigger / details -------------------------------------------------
    with st.expander("Trigger / case details", expanded=True):
        st.write(f"**Case:** {output.get('case_id', case.get('case_id'))}")
        st.write(f"**Trigger:** {output.get('trigger', case.get('description', 'n/a'))}")
        st.write(f"**Expected label:** {case.get('label', 'n/a')}")
        st.write(f"**Subject:** `{json.dumps(case.get('subject', {}))}`")
        st.write(f"**Transaction IDs:** `{json.dumps(case.get('transaction_ids', []))}`")
        st.write(f"**Signals:** `{json.dumps(case.get('signals', {}))}`")

    # -- explanation --------------------------------------------------------
    st.markdown("### Explanation")
    st.write(str(output.get("explanation", "No explanation recorded.")))

    # -- uncertainty / missing evidence -------------------------------------
    uncertainty = output.get("uncertainty", "n/a")
    missing = output.get("missing_evidence", [])
    with st.expander("Uncertainty / missing evidence"):
        st.metric("Uncertainty", str(uncertainty))
        if missing:
            st.table([{"missing": m} for m in missing])
        else:
            st.write("No missing-evidence items recorded.")

    # -- timeline ------------------------------------------------------------
    with st.expander("Timeline"):
        timeline = output.get("timeline", []) or []
        if timeline:
            try:
                st.dataframe(timeline)
            except Exception:
                st.json(timeline)
        else:
            st.write("No timeline events.")
        with st.expander("Raw transactions reviewed"):
            st.json(output.get("transactions_reviewed", []))

    # -- graph evidence -------------------------------------------------------
    with st.expander("Graph evidence", expanded=True):
        st.write(f"**Evidence IDs:** `{json.dumps(output.get('evidence_ids', []))}`")
        findings = output.get("graph_findings", []) or []
        if findings:
            try:
                rows = [
                    {
                        "query": f.get("query", ""),
                        "summary": str(f.get("summary", ""))[:120],
                        "nodes": f.get("node_count", 0),
                    }
                    for f in findings
                ]
                st.dataframe(rows)
            except Exception:
                st.json(findings)
            with st.expander("Full graph findings JSON"):
                st.json(findings)
        else:
            st.write("No graph findings.")
        with st.expander("Entities flagged"):
            st.json(output.get("entities_flagged", {}))

    # -- RAG citations ---------------------------------------------------------
    with st.expander("RAG citations"):
        cites = output.get("rag_citations", []) or []
        if cites:
            try:
                st.table(cites)
            except Exception:
                st.json(cites)
        else:
            st.write("No citations.")

    # -- amounts ---------------------------------------------------------------
    with st.expander("Amounts"):
        st.json(output.get("amounts", {}))

    # -- recommended actions + approval route -----------------------------------
    st.markdown("### Recommended actions / approval route")
    actions = (
        output.get("recommended_actions")
        or output.get("recommended_next_steps")
        or []
    )
    if actions:
        st.table([{"action": a} for a in actions])
    else:
        st.write("No recommended actions.")
    st.write(f"**Approval route:** `{output.get('approval_route', 'analyst review')}`")
    with st.expander("Actions taken"):
        st.json(output.get("actions_taken", []))
    with st.expander("Policy decisions"):
        st.json(output.get("policy_decisions", []))

    # -- propose an action (policy-gated via executor) -------------------------
    with st.expander("Propose an action (policy-gated via executor)"):
        action = st.selectbox("action", ["freeze_card", "block_device", "flag_email",
                                         "notify_user", "escalate_case", "refund_transaction"])
        entities = output.get("entities_flagged", {}) or {}
        default_target = str((entities.get("cards") or [""])[0])
        target = st.text_input("target", value=default_target)
        if st.button("Submit action"):
            if not target:
                st.error("target must be non-empty")
            else:
                try:
                    from src.actions.executor import execute

                    context = {"verdict": output.get("verdict", "escalate"),
                               "confidence": output.get("confidence", 0.0),
                               "fraud_pattern": output.get("fraud_pattern")}
                    record, decision = execute(str(action), target, context)
                    st.json({"record": record, "decision": decision})
                except Exception as exc:
                    st.error(f"action failed: {exc}")

    # -- memory matches ----------------------------------------------------------
    with st.expander("Memory matches"):
        mem = output.get("memory_matches", output.get("_memory_matches", []))
        if mem:
            st.json(mem)
        else:
            st.write("No similar past cases.")

    # -- SAR ----------------------------------------------------------------------
    sar_required = output.get("sar_required", False)
    sar = output.get("sar")
    if sar_required or sar:
        st.markdown("### SAR (Suspicious Activity Report)")
        st.write(f"**SAR required:** {bool(sar_required)}")
        if sar:
            st.json(sar)
    else:
        st.caption("SAR: not required for this case.")

    # -- raw -----------------------------------------------------------------------
    with st.expander("Raw output JSON"):
        st.json(output)


def main() -> None:
    """Streamlit entrypoint (streamlit imported lazily for offline safety)."""
    try:
        import streamlit as st
    except Exception as exc:
        raise RuntimeError(
            "streamlit is not installed; install it to run the UI "
            "(`pip install streamlit`) — saved outputs remain readable as JSON."
        ) from exc

    st.set_page_config(page_title="Fraud investigation dashboard", layout="wide")
    st.title("Fraud investigation — analyst dashboard")

    cases = list_cases()
    if not cases:
        st.error(f"No cases found under {INPUTS}")
        return
    case_id = st.selectbox("Case", cases, index=0)

    try:
        case = load_case_input(str(case_id))
    except Exception as exc:
        st.error(f"Cannot load case input: {exc}")
        return

    col_a, col_b = st.columns(2)
    run_clicked = col_a.button("Run investigation")
    load_clicked = col_b.button("Load saved output")

    if run_clicked:
        with st.spinner(f"Investigating {case_id} ..."):
            try:
                output = run_live_investigation(case)
                st.success("Live investigation complete.")
                _render_output(st, output, case)
            except Exception as exc:
                st.error(f"Live run failed: {exc}")
                st.info("Falling back to saved output (if present).")
                try:
                    _render_output(st, load_saved_output(str(case_id)), case)
                except Exception as exc2:
                    st.error(f"No saved output either: {exc2}")
    elif load_clicked:
        try:
            _render_output(st, load_saved_output(str(case_id)), case)
        except Exception as exc:
            st.error(f"Cannot load saved output: {exc}")
    else:
        # Default view: saved output if present, else case preview.
        try:
            _render_output(st, load_saved_output(str(case_id)), case)
        except Exception:
            st.info("No saved output yet — press **Run investigation**.")
            with st.expander("Case input preview", expanded=True):
                st.json(case)


# Back-compat alias: `streamlit run src/ui/app.py` works with either entry.
def run_ui() -> None:
    """Alias for :func:`main` (older in-progress draft used this name)."""
    main()


if __name__ == "__main__":
    main()
