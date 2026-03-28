import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from ping3 import ping
import speedtest
import subprocess
import socket
import os
import numpy as np
from sklearn.linear_model import LinearRegression
from scapy.all import ARP, Ether, srp
import requests
import networkx as nx
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
from fpdf import FPDF
import time

# ---------------- CONFIG ---------------- #

ROUTER_IP = "192.168.0.1"
DATA_FILE = "latency_data.csv"
DEVICE_FILE = "devices.csv"

st.set_page_config(page_title="AI Network Monitor", layout="wide")

# ---------------- CSS UI ---------------- #

st.markdown("""
<style>
.stApp{
background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
}
h1{
text-align:center;
color:#00e5ff;
}
[data-testid="metric-container"]{
background: rgba(255,255,255,0.05);
padding:15px;
border-radius:10px;
}
[data-testid="stMetricValue"]{
color:#00e5ff;
font-size:28px;
}
.stButton > button{
background:#00e5ff;
color:black;
border-radius:10px;
padding:10px 25px;
}
section[data-testid="stSidebar"]{
background:#111;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ---------------- #

st.sidebar.title("📡 Navigation")

page = st.sidebar.radio(
"Select Page",
["Dashboard","Devices","Topology Map","AI Prediction"]
)

# ---------------- FUNCTIONS ---------------- #

def get_latency():

    try:
        latency = ping(ROUTER_IP)
        if latency:
            return round(latency*1000,2)
    except:
        pass

    return None


def run_speed_test():

    try:
        s = speedtest.Speedtest()
        s.get_best_server()

        download = round(s.download()/1_000_000,2)
        upload = round(s.upload()/1_000_000,2)

        return download,upload
    except:
        return None,None


def save_latency(latency):

    df = pd.DataFrame({"latency":[latency]})

    if os.path.exists(DATA_FILE):
        df.to_csv(DATA_FILE,mode="a",header=False,index=False)
    else:
        df.to_csv(DATA_FILE,index=False)


def get_wifi_name():

    try:
        result = subprocess.check_output(
        "netsh wlan show interfaces",
        shell=True
        ).decode()

        for line in result.split("\n"):
            if "SSID" in line and "BSSID" not in line:
                return line.split(":")[1].strip()

    except:
        pass

    return "Unknown"


def get_signal_strength():

    try:
        result = subprocess.check_output(
        "netsh wlan show interfaces",
        shell=True
        ).decode()

        for line in result.split("\n"):
            if "Signal" in line:
                return line.split(":")[1].strip()

    except:
        pass

    return "Unknown"


def scan_network():

    target="192.168.0.0/24"

    arp=ARP(pdst=target)
    ether=Ether(dst="ff:ff:ff:ff:ff:ff")

    packet=ether/arp

    result=srp(packet,timeout=3,verbose=0)[0]

    devices=[]

    for sent,received in result:

        ip=received.psrc
        mac=received.hwsrc

        try:
            hostname=socket.gethostbyaddr(ip)[0]
        except:
            hostname="Unknown"

        try:
            vendor=requests.get(
            f"https://api.macvendors.com/{mac}",
            timeout=3
            ).text
        except:
            vendor="Unknown"

        devices.append({
        "IP":ip,
        "MAC":mac,
        "Device Name":hostname,
        "Vendor":vendor
        })

    df=pd.DataFrame(devices)

    return df


def check_intruder(devices):

    if os.path.exists(DEVICE_FILE):

        old=pd.read_csv(DEVICE_FILE)

        new_devices=devices[~devices["MAC"].isin(old["MAC"])]

        if len(new_devices)>0:

            st.error("⚠ New Device Detected!")

            st.dataframe(new_devices)

    devices.to_csv(DEVICE_FILE,index=False)


def generate_pdf_report(wifi,signal,latency,download,upload,devices):

    pdf=FPDF()
    pdf.add_page()

    pdf.set_font("Arial",size=16)

    pdf.cell(200,10,"Network Monitoring Report",ln=True)

    pdf.set_font("Arial",size=12)

    pdf.cell(200,10,f"WiFi Name: {wifi}",ln=True)
    pdf.cell(200,10,f"Signal Strength: {signal}",ln=True)
    pdf.cell(200,10,f"Router IP: {ROUTER_IP}",ln=True)

    pdf.cell(200,10,f"Latency: {latency}",ln=True)
    pdf.cell(200,10,f"Download Speed: {download}",ln=True)
    pdf.cell(200,10,f"Upload Speed: {upload}",ln=True)

    pdf.ln(10)

    pdf.cell(200,10,"Connected Devices:",ln=True)

    for i,row in devices.iterrows():

        pdf.cell(
        200,
        10,
        f"{row['IP']} - {row['MAC']} - {row['Device Name']}",
        ln=True
        )

    filename="network_report.pdf"

    pdf.output(filename)

    return filename


# ---------------- DASHBOARD ---------------- #

if page=="Dashboard":

    #   st_autorefresh(interval=5000,key="refresh")

    st.title("🌐 AI Network Monitoring Dashboard")

    col1,col2,col3=st.columns(3)

    col1.metric("WiFi Name",get_wifi_name())
    col2.metric("Signal Strength",get_signal_strength())
    col3.metric("Router IP",ROUTER_IP)


    # Initialize session state
    if "latency" not in st.session_state:
        st.session_state.latency = None

    if "download" not in st.session_state:
        st.session_state.download = None

    if "upload" not in st.session_state:
        st.session_state.upload = None


    # Button click
    if st.button("Run Network Test"):

        with st.spinner("Running network test..."):
            st.session_state.latency = get_latency()
            st.session_state.download, st.session_state.upload = run_speed_test()

        if st.session_state.latency:
            save_latency(st.session_state.latency)
        
    # download=None
    # upload=None
    # latency=None

    # if st.button("Run Network Test"):

    #     latency=get_latency()
    #     download,upload=run_speed_test()

    #     if latency:
    #         save_latency(latency)

    col1,col2,col3=st.columns(3)
    col1.metric(
    "Latency",
    f"{st.session_state.latency} ms" if st.session_state.latency else "N/A"
)

    col2.metric(
    "Download",
    f"{st.session_state.download} Mbps" if st.session_state.download else "N/A"
)

    col3.metric(
    "Upload",
    f"{st.session_state.upload} Mbps" if st.session_state.upload else "N/A"
)
    # col1.metric("Latency",f"{latency} ms" if latency else "N/A")
    # col2.metric("Download",f"{download} Mbps" if download else "N/A")
    # col3.metric("Upload",f"{upload} Mbps" if upload else "N/A")

    # if latency:

    #     fig=go.Figure(go.Indicator(
    #     mode="gauge+number",
    #     value=latency,
    #     title={'text':"Latency (ms)"},
    #     gauge={'axis':{'range':[0,100]}}
    #     ))

        # st.plotly_chart(fig)

    # -------Latency gayuge----------

    if st.session_state.latency:

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=st.session_state.latency,
            title={'text': "Latency (ms)"},
            gauge={'axis': {'range': [0, 100]}}
        ))

        st.plotly_chart(fig)

    # ---------------- SPEEDOMETER UI ---------------- #

    def speed_gauge(value, title, max_val=100):
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value if value else 0,
            title={'text': title},
            gauge={
                'axis': {'range': [0, max_val]},
                'bar': {'color': "#00e5ff"},
            }
        ))
        return fig


    col1, col2 = st.columns(2)

    if st.session_state.download:
        col1.plotly_chart(
            speed_gauge(st.session_state.download, "Download (Mbps)", 200),
            use_container_width=True
        )

    if st.session_state.upload:
        col2.plotly_chart(
            speed_gauge(st.session_state.upload, "Upload (Mbps)", 100),
            use_container_width=True
        )

    # if os.path.exists(DATA_FILE):

    #     df=pd.read_csv(DATA_FILE)

    #     st.subheader("📊 Latency History")

    #     fig=px.line(df,y="latency",markers=True)

    #     st.plotly_chart(fig,use_container_width=True)

    # ---------------- NETWORK ALERT SYSTEM ---------------- #

    st.markdown("### 🚨 Network Status")

    if st.session_state.latency is not None:

        latency = st.session_state.latency
        download = st.session_state.download
        upload = st.session_state.upload

        if latency > 100:
            st.error("🚨 High Latency Detected! Your network is slow.")

        elif download is not None and download < 5:
            st.warning("⚠ Slow Download Speed!")

        elif upload is not None and upload < 2:
            st.warning("⚠ Low Upload Speed!")

        else:
            st.success("✅ Network is Stable and Performing Well")

    # LIVE REAL-TIME LATENCY GRAPH

    if os.path.exists(DATA_FILE):

        df = pd.read_csv(DATA_FILE)

        st.subheader("📊 Live Latency Monitoring")

        chart = st.line_chart(df)

        # Live update loop
        for i in range(10):  # updates 10 times
            time.sleep(2)

            new_latency = get_latency()

            if new_latency is not None:
                new_row = pd.DataFrame({"latency": [new_latency]})

                # Save + update
                new_row.to_csv(DATA_FILE, mode="a", header=False, index=False)

                chart.add_rows(new_row)

    if st.button("Generate PDF Report"):

        devices=scan_network()

        file=generate_pdf_report(
        get_wifi_name(),
        get_signal_strength(),
        latency,
        download,
        upload,
        devices
        )

        with open(file,"rb") as f:

            st.download_button(
            "Download Report",
            f,
            file_name=file
            )


# ---------------- DEVICES ---------------- #

if page=="Devices":

    st.title("📡 Connected Devices")

    if st.button("Scan Network"):

        devices=scan_network()

        check_intruder(devices)

        st.dataframe(devices,use_container_width=True)

        st.success(f"Total Devices Found: {len(devices)}")


# ---------------- TOPOLOGY ---------------- #

if page=="Topology Map":

    st.title("🗺 Network Topology")

    devices=scan_network()

    G=nx.Graph()

    G.add_node("Router")

    for ip in devices["IP"]:
        G.add_edge("Router",ip)

    pos=nx.spring_layout(G)

    fig,ax=plt.subplots()

    nx.draw(G,pos,with_labels=True,node_color="skyblue",node_size=2000,font_size=10)

    st.pyplot(fig)


# ---------------- AI PREDICTION ---------------- #

if page=="AI Prediction":

    st.title("🤖 AI Latency Prediction")

    if os.path.exists(DATA_FILE):

        df=pd.read_csv(DATA_FILE)

        if len(df)>5:

            X=np.arange(len(df)).reshape(-1,1)
            y=df["latency"]

            model=LinearRegression()
            model.fit(X,y)

            prediction=model.predict([[len(df)]])

            st.success(
            f"Predicted Next Latency: {round(prediction[0],2)} ms"
            )

            mean=y.mean()
            std=y.std()

            latest=y.iloc[-1]

            if latest>mean+2*std:

                st.error("⚠ Network anomaly detected!")

        else:

            st.info("Collect more latency data first.")