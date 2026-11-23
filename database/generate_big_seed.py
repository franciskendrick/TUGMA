# Generates database/big_seed.sql (70 students + 30 tutors = 100 profiles).
# Deterministic: the same output every run.   python generate_big_seed.py > big_seed.sql
import random
from collections import Counter, defaultdict

R = random.Random(2026)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_W = [1, 1, 1, 1, 1, 0.3]

SUBJECTS = [
    (1, 'S-ITCS111', 'INTRODUCTION TO COMPUTING'), (2, 'S-ITCS112', 'FUNDAMENTALS OF PROGRAMMING'),
    (3, 'S-ITCS123', 'INTERMEDIATE PROGRAMMING'), (4, 'S-ITCS214', 'DATA STRUCTURES AND ALGORITHMS'),
    (5, 'S-ITCS215', 'HUMAN COMPUTER INTERACTION'), (6, 'S-ITCS226', 'INFORMATION MANAGEMENT'),
    (7, 'S-ITCS227', 'APPLICATION DEVELOPMENT AND EMERGING TECHNOLOGIES'),
    (8, 'S-ITCS318', 'INFORMATION ASSURANCE AND SECURITY 1'),
    (9, 'S-ITCS329', 'SOCIAL ISSUES AND PROFESSIONAL PRACTICE'),
    (10, 'S-CSPC121', 'OBJECT-ORIENTED PROGRAMMING'), (11, 'S-CSPC212', 'DISCRETE STRUCTURES 1'),
    (12, 'S-CSPC223', 'PROGRAMMING LANGUAGES'), (13, 'S-CSPC224', 'DISCRETE STRUCTURES 2'),
    (14, 'S-CSPC315', 'ALGORITHMS AND COMPLEXITY'), (15, 'S-CSPC316', 'ARCHITECTURE AND ORGANIZATION'),
    (16, 'S-CSPC327', 'AUTOMATA THEORY AND FORMAL LANGUAGES'), (17, 'S-CSPC428', 'NETWORKS AND COMMUNICATIONS'),
    (18, 'S-CSPC429', 'OPERATING SYSTEMS'),
    (19, 'D-REED003', 'CHRISTIAN COMMITMENT'), (20, 'G-HUMA003', 'ART APPRECIATION'),
    (21, 'S-MATH200', 'NUMBER THEORY'),
]
CODE = {i: c for i, c, _ in SUBJECTS}
SUBJECT_YEAR = {1: 1, 2: 1, 3: 1, 10: 1, 11: 2, 4: 2, 5: 2, 6: 2, 7: 3, 12: 2, 13: 2, 21: 2,
                8: 3, 9: 3, 14: 3, 15: 3, 16: 3, 17: 4, 18: 4}
# Lecture + laboratory subjects meet twice a week (2 h lecture, 3 h lab);
# every other subject meets once a week for 3 h.
LEC_LAB = {1, 2, 3, 10, 4, 5, 6, 7, 12, 8, 15, 17, 18}
LOAD = {1: [1, 2, 3, 10, 19, 20], 2: [11, 4, 5, 21, 12, 6, 20],
        3: [8, 9, 14, 15, 16, 7], 4: [17, 18, 9, 16]}
YEAR_COUNT = {1: 20, 2: 24, 3: 20, 4: 6}
SECTIONS = {1: 4, 2: 4, 3: 4, 4: 2}

FIRST_F = ["Maria Angelica", "Angelica", "Bianca", "Camille", "Danica", "Erika", "Francesca", "Giselle",
           "Hannah", "Isabelle", "Jasmine", "Kristine", "Lorraine", "Mariel", "Nicole", "Patricia", "Rhea",
           "Shaira", "Trisha", "Yvonne", "Kyla", "Czarina", "Jhoanna", "Katrina", "Liza", "Mikaela",
           "Nadine", "Pia", "Rina", "Sofia", "Janella", "Aira", "Bea", "Carla", "Denise", "Ellaine",
           "Faith", "Gwen", "Ivy", "Joyce", "Mary Grace", "Ana Patricia"]
FIRST_M = ["Angelo", "Bryan", "Carlo", "Dennis", "Enrico", "Gabriel", "Harold", "Ian", "Jericho", "Kenneth",
           "Lorenzo", "Marco", "Nathaniel", "Paolo", "Rafael", "Sebastian", "Timothy", "Vincent", "Xavier",
           "Zandro", "John Paul", "John Carlo", "Mark Anthony", "Jose Miguel", "Juan Carlos", "Christian",
           "Ramon", "Joaquin", "Aldrin", "Benedict", "Cedric", "Dominic", "Emmanuel", "Gerald", "Jomar",
           "Kevin", "Louis", "Neil", "Patrick", "Renz"]
SURNAMES = ["Santos", "Reyes", "Cruz", "Bautista", "Ocampo", "Garcia", "Mendoza", "Torres", "Dela Cruz",
            "Villanueva", "Castillo", "Aquino", "Navarro", "Ramos", "Flores", "Gonzales", "Lopez", "Rivera",
            "Pascual", "Manalo", "Salazar", "Domingo", "De Guzman", "Aguilar", "Mercado", "Soriano",
            "Tolentino", "Valdez", "Cabrera", "Dizon", "Agustin", "Magno", "Marasigan", "Rodriguez", "Tagle",
            "Ilagan", "Gutierrez", "Panganiban", "Macaraeg", "Evangelista", "Alcantara", "Buenaventura",
            "Concepcion", "De Leon", "Enriquez", "Fernandez", "Galang", "Hernandez", "Ignacio", "Javier",
            "Lazaro", "Maglaya", "Natividad", "Olivares", "Pineda", "Quizon", "Robles", "Sison", "Trinidad",
            "Umali", "Vergara", "Zamora", "Banaag", "Carandang", "Esguerra", "Macalintal"]

def hhmm(m): return f"{m // 60:02d}:{m % 60:02d}"

# ---- names (unique, so demo-account emails never collide)
names, used = [], set()
while len(names) < 100:
    n = f"{R.choice(FIRST_F + FIRST_M)} {R.choice(SURNAMES)}"
    if n not in used:
        used.add(n); names.append(n)

# ---- section timetables
def build_section(year):
    sessions = []
    for s in LOAD[year]:
        sessions += [(s, 180, "Lab"), (s, 120, "Lec")] if s in LEC_LAB else [(s, 180, "")]
    for _ in range(500):
        placed, ok = [], True
        for s, dur, comp in sorted(sessions, key=lambda x: (-x[1], R.random())):
            cands = []
            for d in DAYS:
                today = [p for p in placed if p[0] == d]
                if any(p[3] == s for p in today) or sum(p[2] - p[1] for p in today) + dur > 540:
                    continue
                if d == "Saturday" and len(today) >= 2:
                    continue
                for start in range(7 * 60, 17 * 60 - dur + 1, 60):
                    if any(start < p[2] and start + dur > p[1] for p in today):
                        continue
                    adj = any(start == p[2] or start + dur == p[1] for p in today)
                    cands.append(((d, start), DAY_W[DAYS.index(d)] * (3 if adj else 1)))
            if not cands:
                ok = False; break
            (d, start), = R.choices([c for c, _ in cands], [w for _, w in cands])
            placed.append((d, start, start + dur, s, comp))
        if ok:
            return sorted(placed, key=lambda p: (DAYS.index(p[0]), p[1]))
    raise RuntimeError("cannot place section")

sections = {y: [build_section(y) for _ in range(SECTIONS[y])] for y in LOAD}

# ---- students
students, schedule = [], []
for y in (1, 2, 3, 4):
    for i in range(YEAR_COUNT[y]):
        students.append({"year": y, "section": i % SECTIONS[y]})
R.shuffle(students)
for sid, s in enumerate(students, 1):
    s["id"], s["name"] = sid, names[sid - 1]
    s["course"] = "BIT" if R.random() < 0.2 else "BCS"
    s["langs"] = R.choices([["Filipino", "English"], ["Filipino"], ["English"]], [55, 25, 20])[0]
    pool = [x for x in LOAD[s["year"]] if x not in (19, 20)]
    w = [3 if x == 11 else 2 if x == 4 else 1 for x in pool]
    k = R.choices([1, 2, 3], [60, 30, 10])[0]
    need = set()
    while len(need) < min(k, len(pool)):
        need.add(R.choices(pool, w)[0])
    s["needs"] = sorted(need)
y2 = [x for x in students if x["year"] == 2]
for x in y2[:4]:      # need ONLY Information Management: nobody teaches it
    x["needs"] = [6]
for x in y2[4:18]:    # need ONLY Discrete Structures 1: 14 students, 7 tutor spots
    x["needs"] = [11]
sched_id = 0
for s in students:
    for d, a, b, sub, comp in sections[s["year"]][s["section"]]:
        sched_id += 1
        schedule.append((sched_id, s["id"], d, hhmm(a), hhmm(b), sub, comp))

# ---- tutors
tutors = []
for year, n in ((2, 5), (3, 13), (4, 12)):
    tutors += [{"year": year} for _ in range(n)]
for tid, t in enumerate(tutors, 1):
    t["id"], t["name"] = tid, names[70 + tid - 1]
    t["course"] = "BIT" if R.random() < 0.15 else "BCS"
    t["langs"] = R.choices([["Filipino", "English"], ["Filipino"], ["English"]], [65, 20, 15])[0]
    t["capacity"] = R.choice([2, 3, 3, 4, 4, 5, 5, 6])
    t["verified"] = 1
    t["subjects"] = set()
def eligible(t, sub):
    if sub in (19, 20): return False
    return SUBJECT_YEAR[sub] < t["year"] or (SUBJECT_YEAR[sub] == 4 and t["year"] == 4)
d1 = [t for t in R.sample([t for t in tutors if t["year"] >= 3], 3)]   # Discrete 1: scarce on purpose
for t, cap in zip(d1, (2, 2, 3)):
    t["subjects"].add(11); t["capacity"] = cap
for sub in [s for s in SUBJECT_YEAR if s not in (6, 11)]:               # 6 = nobody teaches it
    pool = [t for t in tutors if eligible(t, sub) and len(t["subjects"]) < 4]
    for t in R.sample(pool, min(2, len(pool))):
        t["subjects"].add(sub)
for t in tutors:
    extra = [s for s in SUBJECT_YEAR if s not in (6, 11) and eligible(t, s) and s not in t["subjects"]]
    while len(t["subjects"]) < R.choice([2, 3, 3, 4]) and extra:
        t["subjects"].add(extra.pop(R.randrange(len(extra))))
    if not t["subjects"]:
        t["subjects"].add(R.choice([s for s in (1, 2, 3, 10) if eligible(t, s)]))
for t in R.sample([t for t in tutors if t not in d1], 3):
    t["verified"] = 0
avail, aid = [], 0
for t in tutors:
    taken = []
    for _ in range(R.choice([2, 3, 3, 4])):
        for _ in range(50):
            d = R.choices(DAYS, DAY_W)[0]; ln = R.choice([1, 2, 2, 3]) * 60
            a = R.randrange(7, 17 - ln // 60 + 1) * 60
            if all(not (x[0] == d and a < x[2] and a + ln > x[1]) for x in taken):
                taken.append((d, a, a + ln)); break
    for d, a, b in sorted(taken, key=lambda x: (DAYS.index(x[0]), x[1])):
        aid += 1; avail.append((aid, t["id"], d, hhmm(a), hhmm(b)))

# ---- emit SQL
q = lambda s: "'" + s.replace("'", "''") + "'"
out = []
w = out.append
w("""-- TUGMA big seed: 100 profiles = 70 students (tutees) + 30 tutors, Filipino names.
-- Generated by generate_big_seed.py (deterministic). Replace database/seed.sql with this
-- file and rebuild the database to use it.
--
-- Schedule rules (DLSU-D, first semester AY 2026-2027), synthetic but consistent:
--   * every subject meets ONCE a week per component;
--   * a lecture meets 2 hours, a laboratory 3 hours, any subject without a
--     lecture/lab split (e.g. Discrete Structures 1, GE) meets 3 hours;
--   * lecture+lab subjects therefore have two rows (a 2-hour and a 3-hour one);
--   * classes run Monday to Saturday, 07:00 to 17:00, on whole hours;
--   * students are in block sections: classmates share one timetable.
-- Subjects 19-21 (Christian Commitment, Art Appreciation, Number Theory) are added
-- to the 18 CICS subjects because real timetables include them. Remove them (and the
-- rows that use them) if the dataset must stay strictly CICS.
-- Which subjects have a lab, and which year each subject belongs to, is an
-- approximation, not the official curriculum flowchart.
--
-- Built-in edge cases: 4 students need only S-ITCS226 and nobody teaches it (always
-- unmatched); 14 students need only S-CSPC212 but its 3 tutors have 7 spots in total
-- (capacity pressure); 3 tutors are unverified (an admin must verify them); many
-- students and tutors speak only one language, and some pairs share no free time.

PRAGMA foreign_keys = ON;
""")
w("-- 1. SUBJECTS\nINSERT INTO subjects (subject_id, subject_code, subject_name) VALUES")
w(",\n".join(f"    ({i}, {q(c)}, {q(n)})" for i, c, n in SUBJECTS) + ";\n")
w("-- 2. STUDENTS (tutees)\nINSERT INTO students (student_id, name, grade_level, course) VALUES")
w(",\n".join(f"    ({s['id']}, {q(s['name'])}, {s['year']}, {q(s['course'])})" for s in students) + ";\n")
w("-- 3. TUTORS\nINSERT INTO tutors (tutor_id, name, grade_level, course, verified, capacity) VALUES")
w(",\n".join(f"    ({t['id']}, {q(t['name'])}, {t['year']}, {q(t['course'])}, {t['verified']}, {t['capacity']})" for t in tutors) + ";\n")
w("-- 4. STUDENT SUBJECT NEEDS\nINSERT INTO student_subjects (student_id, subject_id) VALUES")
w(",\n".join(f"    ({s['id']}, {n})" for s in students for n in s["needs"]) + ";\n")
w("-- 5. TUTOR SUBJECTS\nINSERT INTO tutor_subjects (tutor_id, subject_id) VALUES")
w(",\n".join(f"    ({t['id']}, {n})" for t in tutors for n in sorted(t["subjects"])) + ";\n")
w("-- 6. STUDENT LANGUAGES\nINSERT INTO student_languages (student_id, language) VALUES")
w(",\n".join(f"    ({s['id']}, {q(l)})" for s in students for l in s["langs"]) + ";\n")
w("-- 7. TUTOR LANGUAGES\nINSERT INTO tutor_languages (tutor_id, language) VALUES")
w(",\n".join(f"    ({t['id']}, {q(l)})" for t in tutors for l in t["langs"]) + ";\n")
w("-- 8. STUDENT ACADEMIC SCHEDULE (comment = subject code and component)\n"
  "INSERT INTO student_schedule (schedule_id, student_id, day, start_time, end_time, subject_id) VALUES")
rows = []
for i, (sid, stu, d, a, b, sub, comp) in enumerate(schedule):
    tail = "; -- " if i == len(schedule) - 1 else ", -- "
    rows.append(f"    ({sid}, {stu}, {q(d)}, {q(a)}, {q(b)}, {sub}){tail}{CODE[sub]} {comp}".rstrip())
w("\n".join(rows) + "\n")
w("-- 9. TUTOR AVAILABILITY\nINSERT INTO tutor_availability (availability_id, tutor_id, day, start_time, end_time) VALUES")
w(",\n".join(f"    ({i}, {t}, {q(d)}, {q(a)}, {q(b)})" for i, t, d, a, b in avail) + ";")
print("\n".join(out))