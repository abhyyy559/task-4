"""Streamlit analyst dashboard for fraud investigations (offline-safe).

Run with: ``streamlit run src/ui/app.py``

Renders the official answer format: case record, evidence, SAR, and
next-best actions (initial vs final). Live runs use
``src.agent.investigate`` over the HHGOA dataset; saved answers load from
``cases/HHG-*.json``.

Offline safety: ``streamlit`` and all ``src.agent`` imports happen lazily
inside functions, so ``python -m py_compile src/ui/app.py`` passes without
streamlit installed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
# `streamlit run src/ui/app.py` adds the script's folder (src/ui) to sys.path
# but NOT the project root, so lazy `from src.agent...` imports inside the
# live-run path fail with "No module named 'src'". Insert ROOT explicitly;
# idempotent, works regardless of where streamlit is launched from.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INPUTS = ROOT / "cases" / "inputs"
CASES = ROOT / "cases"


def list_cases() -> list[str]:
    """Return sorted case_ids available under cases/inputs/."""
    if not INPUTS.exists():
        return []
    return sorted(p.stem for p in INPUTS.glob("HHG-*.json"))


def load_case_input(case_id: str) -> dict[str, Any]:
    """Load one cases/inputs/{case_id}.json (raises FileNotFoundError)."""
    path = INPUTS / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"case input missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_saved_output(case_id: str) -> dict[str, Any]:
    """Load one cases/{case_id}.json (raises FileNotFoundError)."""
    path = CASES / f"{case_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"saved answer missing: {path} (run benchmark first)")
    return json.loads(path.read_text(encoding="utf-8"))


def run_live_investigation(case: dict[str, Any]) -> dict[str, Any]:
    """Run a live investigation for a case dict via the official pipeline."""
    try:
        from src.agent.orchestrator import investigate_case

        out = investigate_case(dict(case))
    except Exception as exc:
        raise ValueError(f"live investigation failed: {exc}") from exc
    if not isinstance(out, dict):
        raise ValueError("investigation returned non-dict answer")
    return out


def _verdict_color(verdict: str) -> str:
    return {"fraud": "red", "uncertain": "orange", "legitimate": "green"}.get(
        str(verdict).lower(), "gray"
    )


def _nba_table(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "action": str(a.get("action", "")),
            "route": str(a.get("route", "")),
            "reason": str(a.get("reason", ""))[:160],
        }
        for a in items
    ]


def _render_output(st: Any, answer: dict[str, Any], case: dict[str, Any]) -> None:
    """Render one official answer record with streamlit widgets."""
    rec = answer.get("case", {})
    verdict = rec.get("verdict", "uncertain")
    status = rec.get("status", "open")
    prob = float(rec.get("fraud_probability", 0.0) or 0.0)
    pattern = rec.get("pattern", "none")
    exposure = float(rec.get("exposure_usd", 0.0) or 0.0)

    st.subheader(f"Verdict: :{_verdict_color(verdict)}[{verdict}]")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fraud probability", f"{prob:.2f}")
    c2.metric("Pattern", pattern)
    c3.metric("Exposure (USD)", f"${exposure:,.2f}")
    c4.metric("Status", status)

    st.markdown("### Summary")
    st.write(rec.get("summary", "No summary recorded."))
    if rec.get("pattern_description"):
        st.info(rec["pattern_description"])

    with st.expander("Trigger / case details", expanded=True):
        st.write(f"**Case:** {answer.get('case_id', case.get('case_id'))}")
        st.write(f"**Trigger type:** {case.get('trigger_type', 'n/a')}")
        st.write(f"**Trigger:** {case.get('trigger_text', 'n/a')}")
        st.write(f"**Flagged transaction:** `{case.get('flagged_txn_id')}`")
        st.write(f"**Card:** `{case.get('card_id')}` / **Customer:** `{case.get('customer_id')}`")
        if case.get("risk_score") is not None:
            st.write(f"**Model risk score (input, not verdict):** {case.get('risk_score')}")
        st.write(f"**Affected transactions:** `{json.dumps(rec.get('affected_txn_ids', []))}`")
        st.write(f"**First suspicious:** `{rec.get('first_suspicious_txn_id') or 'n/a'}`")
        st.write(f"**Connected cards:** `{json.dumps(rec.get('connected_card_ids', []))}`")
        st.write(
            "**Connected device profiles:** "
            f"`{json.dumps(rec.get('connected_device_profiles', []))}`"
        )

    with st.expander("Evidence", expanded=True):
        evidence = rec.get("evidence", []) or []
        if evidence:
            try:
                st.dataframe(
                    [
                        {
                            "claim": str(e.get("claim", ""))[:140],
                            "source": e.get("source", ""),
                            "ref": e.get("ref", ""),
                            "entities": ", ".join(e.get("entity_ids", [])[:4]),
                        }
                        for e in evidence
                    ]
                )
            except Exception:
                st.json(evidence)
        else:
            st.write("No evidence recorded.")

    with st.expander("Similar prior cases (case memory)"):
        similar = rec.get("similar_prior_cases", []) or []
        st.write(", ".join(similar) if similar else "None retrieved.")
        st.caption(
            f"Written to graph: {rec.get('written_to_graph')} "
            f"({rec.get('graph_case_id') or 'n/a'})"
        )

    sar = answer.get("sar", {}) or {}
    st.markdown("### SAR (Suspicious Activity Report)")
    st.write(f"**File:** {bool(sar.get('file'))} — {sar.get('reason', '')}")
    if sar.get("file"):
        st.write(sar.get("narrative", ""))
        st.write(f"**Subjects:** `{json.dumps(sar.get('subjects', []))}`")
        st.write(f"**Total amount:** ${float(sar.get('total_amount_usd', 0) or 0):,.2f}")
        st.write(f"**Activity dates:** `{json.dumps(sar.get('activity_dates', []))}`")

    nba = answer.get("next_best_actions", {}) or {}
    st.markdown("### Next best actions")
    st.caption("**Initial** (before requested evidence)")
    try:
        st.table(_nba_table(nba.get("initial", []) or []))
    except Exception:
        st.json(nba.get("initial", []))
    st.caption("**Final** (after assumed evidence responses)")
    try:
        st.table(_nba_table(nba.get("final", []) or []))
    except Exception:
        st.json(nba.get("final", []))
    st.write(f"**What changed:** {nba.get('what_changed', 'nothing')}")

    with st.expander("Evidence requests (simulated responses)"):
        reqs = answer.get("evidence_requests", []) or []
        if reqs:
            st.json(reqs)
        else:
            st.write("No extra evidence requested.")

    with st.expander("Run metadata"):
        st.json(
            {
                "stop_reason": answer.get("stop_reason"),
                "tool_calls": answer.get("tool_calls"),
                "tokens": answer.get("tokens"),
                "latency_s": answer.get("latency_s"),
            }
        )

    with st.expander("Propose an action (policy-gated via executor)"):
        from src.agent.policy import KNOWN_ACTIONS

        action = st.selectbox("action", list(KNOWN_ACTIONS))
        target = st.text_input("target", value=str(case.get("card_id", "")))
        if st.button("Submit action"):
            if not target:
                st.error("target must be non-empty")
            else:
                try:
                    from src.actions.executor import execute

                    record, decision = execute(
                        str(action), target, {"rule": "ui-proposal"}
                    )
                    st.json({"record": record, "decision": decision})
                    st.caption(
                        "Only `auto`-route actions execute; L1/L2 are recorded "
                        "as recommendations awaiting human approval."
                    )
                except Exception as exc:
                    st.error(f"action failed: {exc}")

    with st.expander("Raw answer JSON"):
        st.json(answer)


def main() -> None:
    """Streamlit entrypoint (streamlit imported lazily for offline safety)."""
    try:
        import streamlit as st
    except Exception as exc:
        raise RuntimeError(
            "streamlit is not installed; install it to run the UI "
            "(`pip install streamlit`) — saved answers remain readable as JSON."
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
    load_clicked = col_b.button("Load saved answer")

    if run_clicked:
        with st.spinner(f"Investigating {case_id} ..."):
            try:
                output = run_live_investigation(case)
                st.success("Live investigation complete.")
                _render_output(st, output, case)
            except Exception as exc:
                st.error(f"Live run failed: {exc}")
                st.info("Falling back to saved answer (if present).")
                try:
                    _render_output(st, load_saved_output(str(case_id)), case)
                except Exception as exc2:
                    st.error(f"No saved answer either: {exc2}")
    elif load_clicked:
        try:
            _render_output(st, load_saved_output(str(case_id)), case)
        except Exception as exc:
            st.error(f"Cannot load saved answer: {exc}")
    else:
        try:
            _render_output(st, load_saved_output(str(case_id)), case)
        except Exception:
            st.info("No saved answer yet — press **Run investigation**.")
            with st.expander("Case input preview", expanded=True):
                st.json(case)


def run_ui() -> None:
    """Alias for :func:`main`."""
    main()


if __name__ == "__main__":
    main()
