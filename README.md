# TUGMA

> Tutor-student Unified Graph-based Matching Approach

## Overview

## Problem

## Objectives

## Discrete Structures Concepts

### Set Theory
### Predicate Logic
### Relations
### Graph Theory
### Algorithms

## System Architecture
```
tugma/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── assets/
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/
│    ├── mathematical_model.md
│    ├── database_schema.md
│    └── architecture.md
│
├── src/
│   ├── database.py
│   ├── sets.py
│   ├── logic.py
│   ├── relations.py
│   ├── graph.py
│   ├── matching.py
│   ├── scheduling.py
│   └── visualization.py
│
└── tests/
    ├── test_logic.py
    ├── test_matching.py
    └── test_scheduling.py
```

## Features

## Technology Stack

## Installation

## Running the Application

## Database

### Entity Relationship Diagram
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ffffff'}}}%%
erDiagram
    %% Core Parent Entities
    STUDENTS {
        INTEGER student_id PK
        TEXT name
        INTEGER grade_level
        TEXT course
    }

    SUBJECTS {
        INTEGER subject_id PK
        TEXT subject_code UK
        TEXT subject_name
    }

    TUTORS {
        INTEGER tutor_id PK
        TEXT name
        INTEGER grade_level
        TEXT course
        INTEGER verified
    }

    %% Student-Side Tables
    STUDENT_LANGUAGES {
        INTEGER student_id PK, FK
        TEXT language PK
    }

    STUDENT_SUBJECTS {
        INTEGER student_id PK, FK
        INTEGER subject_id PK, FK
    }

    STUDENT_SCHEDULE {
        INTEGER schedule_id PK
        INTEGER student_id FK
        INTEGER subject_id FK
        TEXT day
        TEXT start_time
        TEXT end_time
    }

    %% Tutor-Side Tables
    TUTOR_LANGUAGES {
        INTEGER tutor_id PK, FK
        TEXT language PK
    }

    TUTOR_SUBJECTS {
        INTEGER tutor_id PK, FK
        INTEGER subject_id PK, FK
    }

    TUTOR_AVAILABILITY {
        INTEGER availability_id PK
        INTEGER tutor_id FK
        TEXT day
        TEXT start_time
        TEXT end_time
    }

    %% --- RELATIONSHIPS ---

    %% 1. Pure Student Outer Node
    STUDENTS ||--o{ STUDENT_LANGUAGES : "speaks"

    %% 2. Student-Subject Junctions (Vertical Flow)
    STUDENTS ||--o{ STUDENT_SUBJECTS : "requests"
    STUDENT_SUBJECTS }o--|| SUBJECTS : "needed by"

    %% 3. Student Schedule Mapping (Rerouted through Schedule)
    STUDENTS ||--o{ STUDENT_SCHEDULE : "has class"
    STUDENT_SCHEDULE }o--|| SUBJECTS : "scheduled for"

    %% 4. Tutor-Subject Junctions
    TUTORS ||--o{ TUTOR_SUBJECTS : "teaches"
    TUTOR_SUBJECTS }o--|| SUBJECTS : "taught by"

    %% 5. Pure Tutor Outer Node
    TUTORS ||--o{ TUTOR_LANGUAGES : "speaks"
    TUTORS ||--o{ TUTOR_AVAILABILITY : "available at"
```

## Testing

## Project Structure

## Limitations

## Future Improvements

## License
## Tutor profile, teaching ratings, and certificates

The signed-in member can open **Profile** from the top-right control. Tutor profiles
show academic information, tutoring subjects and availability, criterion-level
teaching ratings, and earned or in-progress certificates. Rating aggregates and
certificate progress are read by `services/profile_service.py`; SQLite access is
provided by `src/database.py`.

The profile schema is included in `database/schema.sql` and its demonstration
records are included in `database/seed.sql`. Existing databases receive the same
additive changes through migration version 4. The seeded tutor reviews are clearly
identified as demonstration data (`is_demo = 1`) and are not genuine student
feedback. Teaching ratings and certificates are display-only and do not affect
the compatibility relation, graph, tutor capacity, or matching algorithm.
