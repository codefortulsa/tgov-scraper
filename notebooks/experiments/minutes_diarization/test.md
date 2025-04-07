# Experiment Results

## With full diarization and minutes

### Chunked (3) 4o-mini with full diarization and minutes

Repetition and overlap with "unknown" has been deleted.  Model confuses Lakin, Wright, and Huffines during procssing of the 3 chunks.

    {
        "SPEAKER_00": "Councilor Decter Wright",
        "SPEAKER_01": "Daniel Regan with the Tulsa Airports Improvement Trust",
        "SPEAKER_02": "Councilor Bush",
        "SPEAKER_03": "Councilor Bellis",
        "SPEAKER_04": "Unknown",
        "SPEAKER_05": "Unknown",
        "SPEAKER_06": "Archie",
        "SPEAKER_07": "Bush",
        "SPEAKER_08": "Bellis",
        "SPEAKER_08": "Councilors (Hall-Harper, Archie, Decter Wright, Dutton, Lakin, Bellis, Bush, Gilbert, Bengel)",
        "SPEAKER_09": "Unknown",
        "SPEAKER_10": "Lakin",
        "SPEAKER_10": "Councilor Decter Wright",
        "SPEAKER_11": "John Huffines",
        "SPEAKER_11": "Lori Doring",
        "SPEAKER_13": "Mr. Evan Taylor",
        "SPEAKER_13": "John Huffines",
        "SPEAKER_14": "Mr. Stuart McDaniel",
        "SPEAKER_15": "Erran Persley, City of Tulsa Economic Development Director",
        "SPEAKER_16": "Jeff Sabin, Development Counsel with the Center for Economic Development Law",
        "SPEAKER_17": "Jack Blair, City Attorney",
        "SPEAKER_18": "Classify as speaker addressing the council or a public comment, but without a specific name",
        "SPEAKER_19": "Chair Lakin",
        "SPEAKER_19": "Decter Wright"
        "SPEAKER_19": "Phil Lakin, Chair of the Council",
    }

## With simplified diarization and minutes

### 4o-mini

    { // 4o mini with no minutes
        "SPEAKER_00": "James Alexander, Jr.",
        "SPEAKER_01": "Daniel Regan",
        "SPEAKER_02": "Bernice Alexander",
        "SPEAKER_03": "Unknown",
        "SPEAKER_04": "Unknown",
        "SPEAKER_05": "Unknown",
        "SPEAKER_06": "Decter Wright",
        "SPEAKER_07": "Councilor Bush",
        "SPEAKER_08": "Councilor Bengel",
        "SPEAKER_09": "Unknown",
        "SPEAKER_10": "Councilor Dutton",
        "SPEAKER_11": "Unknown",
        "SPEAKER_12": "Unknown",
        "SPEAKER_13": "Evan Taylor",
        "SPEAKER_14": "Stuart McDaniel",
        "SPEAKER_15": "Unknown",
        "SPEAKER_16": "Jeff Sabin",
        "SPEAKER_17": "Unknown",
        "SPEAKER_18": "John Huffines",
        "SPEAKER_19": "Phil Lakin, Jr."
    }

### 4o

Looks slightly better than 4o-mini.

    {
        SPEAKER_00: "James Alexander Jr.",
        SPEAKER_01: "Daniel Regan",
        SPEAKER_02: "Bernice Alexander",
        SPEAKER_03: "Unknown",
        SPEAKER_04: "Erran Persley",
        SPEAKER_05: "Councilor Archie",
        SPEAKER_06: "Unknown",
        SPEAKER_07: "Councilor Bush",
        SPEAKER_08: "Unknown",
        SPEAKER_09: "Councilor Hall-Harper",
        SPEAKER_10: "Councilor Decter Wright",
        SPEAKER_11: "Unknown",
        SPEAKER_13: "Evan Taylor",
        SPEAKER_14: "Stuart McDaniel",
        SPEAKER_15: "Unknown",
        SPEAKER_16: "Jeff Sabin",
        SPEAKER_17: "Jack Blair",
        SPEAKER_18: "John Huffines",
        SPEAKER_19: "Phil Lakin Jr.",
    }

### Gemini

    {
        "UNKNOWN": "Unknown",
        "SPEAKER_00": "James Alexander, Jr.",
        "SPEAKER_01": "Daniel Regan with the Tulsa Airports Improvement Trust",
        "SPEAKER_02": "Bernice Alexander",
        "SPEAKER_03": "Unknown",
        "SPEAKER_04": "Erran Persley, City of Tulsa Economic Development Director",
        "SPEAKER_05": "Councilor Archie",
        "SPEAKER_06": "Councilor Gilbert"
        "SPEAKER_07": "Councilor Bush",
        "SPEAKER_08": "Lori Doring, Secretary to the Council",
        "SPEAKER_09": "Unknown",
        "SPEAKER_10": "Councilor Bellis",
        "SPEAKER_11": "Kathryn Aung, Council Staff",
        "SPEAKER_13": "Evan Taylor",
        "SPEAKER_14": "Stuart McDaniel",
        "SPEAKER_15": "Unknown",
        "SPEAKER_16": "Jeff Sabin, Development Counsel with the Center for Economic Development Law",
        "SPEAKER_17": "Jack Blair, City Attorney",
        "SPEAKER_18": "John Huffines",
        "SPEAKER_19": "Chair Lakin",
    }

## With simplified diarization and no minutes

### 4o mini

    {
        SPEAKER_00: "James Alexander Jr.",
        SPEAKER_01: "Daniel",
        SPEAKER_02: "Mrs. Alexander",
        SPEAKER_03: "Unknown",
        SPEAKER_04: "Aaron",
        SPEAKER_05: "Unknown",
        SPEAKER_06: "Unknown",
        SPEAKER_07: "Unknown",
        SPEAKER_08: "Catherine Ong",
        SPEAKER_09: "Unknown",
        SPEAKER_10: "Unknown",
        SPEAKER_11: "Catherine Ong",
        SPEAKER_12: "Unknown",
        SPEAKER_13: "Evan Taylor",
        SPEAKER_14: "Stuart McDaniel",
        SPEAKER_15: "Unknown",
        SPEAKER_16: "Jeff Saban",
        SPEAKER_17: "Unknown",
        SPEAKER_18: "John Huffins",
        SPEAKER_19: "Phil Lakin",
    }

### 4o

    {
        SPEAKER_00: "James Alexander Jr.",
        SPEAKER_01: "Daniel (representative from airport project)",
        SPEAKER_02: "Bernice Alexander",
        SPEAKER_03: "Councilor Belis",
        SPEAKER_04: "Aaron (city staff helping with Crutchfield TIF)",
        SPEAKER_05:
        "Councilor (likely from the same district as the town hall meeting mentioned, possibly Councilor Dr. Wright)",
        SPEAKER_06: "Unknown",
        SPEAKER_07: "Unknown (likely a councilor)",
        SPEAKER_08: "Catherine Ong, Council Staff (acting as roll call announcer)",
        SPEAKER_09: "Unknown (referencing Councilor Dr. Wright)",
        SPEAKER_10:
        "Councilor making motions (uncertain, but often a councilor such as Dr. Wright or Lakin, based on meetings)",
        SPEAKER_11: "Catherine Ong, Council Staff",
        SPEAKER_13: "Evan Taylor",
        SPEAKER_14: "Stuart McDaniel",
        SPEAKER_15: "Unknown (likely another councilor or questioning party)",
        SPEAKER_16: "Jeff Saban, Development Counselor for the Airport",
        SPEAKER_17: "Unknown (likely a city attorney or advisor)",
        SPEAKER_18: "John Huffins",
        SPEAKER_19: "Council Chairman Phil Lakin",
    }
