# XcellerateEQ Product Summary

## What We're Building

**XcellerateEQ** is a real-time meeting analytics platform that detects cognitive biases and behavioral patterns during video meetings, providing instant feedback to improve decision-making quality and meeting dynamics.

---

## Core Value Proposition

Meetings are where critical business decisions happen, yet they're often derailed by invisible cognitive biases like groupthink, anchoring, and authority deference. XcellerateEQ makes these patterns visible in real-time, empowering facilitators and participants to course-correct before bad decisions get made.

---

## Key Features

### 1. Real-Time Signal Detection

The platform detects five core behavioral signals during live meetings:

| Signal | What It Detects | Business Impact |
|--------|-----------------|-----------------|
| **Interruption** | When speakers are cut off mid-sentence | Indicates power dynamics and potential idea suppression |
| **Dominance** | Disproportionate talk time by individuals | Flags meetings dominated by few voices |
| **Tone Shift** | Changes in vocal emotion/sentiment | Detects tension, agreement shifts, or discomfort |
| **Anchoring** | First suggestions unduly influencing outcomes | Prevents premature consensus on initial ideas |
| **Groupthink** | Rapid, uncritical agreement patterns | Alerts when dissent may be suppressed |

### 2. Psychometric Integration

- **Core Baseline Assessment**: 4-6 minute tests establishing individual cognitive profiles
- **Meeting Pulse Instruments**: Quick pre/post meeting surveys
- **CAI (Cognitive Alignment Index)**: Anchor metric showing team cognitive alignment

### 3. Live Dashboard

A 3-column layout providing:
- **Settings Panel**: Configuration and participant controls
- **Your Activity**: Individual metrics, talk time, and engagement scores
- **Live Bias Alerts**: Real-time signal notifications with color-coded thresholds

### 4. Zoom Integration

- Connects to live Zoom meetings via RTMS (Real-Time Media Service)
- Captures audio, video, and transcript streams
- Speaker diarization for participant attribution
- Native recording consent integration

---

## Technical Architecture

### Data Flow
```
Zoom Meeting → RTMS WebSocket → Audio/Video/Transcript Streams
                    ↓
              AWS Processing (S3 + Lambda)
                    ↓
              Hume AI (Face/Voice Analysis)
                    ↓
              Signal Detection Algorithms
                    ↓
              WebSocket → Live Dashboard
```

### Processing Pipeline

**Audio Analysis**:
- Real-time transcription via Zoom RTMS
- Sentiment analysis via Hume AI
- Talk time and interruption metrics

**Video Analysis**:
- Facial expression analysis via Hume API
- Engagement and attention detection
- Emotion tracking with confidence scores

**Transcript Processing**:
- Speaker attribution from Zoom metadata
- Keyword and phrase extraction
- Anchoring/groupthink pattern detection

---

## Signal Detection Logic

### Interruption Detection
- Monitors when a speaker's audio is cut off mid-sentence
- Tracks frequency per participant
- Distinguishes between collaborative overlap and disruptive interruption

### Dominance Detection
- Calculates talk time distribution across all participants
- Flags when any individual exceeds threshold (e.g., >50% of meeting time)
- Updates in real-time as meeting progresses

### Tone Shift Detection
- Analyzes vocal prosody via Hume AI
- Detects emotional changes: confidence → hesitation, calm → tension
- Correlates with meeting events (topics, speakers)

### Anchoring Detection
- Identifies first substantive proposals in discussion
- Tracks how subsequent discussion references or defers to initial ideas
- Alerts when alternatives aren't being explored

### Groupthink Detection
- Monitors agreement velocity (how quickly consensus forms)
- Flags lack of dissenting opinions or devil's advocate positions
- Detects "pile-on" agreement patterns

---

## User Experience

### Meeting Flow
1. User opens meeting link with session ID
2. Joins Zoom meeting with analytics overlay enabled
3. Real-time metrics display as meeting progresses
4. Bias alerts appear when thresholds are crossed
5. Post-meeting summary available after session ends

### Dashboard Sections
- **Meeting Video**: Live participant video feeds
- **Live Bias Panel**: Real-time signal alerts with severity indicators
- **Group Dynamics**: Talk time distribution, participation balance
- **Your Activity**: Personal metrics and engagement scores

---

## Key Technical Decisions

| Decision | Approach | Rationale |
|----------|----------|-----------|
| **Meeting Platform** | Zoom (via RTMS) | Native speaker diarization, enterprise adoption |
| **Video Analysis** | Hume AI | Pre-built face/voice emotion models |
| **Real-time Transport** | WebSockets | Low-latency updates to dashboard |
| **Storage** | AWS S3 | Scalable media chunk storage |
| **Frontend** | React/Next.js | Component-based, real-time capable |

---

## Success Criteria

- Meeting starts within 30 seconds of link click
- Transcription appears with <3 second delay from speech
- Analytics update in real-time without page refresh
- System handles 10+ concurrent participants per meeting
- Signal detection with acceptable false-positive rates

---

*Generated: January 22, 2026*
