import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    """Set cell borders in a simple clean style."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    
    for edge, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        if val is not None:
            el = OxmlElement(f'w:{edge}')
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), '4')  # 0.5 pt
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), '000000')
            tcBorders.append(el)
        else:
            el = OxmlElement(f'w:{edge}')
            el.set(qn('w:val'), 'none')
            tcBorders.append(el)
    tcPr.append(tcBorders)

def add_clean_table(doc, headers, data, col_widths=None):
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Format header row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = 'Times New Roman'
            r.font.size = Pt(10)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0, 0, 0)
        set_cell_borders(hdr_cells[i], top=True, bottom=True, left=True, right=True)

    # Format data rows
    for r_idx, row_data in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            p = row_cells[c_idx].paragraphs[0]
            # Center if short number, left align if text
            if len(str(val)) <= 8 and ('%' in str(val) or str(val).replace('.', '', 1).isdigit() or str(val) in ('Yes', 'No')):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(0, 0, 0)
            set_cell_borders(row_cells[c_idx], top=True, bottom=True, left=True, right=True)

    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)

    doc.add_paragraph()  # Spacing after table
    return table

def build_report():
    doc = docx.Document()

    # 1-inch margins all around
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base Normal Style: Times New Roman, 12pt, black
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    font.color.rgb = RGBColor(0, 0, 0)
    style.paragraph_format.line_spacing = 1.15
    style.paragraph_format.space_after = Pt(4)

    # Helper for headings
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0, 0, 0)
        return p

    # --- TITLE & METADATA ---
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(6)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    trun = title_p.add_run("TECHNICAL REPORT:\nMODEL-BASED TESTING FOR SMART PARCEL LOCKER MANAGEMENT SYSTEM")
    trun.font.name = 'Times New Roman'
    trun.font.size = Pt(16)
    trun.font.bold = True
    trun.font.color.rgb = RGBColor(0, 0, 0)

    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_before = Pt(0)
    meta_p.paragraph_format.space_after = Pt(14)
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mrun = meta_p.add_run("Student Name: Umair Hassan   |   Roll No: 24i-3137\nCourse: Software Testing & Quality Assurance / Model-Based Testing\nDate: November 2026")
    mrun.font.name = 'Times New Roman'
    mrun.font.size = Pt(11)
    mrun.font.bold = True
    mrun.font.color.rgb = RGBColor(0, 0, 0)

    # --- 1. INTRODUCTION ---
    add_h1("1. Introduction")
    add_h2("1.1 Assignment Objectives")
    doc.add_paragraph(
        "Model-Based Testing (MBT) is an advanced quality-assurance paradigm in which an abstract, formal specification "
        "of a software system serves as an executable ground truth (test oracle). Rather than hand-crafting static test "
        "cases, MBT systematically explores the system's behavioral state space, synthesizes valid and invalid operation "
        "sequences, executes them against the implementation under test (System Under Test, or SUT), and automatically "
        "detects divergences in operation return values, observable state snapshots, and safety invariants."
    )
    doc.add_paragraph(
        "The primary objectives of this project are:\n"
        "1. Constructing an independent, executable state-machine model of a Smart Parcel Locker.\n"
        "2. Implementing three algorithmically distinct automated test-generation strategies (Random Walk, Coverage-Guided, and Transition-Pair).\n"
        "3. Building an automated execution engine with independent multi-oracle diagnostics.\n"
        "4. Engineering a suite of 10 realistic faulty system implementations (mutants) with formal equivalence metadata.\n"
        "5. Conducting controlled, reproducible experiments across 5 random seeds to evaluate coverage, mutation detection, and efficiency."
    )

    add_h2("1.2 Case Study: Smart Parcel Locker System")
    doc.add_paragraph(
        "The Smart Parcel Locker is an automated self-service station where couriers deposit parcels and customers retrieve them "
        "using secure credentials. Strict operational rules govern the locker lifecycle: parcels cannot be reserved if occupied or "
        "undergoing maintenance, deposits require matching reservation codes, retrievals require authentic one-time PINs, and "
        "canceled or expired reservations must promptly reset the compartment to available status without credential leakage."
    )

    # --- 2. REQUIREMENTS ANALYSIS ---
    add_h1("2. Requirements Analysis and Behavioral Rules")
    add_h2("2.1 System States")
    doc.add_paragraph(
        "The locker compartment operates across four primary conceptual states:\n"
        "• AVAILABLE: Compartment is clean, empty, and ready for a new reservation.\n"
        "• RESERVED: Compartment is reserved for a customer; awaiting parcel deposit.\n"
        "• OCCUPIED: Parcel has been placed inside and securely locked, awaiting pickup.\n"
        "• MAINTENANCE: Compartment is taken offline for servicing, inspection, or repairs."
    )

    add_h2("2.2 System Operations")
    doc.add_paragraph(
        "The system accepts eight distinct operations: RESERVE, CANCEL, DEPOSIT, RETRIEVE, EXPIRE, DISABLE, ENABLE, and INVALID_ACCESS."
    )

    add_h2("2.3 Formal State Transition Table")
    headers_req = ["Operation", "Source State", "Precondition / Guard", "Target State", "Result Message", "Post-Condition Updates"]
    data_req = [
        ["RESERVE", "AVAILABLE", "Valid customer_id", "RESERVED", "reserved", "Generates R-<customer_id>"],
        ["CANCEL", "RESERVED", "None", "AVAILABLE", "cancelled", "Clears customer & reservation code"],
        ["DEPOSIT", "RESERVED", "code == reservation_code", "OCCUPIED", "deposited", "Generates P-<customer_id>"],
        ["RETRIEVE", "OCCUPIED", "code == retrieval_code", "AVAILABLE", "retrieved", "Clears customer & credentials"],
        ["EXPIRE", "RESERVED", "expired == True", "AVAILABLE", "expired", "Clears customer & credentials"],
        ["DISABLE", "AVAILABLE", "None", "MAINTENANCE", "disabled", "Compartment locked out"],
        ["ENABLE", "MAINTENANCE", "None", "AVAILABLE", "enabled", "Compartment returned to service"],
        ["INVALID_ACCESS", "Any State", "None", "No Change", "invalid_access", "No state or credential mutation"],
    ]
    add_clean_table(doc, headers_req, data_req, [1.0, 1.0, 1.4, 1.0, 1.0, 1.6])

    # --- 3. STATE-MACHINE MODEL & INVARIANTS ---
    add_h1("3. State-Machine Model & Invariants")
    doc.add_paragraph(
        "The executable model in locker/model.py serves as the independent ground truth. It never calls or imports the SUT. "
        "The model maintains independent state variables: state, customer_id, reservation_code, and retrieval_code."
    )
    add_h2("3.1 State Machine Structure")
    doc.add_paragraph(
        "The lifecycle follows formal transition arcs:\n"
        "• AVAILABLE --RESERVE--> RESERVED\n"
        "• AVAILABLE --DISABLE--> MAINTENANCE\n"
        "• RESERVED --DEPOSIT--> OCCUPIED\n"
        "• RESERVED --CANCEL--> AVAILABLE\n"
        "• RESERVED --EXPIRE--> AVAILABLE\n"
        "• OCCUPIED --RETRIEVE--> AVAILABLE\n"
        "• MAINTENANCE --ENABLE--> AVAILABLE\n"
        "All other transitions represent invalid state-event combinations that are rejected without modifying system state."
    )

    add_h2("3.2 Domain Safety Invariants")
    doc.add_paragraph(
        "The test oracle continuously asserts the following domain invariants:\n"
        "1. Empty State Cleanliness: In AVAILABLE and MAINTENANCE, customer_id, reservation_code, and retrieval_code must all be None.\n"
        "2. Reservation Integrity: In RESERVED, customer_id must be non-empty, reservation_code must equal f'R-{customer_id}', and retrieval_code must be None.\n"
        "3. Occupancy Integrity: In OCCUPIED, customer_id must be non-empty, and retrieval_code must equal f'P-{customer_id}'.\n"
        "4. Non-Mutation of Rejected Operations: If an operation returns accepted=False, the post-state snapshot must match the pre-state snapshot bit-for-bit.\n"
        "5. No Double Retrieval: Once retrieved, the compartment returns to AVAILABLE and cannot be retrieved again with the prior PIN."
    )

    # --- 4. TRANSITION-PAIR COVERAGE ---
    add_h1("4. Transition-Pair Coverage Definition & Calculation")
    doc.add_paragraph(
        "An individual state transition is represented as a 3-tuple: t = (source_state, operation, target_state).\n"
        "A valid transition pair consists of two consecutive valid transitions (t1, t2) where t1.target_state == t2.source_state."
    )
    doc.add_paragraph(
        "The locker model defines 7 valid primary transitions:\n"
        "• t1: (AVAILABLE, RESERVE, RESERVED)\n"
        "• t2: (AVAILABLE, DISABLE, MAINTENANCE)\n"
        "• t3: (RESERVED, DEPOSIT, OCCUPIED)\n"
        "• t4: (RESERVED, CANCEL, AVAILABLE)\n"
        "• t5: (RESERVED, EXPIRE, AVAILABLE)\n"
        "• t6: (OCCUPIED, RETRIEVE, AVAILABLE)\n"
        "• t7: (MAINTENANCE, ENABLE, AVAILABLE)"
    )
    doc.add_paragraph(
        "The total number of connected transition pairs is derived from the in-degrees and out-degrees of the intermediate states:\n"
        "• Via RESERVED (in=1, out=3): 3 pairs (t1->t3, t1->t4, t1->t5)\n"
        "• Via OCCUPIED (in=1, out=1): 1 pair (t3->t6)\n"
        "• Via MAINTENANCE (in=1, out=1): 1 pair (t2->t7)\n"
        "• Via AVAILABLE (in=4, out=2): 8 pairs (t4, t5, t6, t7 -> t1, t2)\n"
        "Total Connected Transition Pairs = 3 + 1 + 1 + 8 = 13 pairs (denominator)."
    )
    doc.add_paragraph(
        "Accounting Rules Enforced in locker/metrics.py:\n"
        "1. Disconnected combinations (e.g. t2 ending in MAINTENANCE followed by t1 starting in AVAILABLE) are rejected.\n"
        "2. Rejected operations break the transition chain (setting prev_trans = None).\n"
        "3. Sequence boundaries reset transition pair tracking.\n"
        "4. Repeated pairs do not artificially inflate the coverage score."
    )

    # --- 5. TEST-GENERATION STRATEGIES ---
    add_h1("5. Test-Generation Strategies")
    doc.add_paragraph(
        "Three algorithmically distinct test generators were implemented in locker/generators.py:"
    )
    add_h2("5.1 Strategy A: Random Walk Generator (RandomWalkGenerator)")
    doc.add_paragraph(
        "• Algorithm: Samples operations uniformly at random. At each step, a 60% bias attempts valid parameters, while a 40% bias "
        "intentionally supplies faulty parameters (wrong reservation codes, invalid PINs, unexpired flags).\n"
        "• Advantages: Highly efficient generation (O(1) per step), unbiased state exploration, excellent at fuzzing unexpected inputs.\n"
        "• Limitations: Lacks systematic path memory; inefficient at traversing specific deep sequential paths."
    )
    add_h2("5.2 Strategy B: Coverage-Guided Generator (CoverageGuidedGenerator)")
    doc.add_paragraph(
        "• Algorithm: Maintains a global frequency matrix tracking (state, op, accepted) tuples and state visit counts across sequences. "
        "At each step, evaluates all 16 candidate combinations (8 ops x valid/invalid) via dry-run simulation and greedily selects the action "
        "minimizing prior execution frequency (novelty search).\n"
        "• Advantages: Rapidly achieves 100% state coverage and state-operation coverage by systematically probing unexplored state-event spaces.\n"
        "• Limitations: Incurs evaluation latency due to dry-run lookaheads at every step."
    )
    add_h2("5.3 Strategy C: Transition-Pair Generator (TransitionPairGenerator)")
    doc.add_paragraph(
        "• Algorithm: Targets the 13 valid connected transition pairs. Tracks a global set of covered pairs. At each step, it steers through "
        "outgoing transitions that complete an uncovered pair with the predecessor transition, with lookaheads towards states containing future "
        "uncovered pairs. Additionally, a configurable negative-operation rate (invalid_prob = 0.20) injects state-tailored invalid commands "
        "(wrong PINs, illegal operations) that break the chain without mutating model state.\n"
        "• Advantages: Directly exercises sequential lifecycle dependencies and transition-pair combinations while still fuzzing guards.\n"
        "• Limitations: Slightly slower generation than pure random walk due to graph lookahead calculations."
    )

    # --- 6. TEST RUNNER & MULTI-ORACLE DIAGNOSTICS ---
    add_h1("6. Automated Test Runner & Independent Multi-Oracle Diagnostics")
    doc.add_paragraph(
        "The test execution engine (locker/runner.py) executes command sequences against fresh instances of the SUT and model. "
        "To prevent diagnostic masking, the runner evaluates all five verification dimensions independently at every step:\n"
        "1. Operation Result Comparison: Asserts expected.accepted == actual.accepted and expected.message == actual.message.\n"
        "2. Complete Snapshot Comparison: Asserts exact matching of state, customer_id, reservation_code, and retrieval_code.\n"
        "3. Domain Invariant Verification: Verifies safety invariants on SUT observable fields.\n"
        "4. Non-Mutation Verification: Ensures that rejected operations do not alter state or credentials.\n"
        "5. Credential Cleanup Verification: Verifies that successful CANCEL, EXPIRE, and RETRIEVE wipe all credentials.\n"
        "If multiple checks fail on a single step, all violations are recorded in step_records and failure_details without masking."
    )

    # --- 7. MUTATION TESTING & EQUIVALENCE ---
    add_h1("7. Mutation Testing & Equivalence Analysis")
    doc.add_paragraph(
        "Ten realistic faulty implementations (mutants) were developed in locker/mutants.py. Each mutant introduces an isolated defect. "
        "Every mutant has formal metadata documenting defect category and non-equivalence justification:"
    )

    headers_mut = ["Mutant Identifier", "Defect Category", "Equiv?", "Defect Description & Non-Equivalence Justification"]
    data_mut = [
        ["Mutant1_ReserveOccupied", "Precondition Bypass", "No", "Allows RESERVE when OCCUPIED. SUT rejects with locker_not_available; mutant returns reserved."],
        ["Mutant2_AcceptWrongReservationCode", "Credential Bypass", "No", "Accepts deposit with wrong reservation code. SUT rejects; mutant transitions to OCCUPIED."],
        ["Mutant3_RetrieveWithoutAuth", "Authentication Bypass", "No", "Allows retrieval with invalid PIN. SUT rejects; mutant returns retrieved."],
        ["Mutant4_DoubleRetrieve", "Cleanup Omission", "No", "Fails to clear locker on retrieval. State remains OCCUPIED, allowing duplicate retrieval."],
        ["Mutant5_ExpireWhenNotExpired", "Guard Omission", "No", "Expires reservation when expired=False. SUT rejects; mutant prematurely expires."],
        ["Mutant6_CancelRetainsCredentials", "Invariant Violation", "No", "Fails to clear credentials on cancel. Credentials remain non-None in AVAILABLE state."],
        ["Mutant7_MaintenanceWhenReserved", "Precondition Bypass", "No", "Allows DISABLE when RESERVED. SUT rejects with cannot_disable; mutant enters MAINTENANCE."],
        ["Mutant8_EnableWhenNotMaintenance", "Precondition Bypass", "No", "Allows ENABLE when not in MAINTENANCE. SUT rejects; mutant returns enabled."],
        ["Mutant9_DepositDuringMaintenance", "Precondition Bypass", "No", "Allows deposit into MAINTENANCE compartment. SUT rejects; mutant accepts deposit."],
        ["Mutant10_MutateOnInvalidDeposit", "Non-Mutation Violation", "No", "Corrupts retrieval_code on rejected deposit, violating the non-mutation invariant."],
    ]
    add_clean_table(doc, headers_mut, data_mut, [1.5, 1.2, 0.6, 3.2])

    doc.add_paragraph(
        "Mutation Score Formula: Mutation Score = (Detected Non-Equivalent Mutants / Total Non-Equivalent Mutants) * 100. "
        "Equivalent mutants are excluded from the denominator."
    )

    # --- 8. EXPERIMENTAL SETUP ---
    add_h1("8. Experimental Setup & Fairness")
    doc.add_paragraph(
        "To ensure rigorous experimental fairness across all three strategies:\n"
        "• Number of Strategies: 3 (RandomWalk, CoverageGuided, TransitionPair)\n"
        "• Sequences per Strategy: 500 test sequences\n"
        "• Sequence Length Budget: Exactly 20 operations per sequence across all strategies (10,000 operations per strategy evaluation)\n"
        "• Random Seeds: 5 independent seeds (101, 202, 303, 404, 505)\n"
        "• Evaluated Mutants: 10 non-equivalent mutants\n"
        "• Total SUT Executions: 7,500 test sequences against reference SUT, plus full mutant evaluation runs."
    )

    # --- 9. EXPERIMENTAL RESULTS ---
    add_h1("9. Experimental Results")
    add_h2("9.1 Aggregated Comparison Table (Averaged Over 5 Seeds)")
    headers_res = ["Strategy", "State Cov (%)", "Valid Trans (%)", "State-Op Cov (%)", "Trans-Pair Cov (%)", "Mutation Score (%)", "Std Dev", "Detected (/10)", "Gen Time (s)", "SUT Time (s)"]
    data_res = [
        ["RandomWalk", "100.0%", "100.0%", "100.0%", "100.0%", "100.0%", "0.00", "10.0 / 10", "0.2017 s", "0.3172 s"],
        ["CoverageGuided", "100.0%", "100.0%", "100.0%", "64.62%", "100.0%", "0.00", "10.0 / 10", "2.2369 s", "0.2928 s"],
        ["TransitionPair", "100.0%", "100.0%", "93.75%", "100.0%", "90.0%", "0.00", "9.0 / 10", "0.3729 s", "0.4415 s"],
    ]
    add_clean_table(doc, headers_res, data_res, [1.0, 0.6, 0.6, 0.6, 0.6, 0.7, 0.5, 0.6, 0.6, 0.6])

    add_h2("9.2 Mutant Detection Matrix (% of Seeds Detecting Mutant)")
    headers_mat = ["Mutant Identifier", "Defect Category", "Equiv", "RandomWalk", "CoverageGuided", "TransitionPair"]
    data_mat = [
        ["Mutant1_ReserveOccupied", "Precondition Bypass", "No", "100%", "100%", "100%"],
        ["Mutant2_AcceptWrongReservationCode", "Credential Bypass", "No", "100%", "100%", "100%"],
        ["Mutant3_RetrieveWithoutAuth", "Authentication Bypass", "No", "100%", "100%", "100%"],
        ["Mutant4_DoubleRetrieve", "Cleanup Omission", "No", "100%", "100%", "100%"],
        ["Mutant5_ExpireWhenNotExpired", "Guard Omission", "No", "100%", "100%", "100%"],
        ["Mutant6_CancelRetainsCredentials", "Invariant Violation", "No", "100%", "100%", "100%"],
        ["Mutant7_MaintenanceWhenReserved", "Precondition Bypass", "No", "100%", "100%", "0%"],
        ["Mutant8_EnableWhenNotMaintenance", "Precondition Bypass", "No", "100%", "100%", "100%"],
        ["Mutant9_DepositDuringMaintenance", "Precondition Bypass", "No", "100%", "100%", "100%"],
        ["Mutant10_MutateOnInvalidDeposit", "Non-Mutation Violation", "No", "100%", "100%", "100%"],
    ]
    add_clean_table(doc, headers_mat, data_mat, [1.8, 1.4, 0.6, 0.9, 0.9, 0.9])

    # --- 10. DISCUSSION & LIMITATIONS ---
    add_h1("10. Discussion & Limitations")
    add_h2("10.1 Comparative Analysis & Trade-offs")
    doc.add_paragraph(
        "1. TransitionPairGenerator Performance: With negative-operation selection enabled (invalid_prob = 0.20), TransitionPairGenerator "
        "achieved a 90.0% mutation score across all 5 seeds while achieving 100.0% transition-pair coverage (all 13 connected pairs). "
        "It successfully killed 9 out of 10 mutants, including complex parameter validation bugs (Mutants 2, 3, 5, 10) and lifecycle bugs (Mutants 1, 4, 6, 8, 9). "
        "The only surviving mutant was Mutant 7 (attempting DISABLE while RESERVED), because the generator's state-machine traversal favored "
        "transitioning through valid lifecycle events rather than taking an occupied locker into maintenance."
    )
    doc.add_paragraph(
        "2. Coverage-Guided Trade-off: CoverageGuidedGenerator achieved a 100.0% mutation score and 100.0% state-operation coverage, but "
        "achieved 64.62% transition-pair coverage. Because its novelty heuristic systematically samples every unvisited state-event combination, "
        "it frequently executes invalid operations, which break the consecutive valid transition chain required to form a valid transition pair."
    )
    doc.add_paragraph(
        "3. Computational Efficiency: RandomWalk was the fastest (0.202s generation time), while CoverageGuided required 2.237s due to 16 dry-run "
        "simulations per step. TransitionPair balanced generation speed (0.373s) with structured graph exploration."
    )
    add_h2("10.2 Limitations & Threats to Validity")
    doc.add_paragraph(
        "• Single-Compartment Scope: The system models one compartment at a time; multi-compartment capacity constraints were abstracted.\n"
        "• Synthesized Mutation: Mutants were manually injected based on typical real-world errors."
    )

    # --- 11. CONCLUSION ---
    add_h1("11. Conclusion")
    doc.add_paragraph(
        "The Model-Based Testing framework successfully models the Smart Parcel Locker and validates it through automated multi-oracle execution. "
        "Correcting the transition-pair coverage definition to measure connected state transitions (t1.target == t2.source) and incorporating "
        "deliberate negative-operation synthesis achieved 100% transition-pair coverage and 90% mutation detection under fair experimental conditions."
    )

    # --- 12. EVIDENCE, SCREENSHOTS & VIVA PREPARATION ---
    add_h1("12. Student Evidence, Terminal Screenshots & Viva Preparation")
    add_h2("12.1 Terminal Execution Screenshots")
    doc.add_paragraph("Figure 1: Full Unit & Multi-Oracle Test Suite Execution (All 41 tests passing):")
    if os.path.exists("docs/screenshots/unit_tests_run.png"):
        doc.add_picture("docs/screenshots/unit_tests_run.png", width=Inches(6.2))
        doc.add_paragraph()

    doc.add_paragraph("Figure 2: Controlled Experimental Evaluation Run across 5 seeds and 10 mutants:")
    if os.path.exists("docs/screenshots/experiments_run.png"):
        doc.add_picture("docs/screenshots/experiments_run.png", width=Inches(6.2))
        doc.add_paragraph()

    add_h2("12.2 Visual Charts from Experimental Results")
    if os.path.exists("results/coverage_comparison.png"):
        doc.add_paragraph("Figure 3: Coverage Metrics Comparison Across Strategies:")
        doc.add_picture("results/coverage_comparison.png", width=Inches(5.5))
        doc.add_paragraph()

    if os.path.exists("results/mutation_score_comparison.png"):
        doc.add_paragraph("Figure 4: Mutation Score Comparison Across Strategies:")
        doc.add_picture("results/mutation_score_comparison.png", width=Inches(4.8))
        doc.add_paragraph()

    if os.path.exists("results/execution_time_comparison.png"):
        doc.add_paragraph("Figure 5: Execution Time Breakdown Across Strategies:")
        doc.add_picture("results/execution_time_comparison.png", width=Inches(4.8))
        doc.add_paragraph()

    add_h2("12.3 Individual Viva Preparation Guide")
    doc.add_paragraph(
        "During the individual viva, if an unseen requirement change is presented by the instructor:\n"
        "• Change A (Allow maintenance while OCCUPIED): In locker/model.py, update the DISABLE guard to permit state in (AVAILABLE, OCCUPIED). Update LockerModel.verify_invariants to permit customer_id during maintenance if occupied.\n"
        "• Change B (Allow cancel with additional condition or fee): Add the parameter to Command in locker/types.py and update the CANCEL logic in locker/model.py.\n"
        "• Change C (Introduce new state EXPIRED): Add EXPIRED to State enum in locker/types.py, update EXPIRE transition in locker/model.py to transition to State.EXPIRED instead of directly to AVAILABLE."
    )

    output_path = os.path.abspath("report.docx")
    doc.save(output_path)
    print(f"Report generated successfully at: {output_path}")

if __name__ == "__main__":
    build_report()
