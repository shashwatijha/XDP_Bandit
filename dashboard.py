import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os

st.set_page_config(page_title="EBalaNCer Monitor", layout="wide")


st.sidebar.title("Evaluation Controls")
data_source = st.sidebar.selectbox(
    "Select Data Source", 
    ["mab_contextual.csv", "mab_performance.csv", "baseline_rr.csv"],
    index=0
)

if st.sidebar.button('Clear Selected CSV'):
    with open(data_source, "w") as f:
        f.write("timestamp,choice,reward,load0,load1,traffic_type\n")
    st.sidebar.success(f"{data_source} Reset!")
    st.rerun()


st.title("EBalaNCer: eBPF Adaptive Load Balancer")
st.markdown(f"**Monitoring File:** `{data_source}`")

metric_row = st.columns(3)
chart_row = st.columns(2)

if os.path.exists(data_source):
    try:
        df = pd.read_csv(data_source)
        
        if not df.empty:
            # Indicator logic for Traffic-Aware Source
            if 'traffic_type' in df.columns and data_source == "mab_contextual.csv":
                last_type = df['traffic_type'].iloc[-1]
                if last_type == 1.0:
                    st.warning("⚡ Context: Elephant Flow Detected")
                else:
                    st.info("🖱️ Context: Mouse Flow Detected")

            last_entry = df.iloc[-1]
            
            with metric_row[0]:
                st.metric("Current Target", f"Node {int(last_entry['choice'])}")
            with metric_row[1]:
                st.metric("Last Reward", f"{last_entry['reward']:.2f}")
            with metric_row[2]:
                st.metric("Total Samples", len(df))

            with chart_row[0]:
                st.subheader("Reward History")
                # Color code based on logic type
                colors = {"mab_contextual.csv": "#11caa0", "mab_performance.csv": "#636EFA", "baseline_rr.csv": "#EF553B"}
                fig_reward = px.line(df, x=df.index, y="reward", 
                                     color_discrete_sequence=[colors.get(data_source, "blue")])
                st.plotly_chart(fig_reward, use_container_width=True)

            with chart_row[1]:
                st.subheader("Algorithm Confidence")
                df['cumulative_reward'] = df['reward'].cumsum()
                fig_cum = px.area(df, x=df.index, y='cumulative_reward')
                st.plotly_chart(fig_cum, use_container_width=True)

            # --- PIE CHART SECTION ---
            st.divider()
            dist_col1, dist_col2 = st.columns([1, 2])
            
            with dist_col1:
                st.subheader("Selection Metrics")
                counts = df['choice'].value_counts()
                for i in [0, 1]:
                    count = counts.get(float(i), 0)
                    pct = (count / len(df)) * 100 if len(df) > 0 else 0
                    st.metric(f"Node {i}", int(count), delta=f"{pct:.1f}%")

            with dist_col2:
                st.subheader("Traffic Allocation (Pie)")
                usage_df = df['choice'].map({0: "Node 0", 1: "Node 1"}).value_counts().reset_index()
                usage_df.columns = ['Node', 'Count']
                fig_pie = px.pie(usage_df, values='Count', names='Node', hole=0.4,
                                 color='Node', color_discrete_map={"Node 0": "#636EFA", "Node 1": "#EF553B"})
                st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Waiting for valid data... {e}")

time.sleep(1)
st.rerun()