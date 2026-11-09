#!/usr/bin/env python3
"""Build the README diagrams as SVG, one light and one dark version each. Standard library only.

    python3 docs/diagrams/build.py

Every box and line is placed by hand on purpose: the diagrams explain a design, so they are written
like code and reviewed like code. Run this after changing any label, then commit the SVGs.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

THEMES = {
    "light": dict(bg="#ffffff", panel="#f6f8fa", card="#ffffff", line="#d0d7de", text="#1f2328", muted="#57606a",
                  faint="#8c959f", ops="#0f766e", ops_bg="#e6f6f4", asst="#7c3aed", asst_bg="#f3edff",
                  hand="#b45309", hand_bg="#fff4e0", core="#0969da", core_bg="#e7f0fb", ok="#1a7f37",
                  ok_bg="#dafbe1", hold="#9a6700", hold_bg="#fff8c5", bad="#cf222e", bad_bg="#ffebe9"),
    "dark": dict(bg="#0d1117", panel="#161b22", card="#0d1117", line="#30363d", text="#e6edf3", muted="#9198a1",
                 faint="#6e7681", ops="#2dd4bf", ops_bg="#0b2b28", asst="#b392f0", asst_bg="#221a38",
                 hand="#f0b44c", hand_bg="#2e2210", core="#58a6ff", core_bg="#0d2340", ok="#3fb950",
                 ok_bg="#0f2a17", hold="#d29922", hold_bg="#2b230c", bad="#f85149", bad_bg="#2d1214"),
}


class Svg:
    def __init__(self, w, h, t, title):
        self.w, self.h, self.t, self.parts = w, h, t, []
        self.title = title

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill, stroke=None, r=12, dash=False, sw=1.2):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        da = ' stroke-dasharray="6 5"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{st}{da}/>')

    def text(self, x, y, s, size=14, color=None, weight=400, anchor="start", mono=False, italic=False):
        fam = MONO if mono else FONT
        it = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
                 f'fill="{color or self.t["text"]}" text-anchor="{anchor}"{it}>{escape(s)}</text>')

    def lines(self, x, y, rows, size=13.5, color=None, gap=1.42, **kw):
        for i, s in enumerate(rows):
            self.text(x, y + i * size * gap, s, size, color or self.t["muted"], **kw)

    def arrow(self, pts, color, dash=False, both=False, width=2):
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        self.n = getattr(self, "n", 0) + 1
        mid = f"arrow{self.n}"
        da = ' stroke-dasharray="7 6"' if dash else ""
        start = f' marker-start="url(#{mid}s)"' if both else ""
        self.add(f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                 f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{color}"/></marker>'
                 f'<marker id="{mid}s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                 f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{color}"/></marker></defs>')
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"'
                 f'{da} marker-end="url(#{mid})"{start}/>')

    def pill(self, x, y, s, fg, bg, size=12, pad=9, weight=600):
        w = len(s) * size * 0.6 + 2 * pad
        self.rect(x, y, w, size + 10, bg, r=(size + 10) / 2)
        self.text(x + w / 2, y + size + 2.5, s, size, fg, weight, "middle")
        return w

    def dot(self, x, y, color, r=5):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def card(self, x, y, w, h, title, rows, accent, accent_bg=None, tag=None, dash=False, size=13.5):
        t = self.t
        self.rect(x, y, w, h, t["card"], t["line"], dash=dash)
        self.add(f'<rect x="{x}" y="{y + 10}" width="4" height="{h - 20}" rx="2" fill="{accent}"/>')
        self.text(x + 18, y + 27, title, 16, t["text"], 700)
        yy = y + 50
        if tag:
            self.pill(x + 18, y + 38, tag, accent, accent_bg or t["panel"], 11.5)
            yy = y + 74
        self.lines(x + 18, yy, rows, size)

    def save(self, name):
        body = "\n".join(self.parts)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">\n'
               f'<title>{escape(self.title)}</title>\n'
               f'<rect width="{self.w}" height="{self.h}" rx="16" fill="{self.t["bg"]}" stroke="{self.t["line"]}"/>\n'
               f'{body}\n</svg>\n')
        (OUT / name).write_text(svg, encoding="utf-8")


def connector(s, x1, x2, y, color):
    s.add(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="2.2"/>')
    s.dot(x1, y, color, 4)
    s.dot(x2, y, color, 4)


def architecture(theme):
    t = THEMES[theme]
    s = Svg(1200, 1000, t, "Architecture of The Agency: three WhatsApp agents and a Handler on one desktop")
    s.text(40, 54, "How The Agency fits together", 26, t["text"], 700)
    s.text(40, 82, "One always-on Windows desktop. The agents live in WSL2 Ubuntu; Windows-only tools are reached through interop.",
           15, t["muted"])
    for x, label in ((40, "PEOPLE, ON WHATSAPP"), (296, "GATEWAY"), (976, "TOOLS AND BRIDGES")):
        s.text(x, 124, label, 12, t["faint"], 700)

    # people
    s.card(30, 140, 230, 96, "Team group", ["a small business team", "talks to the Operations agent"], t["ops"])
    s.card(30, 252, 230, 96, "Private chat", ["two people", "talk to the Assistant"], t["asst"])
    s.card(30, 364, 230, 96, "Handler group", ["the owner, from his phone,", "commands everything"], t["hand"])
    s.card(30, 476, 230, 132, "Owner's phone", ["texts, missed calls and", "voicemail reach the Handler", "through a token that can", "only add alerts"],
           t["hand"], dash=True)

    # gateway
    s.card(286, 140, 200, 320, "OpenClaw gateway", ["systemd user service", "", "each group is bound to", "exactly one agent", "",
                                                    "turns run on the Claude", "CLI: Sonnet and Haiku", "",
                                                    "in large groups only", "mentions reach the model"], t["core"])
    s.card(286, 476, 200, 132, "Outbox sender", ["walled agents never post", "themselves: a trusted", "process checks each", "message, then posts it"],
           t["core"])

    # agents panel
    s.rect(506, 108, 448, 516, t["panel"], t["line"], r=16)
    s.text(526, 130, "AGENTS  ·  WSL2 UBUNTU", 12, t["faint"], 700)
    s.card(522, 146, 232, 126, "Operations agent", ["report runs 10:30 and 15:00", "timesheets · scorecard"], t["ops"],
           t["ops_bg"], "walled Linux user", size=13)
    s.card(522, 286, 232, 126, "Assistant", ["reminders · research · links", "checked pictures · voice"], t["asst"],
           t["asst_bg"], "walled Linux user", size=13)
    s.card(522, 426, 232, 182, "Handler", ["mail triage every 2 minutes", "health every 10 minutes", "summaries · usage · alerts",
                                           "acts only by writing visible", "command lines in its reply"], t["hand"], t["hand_bg"], "read-only", size=13)
    # dispatcher
    s.rect(772, 286, 170, 322, t["card"], t["hand"], sw=1.8)
    s.text(788, 313, "Dispatcher", 16, t["text"], 700)
    s.lines(788, 338, ["Plain code, no model.", "Runs a command line", "only if:"], 12.5)
    for i, rule in enumerate(("it came from the", "owner's number", "he asked for it", "it crosses no wall")):
        yy = 398 + i * 22 + (8 if i > 1 else 0) + (8 if i > 2 else 0)
        if i != 1:
            s.dot(792, yy - 4, t["hand"], 3)
        s.text(802, yy, rule, 12.5, t["text"], 600)
    s.lines(788, 512, ["A line copied from mail", "or a page it read is", "refused outright."], 12, t["muted"])
    s.pill(788, 568, "every decision logged", t["hand"], t["hand_bg"], 11)
    s.text(788, 164, "RELAYS", 11.5, t["hand"], 700)
    s.lines(788, 184, ["only when the owner", "explicitly asks"], 12, t["hand"])

    # connections
    connector(s, 260, 286, 188, t["ops"])
    connector(s, 260, 300, 300, t["asst"]) if False else connector(s, 260, 286, 300, t["asst"])
    connector(s, 260, 286, 412, t["hand"])
    s.arrow([(486, 209), (520, 209)], t["ops"])
    s.arrow([(486, 349), (520, 349)], t["asst"])
    s.arrow([(486, 440), (500, 440), (500, 517), (520, 517)], t["hand"])
    s.arrow([(754, 517), (770, 517)], t["hand"])
    s.arrow([(772, 330), (763, 330), (763, 230), (756, 230)], t["hand"])
    s.arrow([(772, 370), (756, 370)], t["hand"])
    s.arrow([(522, 596), (488, 596)], t["core"])

    # tools
    tx, tw = 970, 200
    tools = [
        ("Outlook via COM", ["Windows · timesheets filed,", "reminders saved as drafts"], ["ops"]),
        ("Edge via DevTools", ["Windows · browser tasks and", "a signed-out reader"], ["ops", "asst", "hand"]),
        ("Apps Script bridges", ["Handler: read, draft, calendar,", "no send function at all;", "Operations: sends its report"], ["ops", "hand"]),
        ("Local speech", ["SenseVoice, Whisper fallback;", "no audio leaves the desk"], ["asst"]),
    ]
    y = 140
    for name, rows, users in tools:
        h = 60 + 18 * len(rows)
        s.rect(tx, y, tw, h, t["card"], t["line"])
        s.text(tx + 16, y + 26, name, 15, t["text"], 700)
        s.lines(tx + 16, y + 48, rows, 12.5)
        for i, u in enumerate(users):
            s.dot(tx + tw - 16 - i * 14, y + h - 14, t[u], 4.5)
        y += h + 10
    for i, (u, lab) in enumerate((("ops", "Operations"), ("asst", "Assistant"), ("hand", "Handler"))):
        s.dot(tx + 6 + (0, 80, 154)[i], y + 12, t[u], 4.5)
        s.text(tx + 14 + (0, 80, 154)[i], y + 16.5, lab, 11.5, t["muted"])

    # shared state band
    s.rect(30, 640, 1140, 140, t["panel"], t["line"], r=16)
    s.text(50, 668, "SHARED PLAIN-TEXT STATE", 12, t["faint"], 700)
    s.text(232, 668, "agents read these files instead of the live mailbox or chat history: cheaper, faster, the same answer every time",
           13, t["muted"])
    chips = [("Chat logs", ["every message of every group,", "both ways, with media, in seconds"]),
             ("Mail log", ["one verdict per email; codes never", "kept; long numbers masked"]),
             ("Rolling memory", ["a 7-day block in each agent's", "instructions, plus a weekly journal"]),
             ("Snapshots", ["taken every night, kept for", "recovery"])]
    cx = 50
    for name, rows in chips:
        s.rect(cx, 684, 268, 80, t["card"], t["line"], r=10)
        s.text(cx + 14, 708, name, 14.5, t["text"], 700)
        s.lines(cx + 14, 730, rows, 12)
        cx += 278

    # delivery band
    s.rect(30, 796, 1140, 180, t["panel"], t["line"], r=16)
    s.text(50, 824, "DELIVERY AND OPERATIONS", 12, t["faint"], 700)
    steps = [("GitHub", ["one repository", "for all agents"]),
             ("Deploy bot", ["pulls every 5 minutes", "into its own clone"]),
             ("Checks", ["secret scan, compile,", "full offline suite"]),
             ("Drift guard", ["refuses to overwrite", "a live edit"]),
             ("Live agents", ["never during the", "10:30 and 15:00 runs"])]
    sx = 50
    for i, (name, rows) in enumerate(steps):
        s.rect(sx, 840, 150, 116, t["card"], t["core"] if i in (1, 2, 3) else t["line"], r=10)
        s.text(sx + 14, 866, name, 14.5, t["text"], 700)
        s.lines(sx + 14, 890, rows, 12)
        if i < len(steps) - 1:
            s.arrow([(sx + 150, 898), (sx + 166, 898)], t["core"])
        sx += 168
    s.rect(898, 840, 252, 116, t["card"], t["line"], r=10)
    s.text(912, 866, "On a schedule", 14.5, t["text"], 700)
    s.lines(912, 890, ["health checks every 10 minutes", "mail watch every 2 minutes by day", "behaviour evals each night, only", "for agents whose instructions changed"], 12)
    s.save(f"architecture-{theme}.svg")


def gate_card(s, x, y, w, h, num, title, rows, t):
    s.rect(x, y, w, h, t["card"], t["line"])
    s.add(f'<circle cx="{x + 28}" cy="{y + 28}" r="14" fill="{t["hand_bg"]}" stroke="{t["hand"]}" stroke-width="1.4"/>')
    s.text(x + 28, y + 33, str(num), 14, t["hand"], 700, "middle")
    s.text(x + 52, y + 33, title, 16, t["text"], 700)
    s.lines(x + 18, y + 64, rows, 13.5, t["text"])


def command_path(theme):
    t = THEMES[theme]
    s = Svg(1200, 800, t, "How the Handler's dispatcher decides whether a command line runs")
    s.text(40, 54, "What happens when the owner gives an order", 26, t["text"], 700)
    s.text(40, 82, "The Handler's model only proposes. A dispatcher in plain code decides, in this order, and logs every decision.",
           15, t["muted"])

    # row 1: who proposes
    s.card(30, 112, 330, 112, "The owner, on his phone", ["\u201ctell ops to re-run the weekly report\u201d", "in the Handler group"], t["hand"])
    s.card(410, 112, 360, 112, "Handler (the model, read-only)", ["answers, and writes the action as a", "visible line in its reply:"], t["hand"])
    s.text(428, 210, "relay: ops re-run the weekly report", 13, t["hand"], 600, mono=True)
    s.rect(820, 112, 350, 112, t["hand_bg"], t["hand"], sw=1.6)
    s.text(840, 142, "Dispatcher (plain code, no model)", 16, t["text"], 700)
    s.lines(840, 168, ["reads every command line in the reply", "and puts it through four checks"], 13.5, t["text"])
    s.arrow([(360, 168), (406, 168)], t["hand"])
    s.arrow([(770, 168), (816, 168)], t["hand"])
    s.arrow([(995, 224), (995, 244), (145, 244), (145, 262)], t["hand"])

    # row 2: gates
    gates = [("Sender", ["Did the message come from", "the owner's own number?"]),
             ("Source", ["Was the line copied from an", "email or page it just read?"]),
             ("Allowed", ["Is it an allowed command, and", "does a relay stay inside the", "other agent's wall?"]),
             ("Asked", ["For anything with an effect:", "did the owner's own words ask", "for this exact action, once?"])]
    gx = [30, 316, 602, 888]
    for i, (title, rows) in enumerate(gates):
        gate_card(s, gx[i], 264, 266, 138, i + 1, title, rows, t)
        if i < 3:
            s.arrow([(gx[i] + 266, 333), (gx[i + 1] - 4, 333)], t["ok"])
            s.text(gx[i] + 286 - 10, 324, "pass", 11, t["ok"], 700, "middle") if False else None

    # row 3: what stops a line
    outs = [("no", "REFUSED", "bad", ["a stranger in the group:", "\u201ctell ops to book everything\u201d"]),
            ("yes", "REFUSED", "bad", ["a command line hidden in", "an email it was asked to read"]),
            ("no", "REFUSED", "bad", ["\u201ctell the assistant the client", "invoices are late\u201d: work topic,", "private chat"]),
            ("no", "HELD", "hold", ["\u201cthe afternoon report looked", "thin\u201d: a relay nobody asked for"])]
    for i, (ans, verdict, kind, rows) in enumerate(outs):
        x = gx[i]
        s.arrow([(x + 133, 402), (x + 133, 438)], t[kind])
        s.text(x + 143, 425, ans, 12, t[kind], 700)
        s.rect(x, 442, 266, 118, t[kind + "_bg"], t[kind], sw=1.3)
        s.text(x + 18, 470, verdict, 15, t[kind], 800)
        s.lines(x + 18, 496, rows, 13, t["text"])

    # row 4: ran
    s.arrow([(1154, 333), (1172, 333), (1172, 633), (1154, 633)], t["ok"])
    s.rect(30, 592, 1120, 82, t["ok_bg"], t["ok"], sw=1.4)
    s.text(50, 622, "RAN", 15, t["ok"], 800)
    s.text(96, 622, "Passed all four: the command runs, and code posts the result straight to the group. The model never retells it.",
           14, t["text"], 600)
    s.text(96, 650, "\u201chow is everything?\u201d  \u2192  status: all  \u2192  gateway ok, 3 agents up, last report run ok, 0 alerts",
           13, t["muted"])

    # row 5: audit
    s.rect(30, 690, 1120, 86, t["panel"], t["line"])
    s.text(50, 720, "Audit log", 15, t["text"], 700)
    s.lines(50, 744, ["Every decision, with its reason, is written down with sender numbers masked. Because the line sits in the reply, the owner",
                      "sees exactly what ran. These are keyword rules: they stop accidents and casual injection, and anything irreversible still asks to confirm."], 13)
    s.save(f"command-path-{theme}.svg")


def inbox(theme):
    t = THEMES[theme]
    s = Svg(1200, 700, t, "How the Handler triages mail: rules first, a costed model judge for the rest, a log that keeps only what it should")
    s.text(40, 54, "How the Handler reads the mail without reading it all", 26, t["text"], 700)
    s.text(40, 82, "Every 2 minutes by day, hourly overnight. Plain rules decide first, for free; a model judges only what is left.",
           15, t["muted"])

    s.card(30, 120, 190, 100, "New email", ["picked up by the", "mail watch"], t["core"])
    # rules panel
    s.rect(260, 112, 520, 300, t["panel"], t["line"], r=16)
    s.text(280, 140, "PLAIN RULES  ·  NO MODEL, NO COST", 12, t["faint"], 700)
    rules = [("Looks like a one-time code", "CODE", "bad", "its text is never stored"),
             ("A reply in a thread the owner wrote in", "IMPORTANT", "ok", "always worth a look"),
             ("A known noise sender", "NOISE", "core", "kept short, never posted")]
    for i, (cond, verdict, kind, note) in enumerate(rules):
        y = 156 + i * 78
        s.rect(276, y, 488, 64, t["card"], t["line"], r=10)
        s.text(294, y + 26, cond, 14.5, t["text"], 600)
        s.text(294, y + 48, note, 12.5, t["muted"])
        s.pill(756 - len(verdict) * 7.2 - 18, y + 20, verdict, t[kind], t[kind + "_bg"], 12)
    s.arrow([(220, 170), (256, 170)], t["core"])

    # judge
    s.text(532, 437, "none matched", 12, t["muted"], 600)
    s.arrow([(520, 412), (520, 452)], t["core"])
    s.card(260, 456, 520, 120, "Model judge", ["one costed call per email, written to a cost ledger;", "it answers with one of:"], t["hand"])
    px = 278
    for v, kind in (("IMPORTANT", "ok"), ("FYI", "core"), ("NOISE", "core")):
        px += s.pill(px, 536, v, t[kind], t[kind + "_bg"], 12) + 8
    s.rect(260, 596, 520, 84, t["hold_bg"], t["hold"], sw=1.3)
    s.text(280, 624, "No clear answer, or the call failed  \u2192  PENDING", 14.5, t["hold"], 700)
    s.lines(280, 650, ["never turned into a guess: it is judged again on the next run"], 13, t["text"])
    s.arrow([(520, 576), (520, 594)], t["hold"])

    # log
    s.rect(820, 112, 350, 410, t["card"], t["core"], sw=1.5)
    s.text(840, 142, "Mail log (plain text)", 16, t["text"], 700)
    s.text(840, 166, "what every agent reads instead of the mailbox", 12.5, t["muted"])
    keep = [("IMPORTANT, FYI", "the whole text, up to 20,000", "characters"),
            ("NOISE", "the first 500 characters, enough", "to catch a misjudged email later"),
            ("CODE", "nothing at all", "")]
    for i, (k, a, b) in enumerate(keep):
        y = 196 + i * 78
        s.text(840, y, k, 13.5, t["text"], 700)
        s.text(840, y + 22, a, 13, t["muted"])
        if b:
            s.text(840, y + 41, b, 13, t["muted"])
    s.rect(836, 420, 318, 86, t["panel"], t["line"], r=10)
    s.lines(852, 444, ["Card, account and loan numbers are", "masked to their last four digits", "before anything is written."], 13, t["text"])
    s.arrow([(780, 262), (816, 262)], t["core"])
    s.arrow([(780, 516), (800, 516), (800, 400), (816, 400)], t["core"])

    # summaries
    s.rect(820, 540, 350, 140, t["ok_bg"], t["ok"], sw=1.3)
    s.text(840, 568, "Summaries at fixed times", 16, t["text"], 700)
    s.lines(840, 594, ["only what is new since the last one;", "a quiet slot posts nothing and logs", "why, because a silent job and a broken", "one look the same from outside"], 13, t["text"])
    s.arrow([(995, 522), (995, 538)], t["ok"])
    s.save(f"inbox-triage-{theme}.svg")


if __name__ == "__main__":
    for th in THEMES:
        architecture(th)
        command_path(th)
        inbox(th)
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))
