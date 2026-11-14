# 📡 Software Defined Radio Laboratory Portal

Welcome to the official documentation portal and report repository for **Team-01** in the Software Defined Radio Laboratory course at the Department of Electrical Engineering.

!!! info "Lab Portal Overview"
    This website contains all laboratory documentation, including pre-lab preparation, real-time measurement logs, raw `.cf32` data analysis, and post-session reports for **ADALM-Pluto SDR** experiments.

---

## 📂 Interactive Lab Directory

<div class="grid cards" markdown>

-   :material-tune: **Lab 00: System Setup & Calibration**
    ---
    Environment Calibration & Initial Connectivity.
    <br><br>
    <span class="status-live">Completed & Published</span>
    <br><br>
    [:octicons-arrow-right-24: View Logbook](log.md)

-   :material-waveform: **Lab 01: RF Spectrum Monitoring**
    ---
    Comprehensive analysis of RF Spectrum and Loopback tests.
    <br><br>
    <span class="status-live">Published & Recorded</span>
    <br><br>
    [:octicons-arrow-right-24: Read Full Report](Lab1/lab01.md)

-   :material-chart-bell-curve-cumulative: **Lab 02: Noise Figure & Nonlinearity**
    ---
    Analyzing RF receiver noise figure and dynamic range.
    <br><br>
    <span class="status-pending">Pending In-Lab Data</span>
    <br><br>
    [:octicons-arrow-right-24: View Pre-Lab](Lab2/prelab.md)

</div>

---

## ⚙️ Interactive System Architecture

```mermaid
graph LR
    subgraph PC["💻 Host Environment (GNU Radio 3.10+)"]
        direction TB
        A[Python 3 Processing] <--> B[libiio / pyadi-iio Drivers]
    end
    
    subgraph SDR["📡 ADALM-Pluto (Xilinx Zynq-7010)"]
        direction TB
        C[AD9363 Transceiver]
    end

    B <==>|Static IP 192.168.1.10 <br> LAN/USB| C
    C -->|TX: 325 MHz - 3.8 GHz| D((TX Ant))
    E((RX Ant)) -->|RX: 325 MHz - 3.8 GHz| C
    
    classDef hardware fill:#1e1e1e,stroke:#00e676,stroke-width:2px;
    class SDR hardware;