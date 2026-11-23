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
        TEXT bio
        TEXT study_notes
        TEXT interests
        TEXT learning_style
        TEXT preferred_setup
        TEXT free_time
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
        INTEGER capacity
    }

    CERTIFICATES {
        INTEGER certificate_id PK
        TEXT certificate_code UK
        TEXT title
        TEXT category
        TEXT tier
        TEXT description
        TEXT requirement_label
        INTEGER target_value
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
        TEXT day
        TEXT start_time
        TEXT end_time
        INTEGER subject_id FK
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

    TUTOR_REVIEWS {
        INTEGER review_id PK
        INTEGER tutor_id FK
        INTEGER student_id FK
        TEXT session_reference
        TEXT review_date
        INTEGER is_demo
    }

    TUTOR_REVIEW_SCORES {
        INTEGER review_id PK, FK
        TEXT criterion PK
        INTEGER score
    }

    TUTOR_CERTIFICATES {
        INTEGER tutor_id PK, FK
        INTEGER certificate_id PK, FK
        TEXT status
        INTEGER progress_value
        TEXT earned_date
    }

    %% --- RELATIONSHIPS ---

    %% 1. Student Tables
    STUDENTS ||--o{ STUDENT_LANGUAGES : "speaks"
    STUDENTS ||--o{ STUDENT_SUBJECTS : "requests"
    STUDENT_SUBJECTS }o--|| SUBJECTS : "needed by"
    STUDENTS ||--o{ STUDENT_SCHEDULE : "has class"
    STUDENT_SCHEDULE }o--|| SUBJECTS : "scheduled for"
    STUDENTS ||--o{ TUTOR_REVIEWS : "submits"

    %% 2. Tutor Tables
    TUTORS ||--o{ TUTOR_LANGUAGES : "speaks"
    TUTORS ||--o{ TUTOR_SUBJECTS : "teaches"
    TUTOR_SUBJECTS }o--|| SUBJECTS : "taught by"
    TUTORS ||--o{ TUTOR_AVAILABILITY : "available at"
    TUTORS ||--o{ TUTOR_REVIEWS : "receives"
    TUTORS ||--o{ TUTOR_CERTIFICATES : "tracks"

    %% 3. Review Scores and Certificates
    TUTOR_REVIEWS ||--o{ TUTOR_REVIEW_SCORES : "graded by"
    CERTIFICATES ||--o{ TUTOR_CERTIFICATES : "defines"
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
