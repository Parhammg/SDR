# Lab 02 Pre-Lab Report: Noise Figure, Gain Compression, and Intermodulation

[📥 Download PDF Version of Pre-Lab Report](Prelab2.pdf){ .md-button .md-button--primary }

---

## 1. Summary of Theoretical Concepts

RF receiver architectures are bounded at lower signal levels by thermal and internal component noise, and at upper levels by non-linear gain saturation and intermodulation distortion.

### Noise Figure (NF) and Noise Temperature (Te)
The Noise Factor ($F$) and Noise Figure ($NF$) measure the degradation of the Signal-to-Noise Ratio ($SNR$) as a signal propagates through a receiver processing chain:

$$F = \frac{SNR_{\text{in}}}{SNR_{\text{out}}} = 1 + \frac{T_e}{T_0}, \quad NF = 10 \log_{10}(F)$$

The input-referred noise floor ($N_{\text{floor}}$) over bandwidth $B$ is expressed as:

$$N_{\text{floor}} = -174\text{ dBm/Hz} + NF + 10 \log_{10}(B)$$

### Y-Factor Noise Measurement Method
The Y-Factor method utilizes a calibrated noise source operating in two states: OFF ($T_c \approx T_0$) and ON ($T_h \gg T_0$), defined by Excess Noise Ratio ($ENR$):

$$ENR = \frac{T_h - T_0}{T_0}, \quad Y = \frac{T_h + T_e}{T_0 + T_e} \implies F = \frac{ENR - Y \left(\frac{T_c}{T_0} - 1\right)}{Y - 1}$$

### Third-Order Intercept Point (IIP3) and Gain Compression (P1dB)
Under two-tone excitation at $f_1$ and $f_2$, 3rd-order non-linearities generate intermodulation products (IM3) at $2f_1 - f_2$ and $2f_2 - f_1$.

---

## 2. Theoretical Analysis Highlights

* **Frontend Filter Relocation (Question 1c):** Relocating the $3\text{ dB}$ filter to the frontend alters Friis chain hierarchy (Stage 1 = Filter, Stage 2 = LNA, Stage 3 = Mixer/ADC), resulting in $NF_{\text{new}} \approx 4.95\text{ dB}$.
* **General Y-Factor Relation (Question 2a):** Exact derivation for $T_c \neq T_0$ yields $F = \frac{ENR - Y (T_c/T_0 - 1)}{Y - 1}$.

---

## 3. Measurement Design and Simulation Summary

### Y-Factor Simulation Results ($lab02\_sim.grc$)
* **At Receiver Gain = 40.0 dB ($ENR = 15\text{ dB}$):** $N_{\text{off}} = -41.85\text{ dBFS}$, $N_{\text{on}} = -32.78\text{ dBFS} \implies Y = 9.07\text{ dB} \implies \mathbf{NF \approx 6.50\text{ dB}}$
* **At Receiver Gain = 10.0 dB ($ENR = 15\text{ dB}$):** $N_{\text{off}} = -51.40\text{ dBFS}$, $N_{\text{on}} = -51.10\text{ dBFS} \implies Y = 0.30\text{ dB} \implies \mathbf{NF \approx 26.46\text{ dB}}$
* *Design Note:* At low gain, $Y = 0.30\text{ dB} < 3\text{ dB}$ amplifies readout error sensitivity, justifying the requirement for an $ENR \approx 35\text{ dB}$ source per Table 4 design.

### Linearity and Intermodulation Results
* **Single-Tone 1-dB Compression Point ($G = 0.0\text{ dB}$):** $P_{1\text{dB, in}} \approx -23.3\text{ dBm}$ (output reaches $+0.24\text{ dBFS}$).
* **Two-Tone Intermodulation ($G = 0.0\text{ dB}, P_{\text{in}} = -30\text{ dBm}$):** Fundamental output = $-10.00\text{ dBFS}$, IM3 products = $-25.79\text{ dBFS} \implies \Delta = +15.79\text{ dB} \implies \mathbf{IIP_3 \approx -22.1\text{ dBm}}$ (compared to theoretical $P_{1\text{dB}} + 9.6 = -13.7\text{ dBm}$).

### Antenna Frequency Response
* **Lower Cutoff ($f_L$):** $800.0\text{ MHz}$
* **Upper Cutoff ($f_H$):** $1800.0\text{ MHz}$
* **3-dB Bandwidth ($BW$):** $1000.0\text{ MHz}$

---

## 4. Pre-Lab Prediction Table (Table 6)

| # | Parameter | Prediction | Rationale |
| :--- | :--- | :--- | :--- |
| 1 | $NF$ at Max Gain | $7.0 - 9.0\text{ dB}$ | Dominated by frontend LNA noise figure. |
| 2 | $\Delta NF$ for $-20\text{ dB}$ Gain | $+4.0 \text{ to } +6.0\text{ dB}$ | Lower gain amplifies ADC quantization noise contribution. |
| 3 | $\Delta P_{1\text{dB}}$ for $-10\text{ dB}$ Gain | $+10.0\text{ dB}$ | Prevents pre-ADC saturation, shifting input limit upward. |
| 4 | $Y$-Factor ($NF=7\text{dB}, ENR=15\text{dB}$) | $8.64\text{ dB}$ | $Y = 1 + \frac{ENR}{F} = 1 + \frac{31.62}{5.01} = 7.31$. |
| 5 | $\Delta NF$ with $10\text{ dB}$ Attenuator | $+10.0\text{ dB}$ | Passive loss prior to amplification adds directly to $NF$. |
| 6 | $\Delta P_{\text{IM3}}$ for $+2\text{ dB}$ Input Tone | $+6.0\text{ dB}$ | IM3 products scale with a characteristic $3\text{ dB/dB}$ slope. |
| 7 | Is $IIP_3 - P_{1\text{dB}} \approx 9.6\text{ dB}$? | No | Hard ADC clipping violates 3rd-order polynomial assumptions. |