# Software Defined Radio (SDR) Laboratory

Welcome to the official documentation portal and report repository for **Team-07** in the Software Defined Radio Laboratory course at the Department of Electrical Engineering.

!!! info "Lab Portal Overview"
    This website contains all laboratory documentation, including pre-lab preparation, real-time measurement logs, raw `.cf32` data analysis, and post-session reports for **ADALM-Pluto SDR** experiments.

---

## 👥 Team & Course Identity

| Attribute | Details |
| :--- | :--- |
| **Course** | Software Defined Radio (SDR) Laboratory |
| **Department** | Department of Electrical Engineering |
| **Instructor** | Dr. Seyed Mohammad Karbasi |
| **Teaching Assistants** | Ali Aghaei, Fatemeh Saem, Ali Pourhassan, Ali Majlesi |
| **Team Identifier** | **Team-01** |
| **Team Members** | Seyedparham Moghaddasi & Amirali Rajai|

---

## 🛠️ Hardware & Software Specifications

### 📡 ADALM-Pluto Transceiver Specifications
- **RF Transceiver Chip:** Analog Devices AD9363
- **SoC Architecture:** Xilinx Zynq-7010 (FPGA + Dual ARM Cortex-A9)
- **Frequency Coverage:** $325\text{ MHz}$ to $3.8\text{ GHz}$ (default RF tuning range)
- **Reference Oscillator Accuracy:** $\pm 25\text{ ppm}$ TCXO
- **Network Configuration:** Static IP `192.168.1.10` via LAN/USB

### 💻 Software Infrastructure
- **Flowgraph Environment:** GNU Radio Companion 3.10+
- **Offline Post-Processing:** Python 3 (NumPy, SciPy, Matplotlib)
- **Hardware Interface Drivers:** `libiio` & `pyadi-iio`
- **Documentation Engine:** MkDocs Material with MathJax rendering
- **Source Control & Hosting:** Git & GitHub Pages

---

## 📂 Laboratory Reports Directory

The course follows a structured three-stage learning model (Pre-Session, In-Session, Post-Session). Below is the master index of all lab reports:

| Lab # | Topic / Title | Pre-Report | In-Lab Data | Post-Report | Action |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Lab 00** | System Setup & Environment Calibration | Completed | Verified | Published | [View Logbook](log.md) |
| **Lab 01** | **RF Spectrum Monitoring** | Completed | Recorded `.cf32` | **Published** | [**View Lab 01 Report**](Lab1/lab01.md) |
| **Lab 02** | **RF Receiver Noise Figure & Nonlinearity** | Completed | Pending | Pending | [View Pre-Lab](Lab2/prelab.md) |


---


## 📁 Quick Links & Navigation

- [x] [**Lab 01 Report (`Lab1/lab01.md`)**](Lab1/lab01.md) — Comprehensive analysis of Spectrum Monitoring and Loopback tests.
- [x] [**Team Measurement Logbook (`log.md`)**](log.md) — Real-time in-lab measurement logs, device parameters, and troubleshooting records.