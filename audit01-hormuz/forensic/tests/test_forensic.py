#!/usr/bin/env python3
"""Unit + end-to-end tests on synthetic fixtures (no PortWatch data). Run: python3 -m unittest discover -s forensic/tests -v"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import core, make_fixtures  # noqa: E402


def _json(p):
    with open(p) as fh:
        return json.load(fh)


def _sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()

# closed-form expectations for the synthetic world (audit window 2026-03-01..2026-09-25 = 209 days)
WIN_DAYS = 209
EXP_A = 15000 * WIN_DAYS                     # portA net
EXP_105 = 2000000 + 7 * 1000                 # burst day 2026-03-07 + the 1st of each month Mar..Sep
EXP_C = 1000 * WIN_DAYS


class Synthetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.raw = make_fixtures.write(os.path.join(cls.tmp, "raw"))
        cls.d = core.load_raw(cls.raw)
        cls.sets, cls.by = core.port_sets(cls.d["ports"])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_port_rule_excludes_outside(self):
        self.assertEqual(self.sets["audit_45"], {"portA", "port105"})
        self.assertEqual(self.sets["box_rule"], {"portA", "port105"})

    def test_balance_exact(self):
        b = core.balance(self.d, self.sets["audit_45"], 202603)
        self.assertEqual(b["net_t"], EXP_A + EXP_105)
        self.assertEqual(b["C_t"], EXP_C)
        self.assertEqual(b["L_t"], EXP_A + EXP_105 - EXP_C)
        self.assertEqual(core.data_end(self.d["pm"]), "2026-09-25")

    def test_unit_conversion_t_to_Mt(self):
        b = core.balance(self.d, self.sets["audit_45"], 202603)
        self.assertAlmostEqual(b["L_t"] / 1e6, (EXP_A + EXP_105 - EXP_C) / 1e6, places=9)

    def test_burst_days(self):
        sel, rm = core.burst_days(self.d, "2026-03-01", "2026-09-25", 3)
        self.assertEqual([r["date"] for r in sel], ["2026-03-07"])
        self.assertEqual(rm, 2000000)

    def test_no_duplicates_and_no_gaps(self):
        self.assertEqual(sum(core.duplicates(self.d).values()), 0)
        g = core.gaps(self.d, self.sets["audit_45"], "2026-09-25")
        self.assertEqual((len(g["chokepoint_missing_dates"]), len(g["port_months_absent"]), len(g["port_months_short"])), (0, 0, 0))

    def test_duplicate_detection(self):
        d = core.load_raw(self.raw)
        d["pm"].append(dict(d["pm"][0]))
        d["ch"].append(dict(d["ch"][5]))
        du = core.duplicates(d)
        self.assertEqual((du["port_month_dup_keys"], du["chokepoint_dup_dates"], du["port_month_identical_rows"]), (1, 1, 1))

    def test_gap_detection(self):
        d = core.load_raw(self.raw)
        d["ch"] = [r for r in d["ch"] if r["date"] != "2025-05-05"]
        g = core.gaps(d, self.sets["audit_45"], "2026-09-25")
        self.assertEqual(g["chokepoint_missing_dates"], ["2025-05-05"])

    def test_epoch_dates_equal_string_dates(self):
        raw2 = make_fixtures.write(os.path.join(self.tmp, "raw_epoch"), epoch_dates=True)
        d2 = core.load_raw(raw2)
        self.assertEqual(core.balance(d2, self.sets["audit_45"], 202603), core.balance(self.d, self.sets["audit_45"], 202603))

    def test_negative_control_pre_crisis_ratio_below_one(self):
        rho = core.monthly_rho(self.d, self.sets["audit_45"], core.ym_range(201901, 202602))
        self.assertLessEqual(max(rho.values()), 1.0)          # 30,000+ / 120,000 per day ~ 0.25

    def test_negative_control_shuffled_terminal(self):
        p = core.permutation_port105(self.d, core.ym_range(202603, 202609), core.ym_range(201901, 202602), n=500)
        self.assertLess(p["p_random_months"], 0.05)            # synthetic terminal has no pre-crisis bursts
        self.assertEqual(p["blocks_ge_observed"], 0)

    def test_leave_one_out(self):
        loo = dict(core.leave_one_out(self.d, self.sets["audit_45"], 202603))
        self.assertAlmostEqual(loo["port105"], EXP_105 / 1e6)


class EndToEnd(unittest.TestCase):
    def test_runner_on_synthetic(self):
        tmp = tempfile.mkdtemp()
        try:
            raw = make_fixtures.write(os.path.join(tmp, "data", "raw"))
            out = os.path.join(tmp, "out")
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "run_forensic.py"), "--raw", raw, "--out", out,
                                "--perm-draws", "300", "--compare", f"same={raw}"], capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr)
            res = _json(os.path.join(out, "results.json"))
            man = _json(os.path.join(out, "manifest.json"))
            st = {c["id"]: c["status"] for c in res["checks"]}
            self.assertTrue(all(v in ("PASS", "FAIL", "UNKNOWN") for v in st.values()))
            self.assertEqual(st["published_numbers_reproduce"], "FAIL")      # synthetic numbers must not match the thread
            self.assertEqual(st["duplicate_keys"], "PASS")
            self.assertEqual(st["row_completeness"], "PASS")
            self.assertEqual(st["revision_sensitivity"], "PASS")              # identical release compared with itself
            self.assertEqual(st["negative_control_pre_crisis_windows"], "PASS")
            self.assertEqual(st["negative_control_shuffled_terminal"], "PASS")
            self.assertEqual(st["capacity_field_definition"], "UNKNOWN")      # docs not fetched
            self.assertEqual(res["measurements"]["window_audit_2026-03-01"]["gap_Mt"], (EXP_A + EXP_105 - EXP_C) / 1e6)
            for k in ("code", "dependencies", "inputs", "outputs", "portwatch_release"):
                self.assertIn(k, man)
            self.assertEqual(man["outputs"]["results.json"], _sha(os.path.join(out, "results.json")))
            self.assertTrue(all(len(i["sha256"]) == 64 for i in man["inputs"]))
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
