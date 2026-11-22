# :material-radio-fm: Pre-Lab Report 3: FM Radio, Stereo MPX, and RDS

[:material-file-pdf-box: Download Pre-Lab Report (PDF)](PreLAB3.pdf){ .md-button .md-button--primary target="_blank" }

!!! abstract "Pre-Lab Metadata"
    * **Course:** Software-Defined Radio (SDR) Laboratory
    * **Topic:** Coherent and Non-Coherent Demodulation, Multiplex Stereo, and RDS Data Decoding

## Task 1: One-Page Literature Summary

### 1. Why FM is More Immune to Noise than AM

In Amplitude Modulation (AM), information is encoded directly into the instantaneous amplitude of the high-frequency carrier. Additive White Gaussian Noise (AWGN) from the channel adds algebraically to this envelope, making it mathematically impossible to eliminate noise without altering the original message.

Conversely, in Frequency Modulation (FM), the envelope amplitude remains strictly constant ($A$), and the message is encoded entirely within the instantaneous phase and frequency:

$$
s(t) = A \cos\!\big(2\pi f_c t + \varphi(t)\big)
$$

This structural property provides two fundamental noise-rejection mechanisms:

1. **Amplitude Hard-Limiting:** A receiver limiter (or in discrete SDR, taking the angular phase $\arg(\cdot)$) strips away all spurious amplitude variations caused by channel fading, atmospheric interference, and thermal noise without distorting the underlying message.
2. **Bandwidth-for-SNR Trade-Off:** Above threshold, the post-detection output signal-to-noise ratio ($\text{SNR}_o$) scales quadratically with the frequency deviation ratio $(\Delta f / W)^2$:

$$
\text{SNR}_o \propto \left(\frac{\Delta f}{W}\right)^2 \text{CNR}
$$

Increasing the frequency deviation widens the occupied spectrum, which in turn drastically suppresses detected baseband noise.

### 2. The Cost of the FM Advantage

The superior noise rejection of FM is traded directly against **substantial radio spectrum consumption**. According to Carson's bandwidth rule:

$$
B_T \approx 2(\Delta f + f_{\max})
$$

While a standard AM voice transmission occupies only $2W \approx 10\text{ kHz}$, commercial Wideband FM (WFM) allocates roughly $200\text{ kHz}$ per broadcast channel—an approximately twentyfold increase in spectrum usage.

### 3. The Threshold Effect and Catastrophic Breakdown

The quadratic noise suppression in FM holds only when the input Carrier-to-Noise Ratio ($\text{CNR}$) exceeds a critical threshold ($\text{CNR}_{\text{th}} \approx 10\text{ dB}$). When $\text{CNR}$ falls below this boundary:

* The noise phasor occasionally exceeds the carrier phasor in magnitude, sweeping the resultant vector around the origin and inducing a full $2\pi$ phase wrap-around (phase slip).
* Because the discriminator differentiates phase to extract audio, this rapid $2\pi$ step manifests as a sharp Dirac-like impulse in time, heard as an audible **"click"** or "pop".
* As the signal weakens further, the arrival rate of clicks accelerates exponentially, destroying phase coherence and driving the output $\text{SNR}_o$ into a steep, catastrophic cliff. Unlike AM, where audio degrades gradually into background static, an FM signal drops off abruptly from near-flawless fidelity into complete unintelligibility.

## Task 2: Theoretical Problems & Analytical Solutions

### 1. Single-Tone Bessel Expansion and Carson's Bandwidth

For a single-tone message $m(t) = \cos(2\pi f_m t)$, the instantaneous phase is:

$$
\varphi(t) = 2\pi\Delta f \int_0^t \cos(2\pi f_m \tau)\,d\tau = \frac{\Delta f}{f_m} \sin(2\pi f_m t) = \beta \sin(2\pi f_m t)
$$

where $\beta = \frac{\Delta f}{f_m}$ is the modulation index. The real bandpass signal is expressed as:

$$
s(t) = \operatorname{Re}\!\left\{ A e^{j(2\pi f_c t + \beta \sin(2\pi f_m t))} \right\} = A \cdot \operatorname{Re}\!\left\{ e^{j 2\pi f_c t} \cdot e^{j \beta \sin(2\pi f_m t)} \right\}
$$

Applying the Jacobi-Anger expansion identity:

$$
e^{j \beta \sin(\theta)} = \sum_{n=-\infty}^{+\infty} J_n(\beta) e^{j n \theta}
$$

Substituting $\theta = 2\pi f_m t$ and extracting the real part yields Equation (2):

$$
s(t) = A \sum_{n=-\infty}^{+\infty} J_n(\beta) \cos\!\big(2\pi(f_c + n f_m)t\big)
$$

**Carson's Bandwidth Calculation ($B_T \approx 2(\Delta f + f_{\max})$):**

* **Mono broadcast** ($f_{\max} = 15\text{ kHz}$, $\Delta f = 75\text{ kHz}$):

$$
B_{T,\text{mono}} = 2(75 + 15) = 180\text{ kHz}
$$

* **Stereo multiplex** ($f_{\max} = 53\text{ kHz}$, $\Delta f = 75\text{ kHz}$):

$$
B_{T,\text{stereo}} = 2(75 + 53) = 256\text{ kHz}
$$

* **Comparison with Broadcast Channel Spacing:** Commercial FM channels are spaced by $200\text{ kHz}$. The **$180\text{ kHz}$ mono transmission** fits comfortably within the $200\text{ kHz}$ channel allocation and is closest to this standard grid.

### 2. Carrier Nulls and Deviation Calibration

The amplitude of the center carrier line ($f_c$) is governed by the zero-order Bessel function $J_0(\beta)$. The carrier completely disappears when $J_0(\beta) = 0$. The first two positive roots of $J_0(\beta)$ are:

$$
\beta_1 \approx 2.4048 \approx 2.405, \quad \beta_2 \approx 5.5201 \approx 5.520
$$

For a test tone of $f_m = 1\text{ kHz}$, the corresponding frequency deviations are:

$$
\Delta f_1 = \beta_1 f_m = 2.405 \times 1\text{ kHz} = 2405\text{ Hz}
$$

$$
\Delta f_2 = \beta_2 f_m = 5.520 \times 1\text{ kHz} = 5520\text{ Hz}
$$

* **Calibration Procedure:** A pure $1\text{ kHz}$ sinusoidal audio tone is fed into the FM transmitter while monitoring the RF output on a spectrum analyzer (or an SDR FFT sink). Starting from zero, the input audio amplitude is slowly increased until the center carrier peak at $f_c$ drops into a sharp null and vanishes. At this exact point, $\beta = 2.405$, confirming that the transmitter's frequency deviation is calibrated precisely to $\Delta f = 2405\text{ Hz}$ without requiring a specialized deviation meter.

### 3. Discrete Phase Discriminator Linearity and Limits

The numerical discriminator computes the angular difference between two successive complex samples:

$$
y[n] = \arg\!\big(x[n] x^*[n-1]\big) = \arg\!\left(e^{j(\varphi[n] - \varphi[n-1])}\right)
$$

Because the principal branch of $\arg(\cdot)$ is constrained to $(-\pi, +\pi]$, the phase difference between consecutive samples must not wrap around:

$$
|\varphi[n] - \varphi[n-1]| = |k_f m[n]| < \pi
$$

Since $|m[n]| \le 1$, this condition reduces to:

$$
k_f = \frac{2\pi\Delta f}{f_s} < \pi \implies \Delta f < \frac{f_s}{2}
$$

* **Maximum Detectable Deviation at $f_s = 240\text{ kHz}$:**

$$
\Delta f_{\max} = \frac{240\text{ kHz}}{2} = 120\text{ kHz}
$$

* **Effect of Entering $2\Delta f$ in Receiver Gain:** The discriminator gain is $\text{Gain} = \frac{f_s}{2\pi \Delta f_{\text{rx}}}$. If the receiver mistakenly assumes $\Delta f_{\text{rx}} = 2\Delta f_{\text{actual}}$, the gain is halved:

$$
\hat{m}[n] = \frac{f_s}{2\pi (2\Delta f)} \cdot \left(\frac{2\pi\Delta f}{f_s} m[n]\right) = \frac{1}{2} m[n]
$$

The output audio amplitude is attenuated by exactly $50\%$ (a $6.02\text{ dB}$ loss in volume), while remaining completely linear and free of distortion.

### 4. Comparison: Discriminator vs. PLL Frequency Detector

| Comparison Metric | Non-Coherent Discriminator (`Quadrature Demod`) | Coherent PLL (`PLL Frequency Detector`) |
| :--- | :--- | :--- |
| **Design Parameters** | Only linear scaling gain: $\text{Gain} = \frac{f_s}{2\pi\Delta f}$ | `Loop Bandwidth`, damping factor, `Min/Max Phase` |
| **Performance Above Threshold** | Completely linear; parabolic output noise PSD ($f^2$) | Identical to discriminator; linear frequency tracking |
| **Performance Near Threshold** | Exhibits sudden click impulses around $\text{CNR} \approx 10\text{ dB}$ | **Threshold Extension:** Delays threshold by $2\text{ to }3\text{ dB}$ |
| **Carrier Offset Sensitivity** | Highly robust; carrier offset $\delta f$ produces a harmless constant DC offset | Vulnerable; if $\delta f$ exceeds lock range, the loop loses lock entirely |
| **Computational Complexity** | Extremely low (one complex multiply + one $\arg(\cdot)$) | Moderate to high (phase error, loop filter, NCO updates) |

* **Why the PLL Threshold Advantage Increases with Large $\beta$:** When $\beta \gg 1$, the Carson bandwidth $B_T \approx 2\Delta f$ is vastly wider than the baseband information bandwidth $W$. A non-coherent discriminator must accept all thermal noise across the entire transmission bandwidth $B_T$. In contrast, the PLL acts as a dynamic tracking filter whose effective noise bandwidth $B_L$ is matched only to the message rate ($B_L \ll B_T$). By rejecting out-of-band noise prior to nonlinear phase detection, the PLL suppresses phase slips, significantly improving threshold performance for wideband signals.

### 5. FM Improvement Trade-off Under Constant Received Power

Substituting $\text{CNR} = \frac{P_c}{N_0 B_T}$ into Equation (8):

$$
\text{SNR}_o = \frac{3}{2}\left(\frac{\Delta f}{W}\right)^2 \frac{B_T}{W} \left(\frac{P_c}{N_0 B_T}\right) = \frac{3}{2}\frac{(\Delta f)^2}{W^3}\frac{P_c}{N_0}
$$

Assuming constant received carrier power $P_c$ and noise density $N_0$, doubling the frequency deviation ($\Delta f \to 2\Delta f$) yields:

$$
\text{SNR}_{o,\text{new}} = 4 \times \text{SNR}_{o,\text{old}} \implies 10\log_{10}(4) \approx 6.02\text{ dB improvement}
$$

* **Threshold Power Shift:** The threshold boundary occurs at a constant carrier-to-noise ratio:

$$
\text{CNR}_{\text{th}} = \frac{P_{c,\text{th}}}{N_0 B_T} = 10\text{ dB} = 10 \implies P_{c,\text{th}} = 10 N_0 B_T
$$

Because $B_T \approx 2(\Delta f + W)$, doubling $\Delta f$ approximately doubles the occupied channel bandwidth $B_T$ (for wideband FM). Consequently:

$$
\frac{P_{c,\text{th},\text{new}}}{P_{c,\text{th},\text{old}}} \approx \frac{B_{T,\text{new}}}{B_{T,\text{old}}} \approx 2 \implies 10\log_{10}(2) \approx 3.01\text{ dB}
$$

To remain above the noise threshold, the transmitter must supply approximately **$3\text{ dB}$ more RF power**.

### 6. Carrier Frequency Offset Analysis

If the received carrier possesses an unknown frequency offset $\delta f$, the instantaneous frequency becomes:

$$
f_i(t) = f_c + \delta f + \Delta f\,m(t)
$$

The discrete sample phase difference across interval $T_s = 1/f_s$ is:

$$
\Delta \varphi[n] = 2\pi (f_i - f_c) T_s = \frac{2\pi}{f_s}\big(\delta f + \Delta f\,m[n]\big)
$$

Applying the discriminator gain $\text{Gain} = \frac{f_s}{2\pi\Delta f}$:

$$
\hat{m}[n] = \frac{f_s}{2\pi\Delta f} \cdot \frac{2\pi}{f_s}\big(\delta f + \Delta f\,m[n]\big) = m[n] + \frac{\delta f}{\Delta f}
$$

The carrier offset appears as a pure, frequency-independent DC bias equal to $\frac{\delta f}{\Delta f}$.

* **Numerical Offset Calculation at $434\text{ MHz}$ ($30\text{ ppm}$ tolerance):**

$$
\delta f = 434\text{ MHz} \times 30 \times 10^{-6} = 13.02\text{ kHz}
$$

* **Impact on a Narrowband Channel ($B_T = 16\text{ kHz}$):** A narrowband channel filter centered at baseband has a one-sided passband edge of only:

$$
\frac{B_T}{2} = \frac{16\text{ kHz}}{2} = 8\text{ kHz}
$$

Because $\delta f = 13.02\text{ kHz}$ exceeds the $8\text{ kHz}$ cutoff, the entire FM spectrum is shifted out of the filter's passband, causing severe attenuation, harmonic distortion, and complete loss of reception.

## Task 3: Rate Chain and Parameter Design

The parameters for the first session design table are determined using the Hamming window tap approximation ($N \approx 3.3 \frac{f_s}{\Delta f_{\text{tr}}}$):

### Table 3: Session 1 Design Table

| Quantity / Block Parameter | Designed Value | Numerical Justification & Governing Formula |
| :--- | :--- | :--- |
| **Input rate, decimation factors, and intermediate rates down to 48 kHz audio** | $f_{s,\text{in}} = 2.4\text{ MS/s}$<br>Stage 1 Decimation: $\downarrow 10$<br>Demod Rate: $240\text{ kHz}$<br>Stage 2 Decimation: $\downarrow 5$<br>Audio Rate: $48\text{ kHz}$ | Per Figure 5:<br>$2.4\text{ MS/s} / 10 = 240\text{ kHz}$ covers the composite MPX spectrum ($60\text{ kHz}$). Decimating by $5$ ($240 / 5 = 48\text{ kHz}$) matches standard sound cards. |
| **Channel filter cutoff, transition width, and taps ($N$) for WFM and NBFM** | **WFM:** $f_{\text{cut}} = 100\text{ kHz}$, $\Delta f_{\text{tr}} = 20\text{ kHz}$, $N \approx 396$<br>**NBFM:** $f_{\text{cut}} = 8\text{ kHz}$, $\Delta f_{\text{tr}} = 4\text{ kHz}$, $N \approx 1980$ | Evaluated at $f_s = 2.4\text{ MS/s}$ using $N \approx 3.3 \frac{f_s}{\Delta f_{\text{tr}}}$:<br>WFM: $3.3 \times \frac{2400}{20} = 396$<br>NBFM: $3.3 \times \frac{2400}{4} = 1980$ |
| **Demodulator Gain & Modulator Sensitivity for $\Delta f = 5\text{ kHz}$** | **Demod Gain:** $7.6394$<br>**Mod Sensitivity:** $0.1309\text{ rad/sample}$ | Evaluated at $f_s = 240\text{ kHz}$:<br>$\text{Gain} = \frac{240\times 10^3}{2\pi \times 5000} \approx 7.6394$<br>$\text{Sensitivity} = \frac{2\pi \times 5000}{240\times 10^3} \approx 0.1309$ |
| **PLL Loop Bandwidth and Phase Limits for WFM and NBFM** | **WFM:** $\text{Loop BW} = 0.393$, Limits: $\pm\pi$<br>**NBFM:** $\text{Loop BW} = 0.039$, Limits: $\pm 0.15$ | From Eq. (7) where $B_L \approx 1.06 \times LB \times f_s$ ($f_s = 240\text{ kHz}$):<br>WFM ($B_L \approx 100\text{ kHz}$): $LB = \frac{100}{1.06 \times 240} \approx 0.393$<br>NBFM ($B_L \approx 10\text{ kHz}$): $LB = \frac{10}{1.06 \times 240} \approx 0.039$ |
| **Transmitter attenuation to achieve $-60\text{ dBm}$ at receiver input** | $36.5\text{ dB}$ Pluto internal attenuation | Peak output is $+7\text{ dBm}$ with $30\text{ dB}$ external pad and $0.5\text{ dB}$ cable loss:<br>$-60 = +7 - \text{Att}_{\text{TX}} - 30 - 0.5 \implies \text{Att}_{\text{TX}} = 36.5\text{ dB}$ |

## Task 4: Pre-Lab Experimental Predictions

### Table 4: Session 1 Prediction Table

| Row | Physical Quantity | Predicted Value | Derivation / Notes |
| :---: | :--- | :---: | :--- |
| **1** | Two frequency deviations causing carrier null for $f_m = 1\text{ kHz}$ | $2405\text{ Hz}$ and $5520\text{ Hz}$ | Evaluated from $J_0(\beta) = 0$ roots ($\beta = 2.405$ and $\beta = 5.520$) |
| **2** | Occupied bandwidth of NBFM link ($\Delta f = 5\text{ kHz}$, $f_m = 3\text{ kHz}$) | $16\text{ kHz}$ | Carson's rule: $B_T \approx 2(5 + 3) = 16\text{ kHz}$ |
| **3** | Receiver input power with $40\text{ dB}$ TX attenuation | $-63.5\text{ dBm}$ | $+7\text{ dBm} - 40\text{ dB} - 30\text{ dB} - 0.5\text{ dB} = -63.5\text{ dBm}$ |
| **4** | Carrier frequency offset at $434\text{ MHz}$ ($30\text{ ppm}$ total error) | $\pm 13.02\text{ kHz}$ | $\delta f = 434\text{ MHz} \times 30\times 10^{-6} = \pm 13020\text{ Hz}$ |
| **5** | Minimum PLL `Loop Bandwidth` yielding distortion-free WFM reception | $\approx 0.20\text{ to }0.35$ | Corresponds to tracking baseband stereo frequencies up to $53\text{ kHz}$ |

## Task 5: Risk Analysis and Failure Mitigation

!!! danger "1. Hardware Damage via Direct RF Overdrive (Critical Safety Risk)"
    * **Failure Mechanism:** Connecting the PlutoSDR TX port directly to the RX port without the mandatory $30\text{ dB}$ hardware attenuator, or setting the software internal attenuation to $0\text{ dB}$.
    * **Consequence:** Power delivered to the receiver exceeds the maximum absolute damage rating ($-10\text{ dBm}$), permanently destroying the receiver's Low-Noise Amplifier (LNA).
    * **Mitigation Protocol:** Both team members must physically verify that the inline $30\text{ dB}$ coaxial attenuator is connected to the RX port before executing the flowgraph, and verify `Attenuation TX1 (dB)` $\ge 35\text{ dB}$ in `PlutoSDR Sink`.

!!! warning "2. Audio Distortion via Overly Constrained PLL Bandwidth"
    * **Failure Mechanism:** Setting the `Loop Bandwidth` parameter of the `PLL Frequency Detector` too small (e.g., $< 0.05$) to suppress noise.
    * **Consequence:** The loop phase response becomes too slow to track rapid frequency deviations, causing cycle slips, loss of lock, and severe audio clipping/clicking.
    * **Mitigation Protocol:** Initialize with a conservative bandwidth ($LB \approx 0.35$) and reduce in small increments while monitoring the FFT sink and audio output.

!!! warning "3. De-emphasis Standard Mismatch"
    * **Failure Mechanism:** Leaving the `FM Deemphasis` block at its default GNU Radio value of $\tau = 75\ \mu\text{s}$ (North American / South Korean standard).
    * **Consequence:** Local Iranian and European FM broadcasts use a $\tau = 50\ \mu\text{s}$ pre-emphasis curve; applying $75\ \mu\text{s}$ excessively attenuates high frequencies, producing muffled audio.
    * **Mitigation Protocol:** Explicitly set the `Tau` parameter of `FM Deemphasis` to `50e-6` ($50\ \mu\text{s}$) per ITU-R BS.450 Region 1.