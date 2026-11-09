import unittest

from agency.inbox.cost import Ledger
from agency.inbox.triage import (CODE, FYI, IMPORTANT, KEEP_NOISE, NOISE, PENDING, KeywordJudge, Mail, Triage,
                                 mask_numbers, summary)


def mail(i, subject, body="", sender="someone@example.com", thread=None, tab="primary"):
    return Mail(id=f"m{i}", thread=thread or f"t{i}", sender=sender, subject=subject, body=body, tab=tab)


class TriageTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger({"judge-model": (1.0, 5.0)})
        self.t = Triage(owner_threads={"t-mine"}, noise_senders=("deals@shop.example",),
                        judge=KeywordJudge(), ledger=self.ledger)

    def test_codes_are_never_stored(self):
        d = self.t.decide(mail(1, "Your verification code", "Your verification code is 482913."))
        self.assertEqual((d.verdict, d.by, d.kept), (CODE, "rule", ""))

    def test_rules_decide_first_and_cost_nothing(self):
        out = self.t.run([mail(2, "Re: schedule", "Tuesday works", thread="t-mine"),
                          mail(3, "50% off today", sender="deals@shop.example"),
                          mail(4, "New arrivals", tab="promotions")])
        self.assertEqual([(d.verdict, d.by) for d in out], [(IMPORTANT, "rule"), (NOISE, "rule"), (NOISE, "rule")])
        self.assertEqual(self.ledger.rows, [])

    def test_a_promotions_tab_mail_with_a_work_signal_still_reaches_the_judge(self):
        d = self.t.decide(mail(5, "Interview slots for next week", tab="promotions"))
        self.assertEqual((d.verdict, d.by), (IMPORTANT, "judge"))
        self.assertEqual(len(self.ledger.rows), 1)

    def test_the_judge_is_costed_per_call(self):
        self.t.run([mail(6, "Payment receipt"), mail(7, "Hello there")])
        self.assertEqual(self.ledger.by_action()["triage"]["calls"], 2)
        self.assertGreater(self.ledger.total_usd(), 0)

    def test_no_clear_answer_is_never_a_guess(self):
        for judge in (lambda m: ("MAYBE", "", 10, 1), lambda m: 1 / 0):
            t = Triage(judge=judge, ledger=Ledger({"judge-model": (1.0, 1.0)}))
            d = t.decide(mail(8, "Something unclear"))
            self.assertEqual(d.verdict, PENDING)
            self.assertIn("next run", d.why)

    def test_what_the_log_keeps(self):
        long_body = "x" * (KEEP_NOISE + 100)
        self.assertEqual(len(self.t.decide(mail(9, "New arrivals", long_body, tab="promotions")).kept), KEEP_NOISE)
        self.assertEqual(len(self.t.decide(mail(10, "Re: plan", long_body, thread="t-mine")).kept), len(long_body))

    def test_long_numbers_are_masked_before_anything_is_kept(self):
        self.assertEqual(mask_numbers("card 4111 1111 1111 1234 due"), "card XXXXXXXXXXXX1234 due")
        self.assertEqual(mask_numbers("loan 5502-0098-7712 overdue"), "loan XXXXXXXX7712 overdue")
        self.assertEqual(mask_numbers("call at 10:30, room 42"), "call at 10:30, room 42")
        d = self.t.decide(mail(11, "Statement", "Account 123456789012 is overdue", thread="t-mine"))
        self.assertNotIn("123456789012", d.kept)

    def test_a_silent_summary_says_why(self):
        text, why = summary(self.t.run([mail(12, "50% off", sender="deals@shop.example")]), "5:00 PM")
        self.assertEqual(text, "")
        self.assertIn("silent: 0 of 1", why)

    def test_summary_puts_important_first_and_counts_pending(self):
        t = Triage(owner_threads={"t-mine"}, judge=lambda m: ("MAYBE", "", 1, 1),
                   ledger=Ledger({"judge-model": (1.0, 1.0)}))
        decisions = t.run([mail(13, "Re: offer", thread="t-mine"), mail(14, "Unclear one")])
        text, why = summary(decisions, "8:00 AM")
        self.assertTrue(text.splitlines()[1].startswith("! Re: offer"))
        self.assertIn("1 not judged yet", text)
        self.assertEqual(why, "posted 1")


if __name__ == "__main__":
    unittest.main()
