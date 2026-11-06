# Lab 02 Pre-Lab Report: Noise Figure, Gain Compression, and Intermodulation

[📥 Download PDF Version of Pre-Lab Report](Prelab2.pdf){ .md-button .md-button--primary }

---

## 1. Summary of Theoretical Concepts

RF receiver architectures are bounded at lower signal levels by thermal and internal component noise, and at upper levels by non-linear gain saturation and intermodulation distortion.

### Noise Figure ($NF$) and Noise Temperature ($T_e$)
The Noise Factor ($F$) and Noise Figure ($NF$) measure the degradation of the Signal-to-Noise Ratio ($SNR$) as a signal propagates through a receiver processing chain:

$$F = \frac{SNR_{\text{in}}}{SNR_{\text{out}}} = 1 + \frac{T_e}{T_0}, \quad NF = 10 \log_{10}(F)$$

The input-referred noise floor ($N_{\text{floor}}$) over bandwidth $B$ is expressed as:

$$N_{\text{floor}} = -174\text{ dBm/Hz} + NF + 10 \log_{10}(B)$$

### Y-Factor Noise Measurement Method
The Y-Factor method utilizes a calibrated noise source operating in two states: OFF ($T_c \approx T_0$) and ON ($T_h \gg T_0$), defined by Excess Noise Ratio ($ENR$):

$$ENR = \frac{T_h - T_0}{T_0}, \quad Y = \frac{T_h + T_e}{T_0 + T_e} \implies F = \frac{ENR}{Y - 1}$$

---

## 2. Measurement Design & Simulation Summary

### Y-Factor Simulation Results ($lab02\_sim.grc$)
* **At Receiver Gain = 40.0 dB:** $N_{\text{off}} = -41.85\text{ dBFS}$, $N_{\text{on}} = -32.78\text{ dBFS} \implies Y = 9.07\text{ dB} \implies \mathbf{NF \approx 6.50\text{ dB}}$
* **At Receiver Gain = 10.0 dB:** $N_{\text{off}} = -51.40\text{ dBFS}$, $N_{\text{on}} = -51.10\text{ dBFS} \implies Y = 0.30\text{ dB} \implies \mathbf{NF \approx 26.46\text{ dB}}$

### Linearity & Intermodulation Results
* **Single-Tone 1-dB Compression Point ($G = 0.0\text{ dB}$):** $P_{1\text{dB, in}} \approx -23.3\text{ dBm}$ (output reaches $+0.24\text{ dBFS}$).
* **Two-Tone Intermodulation ($G = 0.0\text{ dB}, P_{\text{in}} = -30\text{ dBm}$):** Fundamental output = $-25.79\text{ dBFS}$, IM3 products = $-10.00\text{ dBFS} \implies \mathbf{IIP_3 \approx -37.9\text{ dBm}}$.

### Antenna Frequency Response ($lab02\_antenna\_response\_simulation.py$)
* **Lower Cutoff ($f_L$):** $800.0\text{ MHz}$
* **Upper Cutoff ($f_H$):** $1800.0\text{ MHz}$
* **3-dB Bandwidth ($BW$):** $1000.0\text{ MHz}$

---

## 3. Pre-Lab Prediction Table (Table 6)

| # | Parameter | Prediction | Rationale |
| :--- | :--- | :--- | :--- |
| 1 | $NF$ at Max Gain | $7.0 - 9.0\text{ dB}$ | Dominated by frontend LNA noise figure. |
| 2 | $\Delta NF$ for $-20\text{ dB}$ Gain | $+4.0 \text{ to } +6.0\text{ dB}$ | Lower gain amplifies ADC quantization noise contribution. |
| 3 | $\Delta P_{1\text{dB}}$ for $-10\text{ dB}$ Gain | $+10.0\text{ dB}$ | Prevents pre-ADC saturation, shifting input limit upward. |
| 4 | $Y$-Factor ($NF=7\text{dB}, ENR=15\text{dB}$) | $8.64\text{ dB}$ | $Y = 1 + \frac{ENR}{F} = 1 + \frac{31.62}{5.01} = 7.31$. |
| 5 | $\Delta NF$ with $10\text{ dB}$ Attenuator | $+10.0\text{ dB}$ | Passive loss prior to amplification adds directly to $NF$. |
| 6 | $\Delta P_{\text{IM3}}$ for $+2\text{ dB}$ Input Tone | $+6.0\text{ dB}$ | IM3 products scale with a characteristic $3\text{ dB/dB}$ slope. |
| 7 | Is $IIP_3 - P_{1\text{dB}} \approx 9.6\text{ dB}$? | No | Hard ADC clipping violates 3rd-order polynomial assumptions. |
