# HLS native-triplet acquisition: primary-source evidence

Status: SOURCE AUDIT, 2026-09-29. No audio was downloaded, decoded, scored, or inspected for this source review. Signal measurements and release-byte verification belong to `HLS_NATIVE_TRIPLET_AUDIT.md`; this document does not substitute literature claims for those measurements.

## Version and release distinction

The [author repository README](https://github.com/Torabiy/HLS-CMDS/blob/ad9a5b08c05f31a61096fec4ab4fde6b0ff1f45c/README.md) identifies `Dataset.v2` as 535 recordings: 50 standalone heart, 50 standalone lung, and 145 mixtures with 145 corresponding heart and 145 lung recordings. It separately identifies v1 as 210 recordings, including 110 mixtures without the additional matched-reference inventory. Repository HEAD was `ad9a5b08c05f31a61096fec4ab4fde6b0ff1f45c` when checked. Dataset.v2 stores metadata CSVs and split Mix1/2/3 archives. These GitHub version labels must not be confused with the [Mendeley release DOI version `.3`](https://data.mendeley.com/datasets/8972jxbpmp/3).

Do not use the older [2024 arXiv preprint](https://arxiv.org/abs/2410.03280) to infer the expanded release's count or missing triplet protocol. The final publication added material directly relevant to correspondence.

## Final publication: decisive acquisition evidence

The [2025 paper](https://doi.org/10.1109/IEEEDATA.2025.3566012), pp. 136–139, reports:

- CAE Juno/Maestro plays repeated, patient-derived prerecorded sounds.
- Each mixture captures both enabled sources; its isolated references were recorded separately without moving the stethoscope. The authors infer equivalence to simultaneous acquisition from replay, not three-channel simultaneous capture.
- Device: Littmann CORE, not Thinklabs. Heart/Bell, lung/Diaphragm, mixture/Midrange; 15-second recordings; Eko Bluetooth/mobile/cloud export.
- Quiet environment, steady contact and pressure precautions; additional preprocessing bandpass filtering.
- IDs `M0001`–`M0145`, with matching `H`/`L` numerical IDs; ten heart and six lung types, all 60 combinations claimed.
- Software: Maestro 1.3, Eko iOS 5.11.1. Natural physiological heart–lung coupling is not reproduced.

The paper does not disclose per-triplet order/time gaps, phase reset/synchronization, clock drift, gain settings, AGC/compression coefficients, post-filter coefficients, or per-file filter-state logs. Repeated playback is not itself proof of waveform additivity. Full text was inspected through the [author publication page](https://www.researchgate.net/publication/391390555_Descriptor_Heart_and_Lung_Sounds_Dataset_Recorded_From_a_Clinical_Manikin_Using_Digital_Stethoscope_HLS-CMDS); the IEEE landing page required JavaScript verification.

## Earlier protocol details and quantitative-specification caution

The [2024 primary preprint](https://arxiv.org/pdf/2410.03280), pp. 2–5, describes a sitting simulator, anterior speakers, standard heart landmarks and bilateral upper/middle/lower anterior lung landmarks. Its standalone collection order was heart-only, then lung-only, then both sources. **This is not a verified within-triplet acquisition order for the expanded release.** It describes cardiac/ventilation synchronization within the simulator, not synchronization to WAV sample zero.

Its Table 1 lists Bell 20–200 Hz, Diaphragm 100–500 Hz and Midrange 50–500 Hz; the respective notes mention high-frequency rolloff, low-frequency rolloff and a 550 Hz peak. These are reported specifications, not measured release transfer functions. The stated 22,050 Hz recording rate conflicts with the project's previously verified released WAV contract. Do not resample data or assert an undocumented conversion history to reconcile this discrepancy. Band endpoints alone cannot specify phase, gain, filter order or an invertible correction.

## Official manufacturer cross-check

The [Littmann CORE FAQ](https://www.littmann.com/en-us/home/core-digital-stethoscope/) describes a Cardiology IV plus CORE attachment. Current and prior Eko-app filter names are Wide/Cardiac/Pulmonary, not the paper's terminology. The FAQ also states that:

- diaphragm contact pressure changes the relative emphasis of low and high frequencies;
- digital-unit volume buttons change earpiece loudness, **not Eko recording volume**;
- active noise cancellation is switchable, with default off;
- amplification is specified at peak frequency, not as a calibrated constant recording gain.

Thus changing listening volume is not established as the cause of measured amplitude mismatch. Neither a device capability nor default establishes the actual switch state of any historical recording. Current documentation cannot retrospectively identify historical firmware/filter coefficients.

The [official Eko manual index](https://support.ekohealth.com/hc/en-us/articles/8890312188443-User-Manuals) explicitly includes Littmann CORE under CORE Attachment documentation. The linked [CORE second-generation manual, LBL071 Rev. 8.0](https://cdn.shopify.com/s/files/1/0715/6111/files/CORE_User_Manual_LBL071_6dd2a357-9b42-4942-b815-c989be18e528.pdf?v=1790017954), printed p. 21, specifies a **4,000 Hz A/D rate** and **20–2,000 Hz frequency response**. This table was rendered and visually checked. It corroborates the plausibility of the released 4 kHz contract, but does not establish the dataset's complete acquisition/export history. Thinklabs and CORE 500 response curves are not applicable substitutes for this device.

## Targeted investigation of the 110/145 release boundary

After signal forensics identified a different mathematical regime among the eligible IDs above 110, the original repository history and release documentation were checked specifically for an appended-mixture generation procedure. The [March 11, 2025 upload](https://github.com/Torabiy/HLS-CMDS/commit/491f590b55eb2fc7123b0e67fef7ad3c7b48d7f1) introduced the v2 archives and CSVs together. The [subsequent README revision](https://github.com/Torabiy/HLS-CMDS/commit/616b4f6503e5ba3bfe3b8b93265e4681876a2aaa) documented 145 mixtures/535 files while retaining the v1 110-mixture/210-file description. Later revisions explain split ZIP extraction and change the Mendeley version link, not signal generation.

The [official Zenodo README](https://zenodo.org/records/15376628/files/HLS_CMDS_README.txt), the [Mendeley v3 publication metadata](https://api.datacite.org/dois/10.17632/8972jxbpmp.3), final paper, and public author repository do **not** disclose a different creation/normalization procedure for IDs 111–145. The repository's inspected executable material is visualization/notebook code, not a documented mixture-generation pipeline. There were no GitHub release assets or issue explanations supplying that missing procedure when checked. Zenodo's web record calls itself Version v1, whereas GitHub calls the 535-file inventory Dataset.v2; retain the immutable record and file identities rather than treating these different labels as a single version number.

**Observed chronology:** the earlier release had 110 mixtures and the expanded one has 145. **Measured elsewhere in this audit:** all 27 *eligible non-test* rows above 110 are almost exactly a common positive gain times the same-time reference sum. **Inference:** this is consistent with normalized digital addition or another mathematically equivalent preparation. **Unknown:** the actual creation history of those files. Neither the chronology nor the signal identity proves the author's generation procedure. The eight excluded late rows were not opened, so this finding must not be generalized to all 35 appended IDs. Call the usable population the **non-test common-gain additive release subset**, not verified independently acquired native acoustic mixtures.

## Consequences for the forensic model (inference, not measured results)

The defensible acquisition hypothesis is separately recorded replay through potentially different recording domains:

`m = G_m(H_phase_a + L_phase_b) + n_m`

`h_ref = G_h(H_phase_c) + n_h`, `l_ref = G_l(L_phase_d) + n_l`.

This motivates independently testing timing, source replay, and transfer response. It does not guarantee any linear map exists. A fit to a mixture alone cannot uniquely identify true component-domain targets when references overlap spectrally, recording gains are unknown, or replay differs. A flexible per-record filter can absorb source leakage and noise; such a reconstruction is not ground truth. Transfer correction therefore needs restricted capacity, non-test held-out groups, and explicit correspondence diagnostics before training.

No source examined establishes a calibrated common gain, phase-aligned references, AGC absence/presence, or a known noise-only interval. Quiet acquisition is not a measured zero noise floor. Those quantities must remain unknown unless the non-test forensic measurements support a bounded conclusion.

## Access and scope notes

Public README, published full text, Littmann FAQ and official Eko manual were readable without sign-in. The IEEE landing page presented JavaScript anti-bot verification; a direct ResearchGate PDF request returned HTTP 403, while its public article full text remained readable. No authentication was requested or bypassed. Mendeley web rendering exposed only a shell during this source pass; do not treat that as local release verification. No HLS audio/archive was fetched by this source-review task.

## References (APA 7)

Torabi, Y., Shirani, S., & Reilly, J. P. (2025). Descriptor: Heart and lung sounds dataset recorded from a clinical manikin using digital stethoscope (HLS-CMDS). *IEEE Data Descriptions, 2*, 133–140. https://doi.org/10.1109/IEEEDATA.2025.3566012

Torabi, Y., Shirani, S., & Reilly, J. P. (2024). *Manikin-recorded cardiopulmonary sounds dataset using digital stethoscope* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2410.03280

Torabi, Y. (n.d.). *HLS-CMDS* [Repository; commit ad9a5b08c05f31a61096fec4ab4fde6b0ff1f45c]. GitHub. https://github.com/Torabiy/HLS-CMDS

Littmann. (n.d.). *Littmann CORE digital stethoscope*. Retrieved September 29, 2026, from https://www.littmann.com/en-us/home/core-digital-stethoscope/

Eko Health. (n.d.). *CORE user manual: Model 2nd generation* (LBL071, Rev. 8.0). https://cdn.shopify.com/s/files/1/0715/6111/files/CORE_User_Manual_LBL071_6dd2a357-9b42-4942-b815-c989be18e528.pdf?v=1790017954
