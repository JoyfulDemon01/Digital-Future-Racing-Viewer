from pathlib import Path
from PIL import Image
import pandas as pd
import streamlit as st


EXPORT_FOLDER = Path("race_exports")


st.set_page_config(
    page_title="DFR Race Viewer",
    layout="wide",
)

st.image(
    "dfr_logo.png",
    width=250
)
st.title("Race Results Viewer")


def get_result_files():
    return sorted(
        EXPORT_FOLDER.glob("race_results_*.csv"),
        reverse=True
    )


result_files = get_result_files()

if not result_files:
    st.warning("No race result exports found yet.")
    st.stop()


selected_results_file = st.sidebar.selectbox(
    "Select Race",
    result_files,
    format_func=lambda path: path.name
)

events_file = EXPORT_FOLDER / selected_results_file.name.replace(
    "race_results_",
    "race_events_"
)


results = pd.read_csv(selected_results_file)

# =========================
# RESULTS SPOILER PROTECTION
# =========================

if "spoilers_revealed" not in st.session_state:
    st.session_state.spoilers_revealed = False

if not st.session_state.spoilers_revealed:

    st.divider()

    st.warning(
        "⚠️ Race results are hidden. "
        "Follow the race through the lap-by-lap events below."
    )

    if st.button("🏁 Reveal Final Results"):
        st.session_state.spoilers_revealed = True
        st.rerun()

# =========================
# SUMMARY DATA
# =========================

finished = results[results["Status"].isin(["Running", "Finished"])]
dnfs = results[~results["Status"].isin(["Running", "Finished"])]

results["Position Change"] = (
    results["Starting Position"] - results["Position"]
)

classified_results = results[
    results["Status"].isin(["Running", "Finished"])
]

biggest_gainer = classified_results.sort_values(
    "Position Change",
    ascending=False
).iloc[0]

biggest_loser = classified_results.sort_values(
    "Position Change",
    ascending=True
).iloc[0]

fastest_lap_row = results[
    results["Fastest Lap"].notna()
].sort_values("Fastest Lap").iloc[0]

podium = results.head(3)


# =========================
# SUMMARY CARDS
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Winner", results.iloc[0]["Driver"])

with col2:
    st.metric("Fastest Lap", fastest_lap_row["Driver"])

with col3:
    st.metric("DNFs", len(dnfs))


col4, col5, col6 = st.columns(3)

with col4:
    st.metric(
        "Biggest Gainer",
        biggest_gainer["Driver"],
        f"+{biggest_gainer['Position Change']}"
    )

with col5:
    st.metric(
        "Biggest Loser",
        biggest_loser["Driver"],
        str(biggest_loser["Position Change"])
    )

with col6:
    st.metric(
        "Pole Sitter",
        results.sort_values("Starting Position").iloc[0]["Driver"]
    )


# =========================
# PODIUM
# =========================

st.subheader("Podium")

podium_cols = st.columns(3)

podium_order = [
    (podium.iloc[1], "🥈 2nd Place"),
    (podium.iloc[0], "🥇 Winner"),
    (podium.iloc[2], "🥉 3rd Place"),
]

for col, (driver_row, title) in zip(podium_cols, podium_order):
    with col:
        st.markdown(
            f"""
            <div style="
                border: 1px solid #444;
                border-radius: 12px;
                padding: 18px;
                text-align: center;
                background-color: #1e1e1e;
            ">
                <h3>{title}</h3>
                <h2>{driver_row['Driver']}</h2>
                <p>{driver_row['Team']}</p>
                <p>Started P{driver_row['Starting Position']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================
# FULL RESULTS TABLE
# =========================

st.subheader("Full Race Results")

display_results = results.copy()

fastest_lap_time = (
    display_results["Fastest Lap"]
    .dropna()
    .min()
)

display_results["Fastest Lap"] = (
    display_results["Fastest Lap"]
    .apply(
        lambda lap:
        f"{lap} ★"
        if pd.notna(lap) and lap == fastest_lap_time
        else lap
    )
)

st.dataframe(
    display_results,
    use_container_width=True,
    hide_index=True
)


# =========================
# RACE EVENTS - LAP BY LAP
# =========================

if events_file.exists():
    events = pd.read_csv(events_file)

    st.subheader("Race Events")

    max_lap = int(events["Lap"].max()) if not events.empty else 1

    if "current_lap" not in st.session_state:
        st.session_state.current_lap = 1

    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

    with col1:
        if st.button("⬅ Previous Lap"):
            st.session_state.current_lap = max(
                1,
                st.session_state.current_lap - 1
            )

    with col2:
        if st.button("Next Lap ➡"):
            st.session_state.current_lap = min(
                max_lap,
                st.session_state.current_lap + 1
            )

    with col3:
        selected_lap = st.slider(
            "Lap",
            min_value=1,
            max_value=max_lap,
            value=st.session_state.current_lap
        )
        st.session_state.current_lap = selected_lap

    with col4:
        if st.button("Final Lap"):
            st.session_state.current_lap = max_lap

    current_lap = st.session_state.current_lap

    st.markdown(f"### Lap {current_lap}")

    lap_events = events[events["Lap"] == current_lap]

    if lap_events.empty:
        st.info("No notable events on this lap.")
    else:
        for _, event in lap_events.iterrows():
            st.write(f"• {event['Event']}")

else:
    st.info("No race events file found for this race.")