from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


QUALIFYING_EXPORT_FOLDER = Path("qualifying_exports")
EXPORT_FOLDER = Path("race_exports")

def format_export_name(path):
    raw = (
        path.stem
        .replace("race_results_", "")
        .replace("qualifying_results_", "")
        .replace("race_events_", "")
        .replace("race_lap_standings_", "")
    )

    try:
        date = datetime.strptime(raw, "%Y-%m-%d_%H-%M-%S")
        return date.strftime("%d %B %Y, %H:%M")
    except ValueError:
        return path.name


def get_result_files():
    return sorted(
        EXPORT_FOLDER.glob("race_results_*.csv"),
        reverse=True
    )


def get_qualifying_files():
    return sorted(
        QUALIFYING_EXPORT_FOLDER.glob("qualifying_results_*.csv"),
        reverse=True
    )


def format_position_diff(diff):
    if pd.isna(diff):
        return "—"

    diff = int(diff)

    if diff > 0:
        return f"▲ +{diff}"

    if diff < 0:
        return f"▼ {diff}"

    return "—"


st.image("viewer.png", width=1920)

race_tab, qualifying_tab = st.tabs(["🏁 Race Results", "⏱ Qualifying"])


# =========================
# RACE TAB
# =========================

with race_tab:
    result_files = get_result_files()

    if not result_files:
        st.warning("No race result exports found yet.")
    else:
        selected_results_file = st.selectbox(
            "Select Race",
            result_files,
            format_func=lambda path: f"Race - {format_export_name(path)}"
        )

        events_file = EXPORT_FOLDER / selected_results_file.name.replace(
            "race_results_",
            "race_events_"
        )

        standings_file = EXPORT_FOLDER / selected_results_file.name.replace(
            "race_results_",
            "race_lap_standings_"
        )

        results = pd.read_csv(selected_results_file)

        st.caption(f"Loaded: `{selected_results_file.name}`")

        # =========================
        # RACE EVENTS + LAP STANDINGS
        # =========================

        st.subheader("🏁 Race Results")

        if events_file.exists():
            events = pd.read_csv(events_file)
        else:
            events = pd.DataFrame(columns=["Lap", "Event"])

        if standings_file.exists():
            lap_standings = pd.read_csv(standings_file)
        else:
            lap_standings = pd.DataFrame()

        if not events.empty:
            max_lap_from_events = int(events["Lap"].max())
        else:
            max_lap_from_events = 1

        if not lap_standings.empty and "Lap" in lap_standings.columns:
            max_lap_from_standings = int(lap_standings["Lap"].max())
        else:
            max_lap_from_standings = 1

        max_lap = max(max_lap_from_events, max_lap_from_standings)

        if "current_lap" not in st.session_state:
            st.session_state.current_lap = 1

        st.session_state.current_lap = min(
            st.session_state.current_lap,
            max_lap
        )

        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 1, 2, 1])

        with nav_col1:
            if st.button("⬅ Previous Lap"):
                st.session_state.current_lap = max(
                    1,
                    st.session_state.current_lap - 1
                )

        with nav_col2:
            if st.button("Next Lap ➡"):
                st.session_state.current_lap = min(
                    max_lap,
                    st.session_state.current_lap + 1
                )

        with nav_col3:
            selected_lap = st.slider(
                "Lap",
                min_value=1,
                max_value=max_lap,
                value=st.session_state.current_lap
            )
            st.session_state.current_lap = selected_lap

        with nav_col4:
            if st.button("Final Lap"):
                st.session_state.current_lap = max_lap

        current_lap = st.session_state.current_lap

        st.markdown(f"### Lap {current_lap}")

        event_col, standings_col = st.columns([1, 2])

        with event_col:
            st.subheader("Events")

            if events.empty:
                st.info("No race events file found for this race.")
            else:
                lap_events = events[events["Lap"] == current_lap]

                if lap_events.empty:
                    st.info("No notable events on this lap.")
                else:
                    for _, event in lap_events.iterrows():
                        st.write(f"• {event['Event']}")

        with standings_col:
            st.subheader("Standings")

            if lap_standings.empty:
                st.info("No lap standings file found for this race.")
            else:
                current_standings = lap_standings[
                    lap_standings["Lap"] == current_lap
                ].copy()

                if current_standings.empty:
                    st.info("No standings data for this lap.")
                else:
                    if "Diff" in current_standings.columns:
                        current_standings["Diff"] = current_standings["Diff"].apply(
                            format_position_diff
                        )

                    standings_columns = [
                        "Position",
                        "Last Lap Position",
                        "Diff",
                        "Driver",
                        "Team",
                        "Tyre",
                        "Lap Time",
                        "Fastest Lap",
                    ]

                    available_columns = [
                        column for column in standings_columns
                        if column in current_standings.columns
                    ]

                    st.dataframe(
                        current_standings[available_columns],
                        use_container_width=True,
                        hide_index=True
                    )

        # =========================
        # RESULTS SPOILER PROTECTION
        # =========================

        if "spoilers_revealed" not in st.session_state:
            st.session_state.spoilers_revealed = False

        if not st.session_state.spoilers_revealed:
            st.divider()

            st.warning(
                "⚠️ Race results are hidden. "
                "Follow the race through the lap-by-lap replay above."
            )

            if st.button("🏁 Reveal Final Results"):
                st.session_state.spoilers_revealed = True
                st.rerun()

        # =========================
        # FINAL RESULTS
        # =========================

        if st.session_state.spoilers_revealed:
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

            st.divider()

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
# QUALIFYING TAB
# =========================

with qualifying_tab:
    st.subheader("⏱ Qualifying Results")

    qualifying_files = get_qualifying_files()

    if not qualifying_files:
        st.warning("No qualifying exports found yet.")
    else:
        selected_qualifying_file = st.selectbox(
            "Select Qualifying Session",
            qualifying_files,
            format_func=lambda path: f"Qualifying - {format_export_name(path)}"
        )

        qualifying_results = pd.read_csv(selected_qualifying_file)

        st.caption(f"Loaded: `{selected_qualifying_file.name}`")

        pole_sitter = qualifying_results.iloc[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Pole Sitter", pole_sitter["Driver"])

        with col2:
            st.metric("Team", pole_sitter["Team"])

        with col3:
            st.metric("Pole Time", pole_sitter["Fastest Lap"])

        st.dataframe(
            qualifying_results,
            use_container_width=True,
            hide_index=True
        )