from pathlib import Path
import streamlit as st
import pandas as pd
from paisa_agent.config import Settings
from .ui_config import load_ui_settings, save_ui_settings
from app import discover_candidates, build_daily_recommendations
from historical_backtest import run_historical_backtest


def main():
    st.set_page_config(page_title="Paisa Agent", layout="wide")
    st.title("Paisa Agent \u2013 Penny Stock Research & Recommendation")
    settings = Settings()
ui_settings = load_ui_settings()
for _key, _value in ui_settings.items():
    setattr(settings, _key, _value)
    st.write("## Phase 1: Market Research")
    st.write("This dashboard fetches recent historical data for a penny stock universe and ranks candidates by a simple score.")

    if st.button("Refresh Recommendations"):
        recommendations = discover_candidates(settings)
        if recommendations.empty:
            st.warning("No buy candidates found in the current universe.")
        else:
            st.success(f"Found {len(recommendations)} candidate(s)")
            st.dataframe(recommendations.head(settings.max_daily_positions))
    else:
        st.info("Press the button to fetch the latest candidate list.")

    st.markdown("---")
    st.write("## Run Full Agent")
    st.write("Click a button to run the recommendation pipeline and optionally the backtest from the UI.")

    if st.button("Run recommendation + backtest"):
        status = st.empty()
        status.text("Starting daily recommendation workflow...")
        with st.spinner("Discovering candidates..."):
            candidates = discover_candidates(settings)
        status.text(f"Found {len(candidates)} candidate(s).")

        with st.spinner("Building daily recommendations..."):
            recommendations = build_daily_recommendations(candidates, settings)

        if recommendations.empty:
            status.warning("No buy candidates found today based on current rules.")
        else:
            out_dir = Path(settings.report_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            rec_file = out_dir / f"recommendations_{pd.Timestamp.today().date().isoformat()}.csv"
            recommendations.to_csv(rec_file, index=False)
            status.success(f"Saved daily recommendations to {rec_file}")
            st.dataframe(recommendations.head(settings.max_daily_positions))

        status.text("Running historical backtest...")
        with st.spinner("Executing backtest..."):
            backtest_result = run_historical_backtest(settings, refresh=False)

        if backtest_result is None:
            status.error("Historical backtest failed or produced no output.")
        else:
            status.success("Historical backtest complete.")
            st.write("### Backtest summary")
            st.write(backtest_result["metrics"])
            st.write("- Trades file:", backtest_result["trades_file"])
            st.write("- Portfolio file:", backtest_result["portfolio_file"])
            st.write("- Summary file:", backtest_result["summary_file"])
            st.write("- Knowledge base:", backtest_result["knowledge_file"])

    st.markdown("---")
    st.write("### Notes")
    st.write(
        "- Only stocks with current price under ₹20 are scored.\n"
        "- The model uses SMA/EMA, RSI, MACD and volume rules in a simple scoring engine.\n"
        "- This is a paper trading prototype for discovery and testing, not a live broker hookup." 
    )

if __name__ == "__main__":
    main()
