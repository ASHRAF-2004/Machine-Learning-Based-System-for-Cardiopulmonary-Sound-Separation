# External cardiopulmonary dataset audit

Audit date: 2026-09-29. Status: **BOUNDED TIER-B QUALIFICATION COMPLETE — EXTERNAL TRANSFER PILOT REJECTED**.
Qualified does not mean clean ground truth or adopted for the final model.
See `EXTERNAL_DATA_TRAINING_EXECUTION.md`; no full external acquisition/training
followed the failed predeclared target-domain gate.

The existing 171,313-parameter T8 separator remains the fallback. This record does not change its model, checkpoint, inference, or test protocol. T9 remains sealed. No production or demographic-interface change is proposed.

## Decision at the dataset-search gate

- **Heart selected for bounded qualification:** the public CirCor DigiScope v1.0.3 release.
- **Lung selected for bounded qualification:** SPRSound, initially its BioCAS2022 training release, pinned to commit `bca1e51422a42a042441010081519610ef3845d0`.
- **Secondary candidates:** HF_Lung_V1, then KAUH diaphragm exports, subject to source-purity and grouping qualification.
- **External recordings accepted as training targets:** none on the strength of this literature/catalogue audit alone.
- **External Tier A pure separation references established:** none.

CirCor and SPRSound offer explicit participant metadata, original public distributions, reusable licences, cardiac/respiratory annotations and substantially more people than the manikin corpus. Their population/device mismatch and possible physiological cross-contamination remain material risks. Selection means **inspect**, not “clean ground truth.” A future pretraining pilot must be labelled imperfect-source pretraining and must earn adoption through held-out HLS **non-test** family transfer.

The machine-readable inventory is [external_dataset_catalog_v1.json](../research/datasets/external_dataset_catalog_v1.json). Its `record_defaults` defines every requested audit field. Each dataset shallow-merges those defaults with its overrides; an inherited `null` means **unknown/unverified**, not zero or absent. It is a dataset catalogue, not a recording-level accepted-source registry.

## Search scope and evidence rules

Original repositories, PhysioNet, Mendeley, Figshare, Zenodo and dataset papers were examined, including 2023–2026 releases. Newer does not imply independent: SPRSound task folders, HLS adaptations and aggregated auscultation corpora can repeat earlier recordings. The search prioritized paired/multisensor data before classification corpora.

Tier A means genuinely isolated sources or defensible paired separation references. Tier B is a **potential** imperfect-source pretraining pool requiring recording-level qualification. Tier C supplies domain information but is not presently defensible clean supervision. Rejected means unselected for this program, not scientifically worthless.

Classification labels certify the labelled event or diagnosis, not acoustic source purity. Neither a stethoscope filter nor a “normal” label establishes a pure heart/lung target. EIT, respiration bands, ECG and SCG are not lung waveform references. Theoretical usefulness of multimodal recordings does not establish a recoverable additive reference triple.

## Evidence matrix: populations and acquisition

Published cohort counts, public release counts, independent acquisitions, channel/filter exports and accepted recording counts are kept distinct.

| Dataset / original source | Population and recording evidence | Format / demographics / acquisition | Present role |
|---|---|---|---|
| [HLS-CMDS v3](https://data.mendeley.com/datasets/8972jxbpmp/3) | 535 published files; controlled manikin, **zero human subjects**. Existing permitted non-test source pool is 45 heart + 41 lung. | Prior verified project evidence: mono PCM16, 4 kHz, 15 s. Littmann CORE at multiple chest sites; different filter modes. | Existing target-domain supervision, not external diversity. Separate component recordings do not prove synchronized additive references. |
| [CirCor v1.0.3](https://physionet.org/content/circor-heart-sound/1.0.3/) | **942 public subject-ID rows / 3,163 WAVs**, not the full paper's 1,568-person cohort. Additional IDs can link repeat people. | Native 4 kHz. Age categories and reported sex; murmurs and outcomes; valve sites. Brazil screening campaigns. Full-paper 4.8–80.4 s range is not the measured eligible subset range. | Tier B candidate; primary heart qualification. |
| [SPRSound](https://github.com/SJTU-YONGFU-RESEARCH-GRP/SPRSound) | Original: 292 people, 2,683 recordings, about 8.2 h. Current canonical releases: 6,567 paths / 6,566 distinct Git blobs, 868 known subject-ID strings; 390 files lack IDs. | Original 8 kHz/16-bit; Yunting II, Shanghai Children's Medical Center. Original CSV: ages 0.2–16.2, 140 female/152 male. Event and record-quality labels. | Tier B candidate; primary lung qualification. Later releases are not automatically accepted. |
| [HF_Lung_V1](https://gitlab.com/techsupportHF/HF_Lung_V1) | 261 TSECC patients + 18 RCW/RCC residents; 9,765 × 15 s = **40.69 channel-hours**, not equivalent independent patient-hours. | 4 kHz/16-bit; Littmann3200 and HF-Type-1. Shifted dates/sessions; Taiwan. Demographics incomplete; small RCW/RCC component 11 male/7 female. | Tier B candidate; secondary adult/device diversity. Date grouping is not proven patient identity. |
| [ICBHI2017](https://bhichallenge.med.auth.gr/) | 126 subjects, 920 recordings, 5.5 h; 6,898 respiratory cycles. | 10–90 s; metadata includes age/sex, chest location and four devices. Portugal/Greece. Exact file-format inventory deferred. | Tier C currently; technical/rights/purity qualification deferred. |
| [CinC2016](https://physionet.org/content/challenge-2016/1.0.0/) | Official page narrative reports 3,126 A–E training records; full current archive and per-database person linkage not inventoried here. | Mono, resampled 2 kHz; 5 s to over120 s. Updated classification/quality annotations; variable recording domains. | Tier C currently; native bandwidth and contamination make CirCor the first choice. |
| [KAUH v3](https://data.mendeley.com/datasets/jwyy9np4gv/3) | **112 independent acquisitions**, each with three filter exports; 35 healthy/77 unhealthy. | 5–30 s; Littmann3200, Jordan. 43 female/69 male. Subject age/sex/site/disease metadata; original age prose conflicts with its table. | Tier B candidate; D/diaphragm exports only if qualified. Short files need exclusion, not unrelated concatenation. |
| [BRACETS v1](https://data.mendeley.com/datasets/f43c7snks5/1) | 78 adults; 1,097 respiratory + 795 EIT recordings. | Portugal/Greece; simultaneous single/multichannel respiratory audio and EIT. Full technical and demographic distributions unverified. | Tier C currently; potentially useful adult acquisition diversity, **not** pure heart/lung reference data. |
| [RespiratoryDatabase@TR v2](https://data.mendeley.com/datasets/p9z4h98s6j/2) | Public release is a COPD lung subset; exact available cohort/file totals unverified. Wider study table: 77 people; abstract says75. Do not substitute either for released inventory. | Paper describes 4 kHz, two Littmann3200 devices, 12 lung/4 heart sites and three filters. Left/right pairs synchronized, not all16 channels. | Tier C pending scope reconciliation. Breath-hold heart acquisition in the paper does not prove those files are publicly available. |
| [FOSTER](https://www.nature.com/articles/s41597-025-05694-2) | 40 healthy participants, 20 female/20 male, mean age26.93±7.09; about7 min/person. | 10 kHz/16-bit multimodal FCG/SCG/ECG/PCG/respiration; Naples. Respiration uses a **band**, not acoustic lung reference. | Tier C; no verified dataset licence and no paired lung waveform. |
| [MSCAD](https://zenodo.org/records/7857970) | 18,497 recordings/1,333 patients plus4,547/319; overlap between parts unknown. | Cardiac/pulmonary auscultation, encounters and vitals; chronic/COVID19/healthy populations. Restricted payload uninspected. | Rejected for current production-usable data path: NC-SA and restricted; no access sought. |
| [BMD-HS](https://doi.org/10.1016/j.cmpbup.2026.100237) | Paper reports864 cardiac records; actual reusable download inventory unverified. | Normal/valvular disease with echocardiographic labels; demographic/smoking metadata reported. | Unqualified: paper-linked original repository404; an NC-ND fork is not an automatically equivalent substitute. |
| [CoCross2024](https://figshare.com/articles/dataset/CoCross_Covid-19_Lung_Sounds_Database/23578719) | Public archive inventory not yet measured; do not reuse platform-wide patient totals as archive totals. | Mechanically ventilated critically ill COVID19, Thessaloniki ICU; audio plus features. | Tier C domain-only; ventilation/ICU contamination must not become “clean lung.” |

Where a table does not give duration, sample format, channel count, patient linkage, demographic coverage, annotation details or hardware, that field remains explicitly unknown in the catalogue. No missing value was inferred from a filename convention belonging to a different dataset.

## Rights, access, storage and originality

| Dataset | Verified access / rights | Size/checksum evidence | Qualification concern |
|---|---|---|---|
| CirCor | Public; **ODC-By 1.0**, not a generic CC licence. Dataset/paper/PhysioNet attribution. | Official page: 449.5 MB ZIP / 558.9 MB expanded; verify file SHA-256 during acquisition. | Known clinical noise; annotation quality does not certify source isolation. |
| SPRSound | Public original repository; **CC BY4.0**. | Canonical WAV payload1,199,006,486 bytes; Git blob identities available; independently hash downloads. | Patient reuse, task-folder duplication, missing IDs, poor-quality records. |
| HF_Lung_V1 | Public GitLab; **CC BY4.0**. | PCM-only estimate1,171,800,000 bytes; exact archive checksum unverified. | Session/date proxies, correlated channels, single-annotator labels; corrected/padded file documented. |
| ICBHI | Official “freely available for research” wording; exact production-reusable licence unresolved. | Official direct HTTPS currently fails **expired TLS certificate**; no insecure bypass. Size/checksums unverified. | Do not import third-party CC0 claims or silently use reposts. |
| CinC2016 | Public; **ODC-By1.0**. | Whole-page ZIP1011.4 MB / expanded1.1 GB; selected subset differs. | Talking, movement, breathing and intestinal contamination explicitly described. |
| KAUH | Public dataset metadata, **CC BY4.0**; article licence differs. | Archive size/checksums unverified. | B/D/E exports are correlated; some shorter than8 s; filter domain can be a shortcut. |
| BRACETS / RDTR | Identified Mendeley releases **CC BY4.0**. | Archives not inventoried; size/checksums unknown. | Full-paper scope does not establish public pure-reference scope. |
| FOSTER | Public OSF child `3u6yb`, `node_license:null`; advertised parent returned401, requests stopped. | Unknown. | Not selected; no bypass, no access request and no article-licence substitution for dataset rights. |
| MSCAD | **CC BY-NC-SA4.0**, restricted files requiring form and Zenodo approval. | Unknown; cumulative platform download-volume counter is **not** archive size. | Not selected; no authenticated access attempted. |
| BMD-HS | Original repo unavailable; original usable payload licence unresolved. | Unknown. | No substitution of differently licensed fork. |
| CoCross | Public **CC BY4.0**. |1,344,441,829-byte ZIP; official MD5 `b9db86066a3670106e1c0958258120c6`. | Not selected for pure-target pilot. |

If a selected dataset requires login or a click-through agreement, stop acquisition and use the official external-browser authentication/consent flow. Public metadata access is not permission to bypass restricted payloads. Dataset rights must remain attached to source and derived manifests; these research findings are not blanket legal clearance for every downstream use.

### Rejected false-diversity opportunities

- **HF_Lung_V1_IP/HF_Lung_V2:** the incremental package is [CC BY-NC4.0](https://gitlab.com/techsupportHF/HF_Lung_V1_IP), unlike V1. V2 also contains V1, so summing versions double-counts.
- **HLS UNIWA normalized2026 adaptation:** [official metadata](https://zenodo.org/records/20027993) identifies50 heart+50 lung derivatives from HLS. It adds no people/families and could leak sealed families through renamed audio. **Do not acquire or fingerprint its audio.**
- **BreathMY_v2 (2026):** [original repository](https://github.com/QHPC-SP-Research-Lab/BreathMY_v2/) expands150 existing recordings through time stretching, cycle replication and noise; CC BY-NC4.0. Synthetic volume is not independent diversity.
- **CaReSound/AuscultaBase/other combined corpora:** reuse of CirCor/SPRSound/ICBHI is not an additional population. Start from original sources, not duplicated compilations.
- **Zhou et al.2024 respiratory dataset:** original paper located, DOI `10.1121/10.0025851`; authoritative downloadable payload/licence not verified. Unqualified, not silently accepted from reposts.

## Exact duplication and identity findings

The SPRSound metadata inspection used only the original repository tree and patient CSV, not HLS test data. Canonical release WAV counts are 2,683 / 871 / 1,704 / 1,309 for 2022 / 2023 / 2024 / 2025. Their payloads are 470,268,708 / 164,028,852 / 342,024,672 / 222,684,254 bytes respectively. Downloading every repository WAV path would instead count 20,457 paths and 3.76 GB because task folders replicate the releases.

One canonical exact Git-blob duplicate already crosses the original challenge train/test directories:

- `BioCAS2022/test2022_wav/41279835_14.1_0_p1_2050.wav`
- `BioCAS2022/train2022_wav/41279835_14.1_0_p1_2945.wav`

This is **external** split metadata, not T9. It demonstrates why a project-specific subject-grouped registry and content deduplication are required. Original intra-patient challenge divisions cannot be adopted as independent-patient validation.

CirCor `Additional ID` links participants across campaigns. Build connected components before external train/validation assignment; balancing 942 rows as 942 independent people can be wrong. Use immutable raw checksums, canonical PCM fingerprints and lineage metadata for acquired external/non-test sources only. Do not decode T9 to check duplication: exclude known HLS-derived corpora by provenance first.

## Source-purity and recording qualification gate

The bounded acquisition protocol has preselected 40 CirCor subject IDs / 73 recording candidates and 40 SPRSound subject IDs / 77 candidates. These are **candidate counts**, not qualified targets. The recording registry and acquisition evidence—not this catalogue—must record final technical/purity acceptance.

Required checks before any pilot:

1. Preserve downloaded originals unchanged; pin URLs/versions and hash every file. Keep payloads/caches ignored and outside normal Git history.
2. Decode only external and permitted HLS non-test recordings. Verify finite samples, actual rate/bit depth/channels/duration, clipping, silence, corruption and duplicates; every exclusion needs a reason.
3. Use a deterministic anti-aliased 4 kHz mono float32 derivation with resampler settings and both hashes. Do not reconstruct lost bandwidth by claiming that upsampling adds information.
4. Select only valid eight-second contiguous crops. Do not concatenate unrelated records/people. Physiological and artifact review must cover the proposed crop, not just its file label.
5. Review a predeclared cross-subject/pathology/age/site sample, including imperfect cases. Check heart leakage in lung candidates and breathing/handling/speech in cardiac candidates. Statistics and event annotations alone cannot prove purity.
6. Keep subject groups, duplicate clusters and dependent filtered/channel versions together. Missing identity stays unknown; no convenient substitute “patient ID” is invented.
7. Freeze an accepted recording/crop manifest only after qualification. If acceptable imperfect-source targets cannot be established, do not run fake-clean supervised pretraining; use the paused HLS-only fallback.

Any eventual synthetic target must be described honestly as a **qualified heart-dominated or lung-dominated recording**, with residual contamination assumptions and confidence. Adding two contaminated recordings yields exact synthetic additivity but does **not** validate physiological heart/lung purity.

## Diversity and demographic/product recommendation

**UX DECISION A: NO DEMOGRAPHIC INPUT REQUIRED.** No frontend work, automatic age/sex classifier, or demographic routing is justified by this audit.

Age is relevant to external training population coverage: the first feasible heart/lung candidates are pediatric-heavy. This is a limitation, not proof that a universal separator needs an age input. Use actual dataset age categories/ranges; retain unknown values, and avoid inventing precise age from a broad CirCor category. Sex may support descriptive stratification, not presumed conditioning. Device, chest site and pathology may confound apparent demographic differences.

For a future qualified pool, subject/dataset balancing and physiologically compatible age-domain pairing are preferable to uniform file sampling. These are protocol decisions to freeze before treatment results, not permission to add demographic UI. Device diversity is important because a heart-only device and lung-only device can create a dataset-identity shortcut. HLS held-out-family transfer remains the target-domain adoption criterion, not external-domain classification accuracy.

No claim of clinical effectiveness, patient-level generalization or universal pediatric/adult robustness follows from this catalogue.

## References (APA7; original publications/data)

Ali, S. N., Zahin, A., Shuvo, S. B., Nizam, N. B., Nuhash, S. I. S. K., Razin, S. S., Sani, S. M. S., Rahman, F., Nizam, N. B., Azam, F. B., Hossen, R., Ohab, S., Noor, N., & Hasan, T. (2026). BUET multi-disease heart sound dataset: A comprehensive auscultation dataset for developing computer-aided diagnostic systems. *Computer Methods and Programs in Biomedicine Update, 9*,100237. https://doi.org/10.1016/j.cmpbup.2026.100237

Altan, G., & Kutlu, Y. (2020). *RespiratoryDatabase@TR (COPD severity analysis)* (Version2) [Data set]. Mendeley Data. https://doi.org/10.17632/p9z4h98s6j.2

Altan, G., Kutlu, Y., Garbi, Y., Pekmezci, A. O., & Nural, S. (2021). *Multimedia respiratory database (RespiratoryDatabase@TR): Auscultation sounds and chest X-rays* [Preprint; repository version of earlier study]. arXiv. https://doi.org/10.48550/arXiv.2101.10946

Fraiwan, M., Fraiwan, L., Khassawneh, B., & Ibnian, A. (2021). A dataset of lung sounds recorded from the chest wall using an electronic stethoscope. *Data in Brief, 35*,106913. https://doi.org/10.1016/j.dib.2021.106913

Hsu, F.-S., Huang, S.-R., Huang, C.-W., Huang, C.-J., Cheng, Y.-R., Chen, C.-C., Hsiao, J., Chen, C.-W., Chen, L.-C., Lai, Y.-C., Hsu, B.-F., Lin, N.-J., Tsai, W.-L., Wu, Y.-L., Tseng, T.-L., Tseng, C.-T., Chen, Y.-T., & Lai, F. (2021). Benchmarking of eight recurrent neural network variants for breath phase and adventitious sound detection on a self-developed open-access lung sound database—HF_Lung_V1. *PLOS ONE,16*(7),e0254134. https://doi.org/10.1371/journal.pone.0254134

Liu, C., Springer, D., Li, Q., Moody, B., Juan, R. A., Chorro, F. J., Castells, F., Roig, J. M., Silva, I., Johnson, A. E. W., Syed, Z., Schmidt, S. E., Papadaniil, C. D., Hadjileontiadis, L., Naseri, H., Moukadem, A., Dieterlen, A., Brandt, C., Tang, H., … Clifford, G. D. (2016). An open access database for the evaluation of heart sound algorithms. *Physiological Measurement,37*(12),2181–2213. https://doi.org/10.1088/0967-3334/37/12/2181

Kaimakamis, E., Kotoulas, S., Tzimou, M., Karachristos, C., Giannaki, C., Kilintzis, V., Stefanopoulos, L., Chatzis, E., Beredimas, N., Rocha, B., Pessoa, D., Paiva, R. P., Maglaveras, N., Bitzani, M., & Lavrentieva, A. (2024). *CoCross Covid-19 lung sounds database* (Version 1) [Data set]. Figshare. https://doi.org/10.6084/m9.figshare.23578719.v1

Oliveira, J., Renna, F., Costa, P. D., Nogueira, M., Oliveira, C., Ferreira, C., Jorge, A., Mattos, S., Hatem, T., Tavares, T., Elola, A., Rad, A. B., Sameni, R., Clifford, G. D., & Coimbra, M. T. (2022). The CirCor DigiScope dataset: From murmur detection to murmur classification. *IEEE Journal of Biomedical and Health Informatics,26*(6),2524–2535. https://doi.org/10.1109/JBHI.2021.3137048

Oliveira, J., Renna, F., Costa, P., Nogueira, M., Oliveira, A. C., Elola, A., Ferreira, C., Jorge, A., Bahrami Rad, A., Reyna, M., Sameni, R., Clifford, G., & Coimbra, M. (2022). *The CirCor DigiScope phonocardiogram dataset* (Version1.0.3) [Data set]. PhysioNet. https://doi.org/10.13026/tshs-mw03

Pabiszczak, M., Ravn, J., Adler, D., & Avraham, L. (2023). *Medsensio-Sanolla cardiopulmonary auscultation dataset [MSCAD]—A dataset of lung & heart auscultation recordings as well as vitals data for COVID and chronic patients* (Version1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.7857970

Parlato, S., Centracchio, J., Cinotti, E., Manzi, M. V., Canciello, G., Prastaro, M., Lembo, M., Brandwood, B. M., Gargiulo, G. D., Bifulco, P., Esposito, G., Izzo, R., & Andreozzi, E. (2025). A forcecardiography dataset with simultaneous SCG, heart sounds, ECG, and respiratory signals. *Scientific Data,12*,1370. https://doi.org/10.1038/s41597-025-05694-2

Pessoa, D., Rocha, B. M., Strodthoff, C., Gomes, M., Rodrigues, G., Petmezas, G., Cheimariotis, G.-A., Kilintzis, V., Kaimakamis, E., Maglaveras, N., Marques, A., Frerichs, I., de Carvalho, P., & Paiva, R. P. (2023). BRACETS: Bimodal repository of auscultation coupled with electrical impedance thoracic signals. *Computer Methods and Programs in Biomedicine,240*,107720. https://doi.org/10.1016/j.cmpb.2023.107720

Rocha, B. M., Filos, D., Mendes, L., Serbes, G., Ulukaya, S., Kahya, Y. P., Jakovljevic, N., Turukalo, T. L., Vogiatzis, I. M., Perantoni, E., Kaimakamis, E., Natsiavas, P., Oliveira, A., Jácome, C., Marques, A., Maglaveras, N., Paiva, R. P., Chouvarda, I., & de Carvalho, P. (2019). An open access database for the evaluation of respiratory sound classification algorithms. *Physiological Measurement,40*(3),035001. https://doi.org/10.1088/1361-6579/ab03ea

Salvador-Navarro, A., De La Torre-Cruz, J., Muñoz-Montoro, A. J., Ranilla-Cortina, S., Carabias-Orti, J. J., Cruz-Molina, J. M., & Cañadas-Quesada, F. J. (2026). Respiratory rate estimation from breath sounds based on deep learning. *Biomedical Signal Processing and Control,119*,109905. https://doi.org/10.1016/j.bspc.2026.109905

Torabi, Y., Shirani, S., & Reilly, J. P. (2025). Descriptor: Heart and lung sounds dataset recorded from a clinical manikin using digital stethoscope (HLS-CMDS). *IEEE Data Descriptions,2*,133–140. https://doi.org/10.1109/IEEEDATA.2025.3566012

Zhang, Q., Zhang, J., Yuan, J., Huang, H., Zhang, Y., Zhang, B., Lv, G., Lin, S., Wang, N., Liu, X., Tang, M., Wang, Y., Ma, H., Liu, L., Yuan, S., Zhou, H., Zhao, J., Li, Y., Yin, Y., … Lian, Y. (2022). SPRSound: Open-source SJTU paediatric respiratory sound database. *IEEE Transactions on Biomedical Circuits and Systems,16*(5),867–881. https://doi.org/10.1109/TBCAS.2022.3204910

Zhou, G., Liu, C., Li, X., Liang, S., Wang, R., & Huang, X. (2024). An open auscultation dataset for machine learning-based respiratory diagnosis studies. *JASA Express Letters,4*(5),052001. https://doi.org/10.1121/10.0025851

Dataset-specific original URLs in the tables/catalogue additionally identify the exact distribution and its rights. Article metadata were checked against original publisher/DOI records; article copyright must not be silently substituted for a dataset licence.
