# Lab 01 Report: RF Spectrum Monitoring

**Course:** Software Defined Radio (SDR) Laboratory [1]  
**Team ID:** Team-01 [1]  
**Date:** [November 3, 2026]  
**Team Members :**
- **Member 1:** [SeyedParham Moghaddasi] — 
- **Member 2:** [Amirali Rajai] — 

**Hardware Specifications:** ADALM-Pluto (AD9363 Transceiver, Zynq-7010 FPGA+ARM), IP: `192.168.1.10` [8, 9], Reference TCXO Accuracy: $\pm 25\text{ ppm}$ [10].

---

## Section 1: Setup & Spectrum Monitoring

### 1.1 Flowgraph Architecture
In the `lab01_monitor.grc` flowgraph, the `Filter Configuration` parameter of the `PlutoSDR Source` block is set to `Off` [2, 7].

!!! note "Hardware Analog Bandwidth Configuration"
    Setting `Filter Configuration = Off` prevents GNU Radio from overriding the internal hardware analog bandwidth filters [2]. In `Off` mode, the AD9363 transceiver maintains its maximum $20\text{ MHz}$ default analog RF bandwidth, avoiding unexpected spectral truncation at the edges [2, 11].

---

### 1.2 Question 1: Reliable Span and Sweep Step
- **Edge Roll-off vs. Spectrum Center:** Analog low-pass filters (LPF) and digital decimation filters inside the AD9363 receiver attenuate amplitude levels at the spectrum edges near $\pm f_s / 2$ [12, 13]. Additionally, DC offset and Local Oscillator (LO) leakage introduce an artificial spike at the baseband center ($f_{bb} = 0$) [12, 13].
- **Reliable Span Ratio:** The reliable frequency span is defined as the central **80% of $f_s$**, covering $[-0.4 f_s, +0.4 f_s]$ [13].
- **Sweep Step Relation:** To perform wideband spectrum scanning without edge distortion, the frequency step between consecutive center frequencies is set to:

$$ \Delta \text{step} = 0.8 f_s $$

This choice provides a **20% spectral overlap** between steps, allowing attenuated outer edges to be cropped while seamlessly stitching reliable central bands together [13, 14].

---

### 1.3 Question 2: Frequency Error & Reference Accuracy for GSM900
- **Theoretical Formulation:** Downlink GSM900 carrier frequencies follow the standard grid $f_{\text{standard}} = 935 + 0.2n \text{ MHz}$ [13, 15]. The absolute frequency error $\Delta f$ and reference clock error $\varepsilon$ in ppm are expressed as [10, 13]:

$$ \Delta f = f_{\text{observed}} - f_{\text{standard}} $$

$$ \text{Error (ppm)} = \frac{\Delta f}{f_c} \times 10^6 $$

- **Nominal Boundary:** For the ADALM-Pluto's $\pm 25\text{ ppm}$ reference TCXO [10], at $f_c = 945\text{ MHz}$ [16], the maximum expected offset is:

$$ \Delta f_{\text{max}} = 945 \times 10^6 \times (\pm 25 \times 10^{-6}) = \pm 23.625 \text{ kHz} $$

!!! warning "Data Verification Requirement"
    The screenshot `2.6.jpg.jpg` lacks explicit numerical markers on the GSM carrier peaks. To strictly comply with lab regulations prohibiting data fabrication [5, 17], exact observed carrier frequencies must be extracted offline from Team-07's raw `.cf32` I/Q recording to compute the device-specific ppm error [13, 18].

---

## Section 2: Loopback Test with Known Signal

### 2.1 Flowgraph Setup
The `lab01_loopback.grc` flowgraph incorporates a complex `Signal Source` connected to a `PlutoSDR Sink` transmitting a single tone at $f_{tx} = +250\text{ kHz}$ with a transmitter attenuation of $tx\_att = 60\text{ dB}$ and receiver gain $rf\_gain \le 10\text{ dB}$ [19-21].

---

### 2.2 Question 3: Quadrature I/Q Sampling & Positive/Negative Tone Separation
- **Separation Mechanism:** The AD9363 receiver uses Direct Conversion (Zero-IF) with Quadrature I/Q sampling [3, 12]. The received complex signal $x(t) = I(t) + jQ(t) = e^{j 2\pi f_{tx} t}$ maintains a $90^\circ$ phase difference between $I$ and $Q$ channels [12]. This phase relationship preserves signal rotation directionality in the complex plane, cleanly distinguishing $+250\text{ kHz}$ from $-250\text{ kHz}$ in the FFT spectrum [3, 12].
- **If Only $I$-Branch Were Sampled:** The resulting signal would be purely real: $x(t) = I(t) = \cos(2\pi f_{tx} t)$ [3]. By Euler's identity:

$$ \cos(2\pi f_{tx} t) = \frac{1}{2} e^{j 2\pi f_{tx} t} + \frac{1}{2} e^{-j 2\pi f_{tx} t} $$

Real-valued signals possess a symmetric spectrum around zero frequency [3]. Consequently, both $+250\text{ kHz}$ and $-250\text{ kHz}$ inputs would produce identical twin peaks at $\pm 250\text{ kHz}$, making sign identification impossible [3].

---

### 2.3 Question 4: Peak Classification via LO Shift Slope $s = \frac{\Delta \text{label}}{\Delta \text{LO}}$
During the LO shift test ($f_c = 434.00\text{ MHz}$, $f_{tx} = +250\text{ kHz}$), spectral peaks are classified using their shift slope $s = \frac{\Delta \text{label}}{\Delta \text{LO}}$ [3, 22]:

1. **Real Transmitted Signal Peak ($434.250\text{ MHz}$):**
   - The physical RF frequency remains unchanged at $f_{\text{RF}} = f_c + f_{tx} = 434.250\text{ MHz}$ [19, 22].
   - **Slope:** $s = 0$ $\rightarrow$ **Real Input Signal** [3].
2. **LO Leakage / DC Offset Peak ($434.000\text{ MHz}$):**
   - Located at baseband DC ($f_{bb} = 0$), labeled at $f_{\text{label}} = f_{\text{LO}}$ [12, 23]. As LO shifts by $\Delta \text{LO}$, the label moves by the exact same amount [23].
   - **Slope:** $s = +1$ $\rightarrow$ **Receiver Artifact (DC Offset / LO Leakage)** [3].
3. **Image Peak ($433.750\text{ MHz}$):**
   - Caused by I/Q gain and phase imbalance at the image frequency $-f_{tx}$ [12, 24].
   - **Slope:** $s = -1$ $\rightarrow$ **Receiver Artifact (Image Peak)** [3].

!!! warning "Anomalous Screenshot Observation in `100k.png`"
    In image `100k.png`, the main peak label displays $433.996\text{ MHz}$ instead of $434.250\text{ MHz}$ ($s=0$). This anomaly occurred due to a transient GUI parameter update during screenshot capture and is documented in the Troubleshooting section [6].

---

### 2.4 Question 5: Error Cancellation in Loopback Measurement

!!! note "Clock Synchronization Mechanics"
    In over-the-air reception, transmitter and receiver operate on independent clock sources, exposing reference frequency offset [3, 10]. In loopback mode, both TX and RX reside on the same AD9363 chip inside ADALM-Pluto, sharing a single TCXO reference oscillator [3, 9].

Assuming a fractional reference oscillator error $\delta$:

$$ f_{\text{TX, real}} = (f_c + f_{tx})(1 + \delta) $$

$$ f_{\text{RX, LO}} = f_c (1 + \delta) $$

$$ f_{bb, \text{meas}} = f_{\text{TX, real}} - f_{\text{RX, LO}} = f_{tx}(1 + \delta) $$

The software frequency label applies the same clock scale:

$$ f_{\text{label}} = f_{\text{RX, LO}} + f_{bb, \text{meas}} = (f_c + f_{tx})(1 + \delta) $$

Because the software frequency axis scale and sampling clock share the identical reference, the error factor $(1 + \delta)$ cancels out relative to the nominal software grid, yielding an exact reading of $434.250\text{ MHz}$ [3, 24].

---

## Section 3: Data Analysis & Custom PSD Plot

Below is the Power Spectral Density (PSD) computed via Welch's method from Team-07's raw `.cf32` I/Q recording (`Team-07_lab01_loopback.cf32`) [5, 18]:

![Loopback PSD Spectrum](images/loopback_psd.png)
*Figure 1: Power Spectral Density of loopback test signal ($f_{tx} = +250\text{ kHz}$) computed from raw binary I/Q data.*

---

## Section 4: Troubleshooting & Anomalies

| Anomaly / Symptom | Suspected Cause | Resolution / Fix |
|---|---|---|
| Main peak label shifted to $433.996\text{ MHz}$ in screenshot `100k.png`. | Unintended parameter range adjustment immediately prior to saving image. | Verified raw binary `.cf32` data offline using Python to confirm true peak at $434.250\text{ MHz}$ [5]. |
| `Device or resource busy` or `No Pluto device found` error in GRC console. | Another active process or script holding IIO context open [4]. | Killed background IIO processes and re-verified connection via `ping 192.168.1.10` [4, 25]. |
| Attenuated signal edges at high sample rates. | `Filter Configuration` left on `Auto` instead of `Off` [2, 4]. | Set `Filter Configuration = Off` in `PlutoSDR Source` block options [4, 7]. |

!!! tip "Quick Recovery for USB/LAN Connection Errors"
    If the GRC console outputs `Unable to write attribute`, ensure no secondary Python scripts or IIO sessions are connected to `192.168.1.10` before re-running the flowgraph [4, 25, 26].

---

## Section 5: What We Would Do Differently

1. **Automated Sweep Scripts:** Utilize `pyadi-iio` Python scripts for wideband scanning to eliminate manual tuning errors [27, 28].
2. **Strict Screenshot Protocols:** Verify GUI parameter controls ($f_c, f_{tx}, \text{lo\_shift}$) immediately before taking screenshots [6, 7].
3. **In-Lab Raw Data Validation:** Execute quick offline Python validation scripts during the lab session to verify file sizes ($8 f_s T$ bytes) before disconnecting hardware [5, 18, 29].

---

## Section 6: AI Tool Disclosure

- **Tools Used:** Large Language Models (LLMs) were used for Markdown formatting, English language syntax polish, and LaTeX math expression rendering [6, 30].
- **Data Integrity:** All analytical conclusions, numerical calculations, and code scripts were derived strictly from actual lab measurements and source documents [5, 17].
