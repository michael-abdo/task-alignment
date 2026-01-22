# Conversation Analysis Architecture Diagrams - Organized

## CHUNK 1: CURRENT ARCHITECTURE
*What exists today and current limitations*

1. **chunk1_01_current_implementation** - The actual deployed system (6 services completed: Talk Time, Interruption, Dominance, Tone Shift, Safety Score, Fatigue)
2. **chunk1_02_interruption_detection** - Interruption detection design (transcript-based, 400ms overlap)
3. **chunk1_03_data_pipeline** - How data currently flows through the system (sequential processing)
4. **chunk1_04_old_modality_focused** - Current modality-focused architecture pattern

## CHUNK 2: TRANSITION ARCHITECTURE
*Multi-modal enhancement concepts, Hume AI integration, and validation techniques*

1. **chunk2_01_multimodal_architecture** - Original multi-modal processing vision
2. **chunk2_02_interruption_validation** - Multi-modal interruption validation workflow
3. **chunk2_03_tone_shift_detection** - Multi-modal tone analysis process
4. **chunk2_04_implementation_gantt** - Implementation timeline (needs updating)
5. **chunk2_05_false_positive_filters** - Techniques for reducing false positives
6. **chunk2_06_tone_validation_matrix** - Cross-modal validation matrix
7. **chunk2_07_flashpoint_fusion_v1** - **Flashpoint Detector: First Fusion Layer implementation (PRs 55/56)**
8. **chunk2_08_fusion_layer_evolution** - **Evolution path from Flashpoint v0.1 to full Fusion Layer**

## CHUNK 3: END STATE ARCHITECTURE
*Target feature-focused, infinitely scalable architecture*

1. **chunk3_01_unified_event_architecture** - Unified event bus core architecture
2. **chunk3_02_feature_plugin_detail** - How feature plugins work in detail
3. **chunk3_03_infinite_scalability** - Demonstration of unlimited feature scaling
4. **chunk3_04_new_feature_focused** - Clean feature-focused architecture pattern

## CHUNK 4: PSYCHOMETRIC PROFILE INTEGRATION
*User context layer that enriches detection outputs with dispositional baselines (Future)*

1. **chunk4_01_psychometric_profile_overlay** - How profile data enriches detection outputs

---

## Hume AI Integration (PRs 55/56)

### What Hume Provides

| Service | Signals | Source |
|---------|---------|--------|
| **HumeAudioService** | valence, arousal, tension_index, drift, volatility, band | Hume Prosody API |
| **HumeFaceService** | positive_engagement, distress_concern | Hume Expression API |

### Flashpoint Detector (First Fusion Layer)

The **Flashpoint Detector** is the initial implementation of the Fusion Layer concept from chunk2_01.

**What it does:**
- Monitors `hume_audio_tension_index` and `hume_face_distress_concern`
- When BOTH exceed 0.35 threshold within 7 seconds
- Emits a `timeline_event` of kind `flashpoint`
- 20-second cooldown between events

**Why it matters:**
- Single-signal detection is noisy (voice tension could be excitement, facial distress could be concentration)
- Multi-signal agreement = high confidence something significant is happening

**Evolution path:**
```
v0.1 (Current)     →  v0.2 (Enhanced)      →  v1.0 (Full Fusion)
─────────────────     ─────────────────       ─────────────────
2 Hume signals        All Hume signals        All detectors
Simple AND logic      Weighted scoring        + existing detectors
No confidence         Confidence 0-1          + validation layer
```

---

## Architecture Evolution Summary

**CHUNK 1** → **CHUNK 2** → **CHUNK 3** → **CHUNK 4**

From service-oriented, limited multi-modal capability → Hume AI + Flashpoint Fusion → Feature-focused, multi-modal-first architecture → User context enrichment via psychometric profiles

## Key Principles by Chunk

### Chunk 1 (Current - Text-Based)
- Service-oriented architecture
- **Text/Transcript-based detectors:**
  - talk_time_analytics (Gini coefficient, words spoken)
  - interruption_detector (400ms overlap threshold on transcript timing)
  - dominance_analyzer (50% speaking time threshold)
  - tone_shift_detector (Claude API on transcript text)
  - safety_score (composite 0-100 metric)
  - fatigue_detector (PERCLOS, blink rate, microsleep)
- Sequential processing model

### Chunk 2 (Transition - Hume Integration)
- **NEW: Hume AI signal extraction** (PRs 55/56)
  - HumeAudioService: prosody analysis (tension, arousal, valence)
  - HumeFaceService: facial expression analysis (engagement, distress)
- **NEW: Flashpoint Detector** - first Fusion Layer implementation
- Multi-modal validation techniques
- False positive reduction strategies
- Cross-modal correlation methods

### Chunk 3 (End State)
- Feature-focused design
- Multi-modal processing is core foundation
- Infinite scalability through plugin architecture
- Unified event stream for all features
- Independent feature scaling

---

## Diagram vs Implementation Status

### Current State (After PRs 55/56)

| Component | Status | Input Type |
|-----------|--------|------------|
| interruption_detector | Completed | Transcript timing |
| tone_shift_detector | Completed | Transcript text + Claude API |
| dominance_analyzer | Completed | Transcript speaking stats |
| HumeAudioService | NEW (PR 55) | Audio stream via Hume API |
| HumeFaceService | NEW (PR 56) | Video frames via Hume API |
| Flashpoint Detector | NEW (PR 56) | Hume audio + face signals |
| Full Fusion Layer | Future | All signals combined |

### What PRs 55/56 ADD (not replace)

```
BEFORE:                          AFTER:
────────                         ──────
Transcript ──→ Detectors         Transcript ──→ Detectors (unchanged)
                                      +
                                 Audio ──→ HumeAudio ──┐
                                                       ├──→ Flashpoint
                                 Video ──→ HumeFace ───┘
```

The existing text-based detectors continue to work. Hume services and Flashpoint Detector are a PARALLEL track that adds new multimodal capabilities.

---

## API Endpoints

### Existing
- `GET /api/analytics/...` - Existing analytics endpoints

### New (PRs 55/56)
- `GET /api/analytics/sessions/<id>/hume-audio` - Hume audio metrics
- `GET /api/analytics/sessions/<id>/hume-face` - Hume face metrics
- `GET /api/analytics/deal-review/<uuid>/view-model?include_realtime=1` - Combined view model
