"""
Typing Speed Tester  (v3)
-------------------------
Concepts used:
  * Strings   -> comparing typed text with target text, slicing, strip(), split(), f-strings
  * Functions -> helper functions for WPM, accuracy, text selection, rating
  * GUI       -> Tkinter: cards, progress bar, custom buttons, themes, text tags, after()

Run:  python typing_speed_tester.py

Shortcuts
  Tab, then Enter  -> start the next test (new text)
  F11              -> toggle full screen
  Esc              -> exit full screen (or restart the same text if not full screen)
  Ctrl+N           -> new text
"""

import math
import random
import time
import tkinter as tk
from tkinter import font as tkfont

# ----------------------------------------------------------------------------
# DATA (strings)
# ----------------------------------------------------------------------------
SENTENCES = [
    "The quick brown fox jumps over the lazy dog near the quiet river bank.",
    "Python is a powerful language that is easy to learn and fun to use.",
    "Practice makes perfect, so keep typing every day to improve your speed.",
    "A journey of a thousand miles begins with a single step forward.",
    "Programming is the art of telling a computer exactly what you want it to do.",
    "Success is not final and failure is not fatal; courage to continue counts.",
    "Clean code always looks like it was written by someone who really cares.",
    "Technology is best when it brings people together and makes life simpler.",
]

TIME_OPTIONS = [30, 60, 90]
BASE_CONTENT_WIDTH = 808

THEMES = {
    "dark": dict(
        bg="#11131c", card="#1b1f2e", input="#141826", border="#2a3045",
        text="#e6e9f5", muted="#8b93b3", dim="#5a6285",
        accent="#7c8cff", accent_hover="#95a2ff", btn_text="#0f1220",
        sec="#262b40", sec_hover="#323959",
        good="#4ade80", bad="#f87171", warn="#fbbf24",
        bad_bg="#4a1d26", cur_bg="#2c3358",
    ),
    "light": dict(
        bg="#f3f5fb", card="#ffffff", input="#f7f8fd", border="#dde1ef",
        text="#1d2238", muted="#6b7390", dim="#a3a9c0",
        accent="#4f5bd5", accent_hover="#6470e8", btn_text="#ffffff",
        sec="#e6e9f6", sec_hover="#d6dbef",
        good="#16a34a", bad="#dc2626", warn="#d97706",
        bad_bg="#fde2e2", cur_bg="#e1e5ff",
    ),
}


# ----------------------------------------------------------------------------
# FUNCTIONS (logic, independent of the GUI)
# ----------------------------------------------------------------------------
def get_random_text(previous=""):
    """Return a random sentence, avoiding an immediate repeat."""
    choice = random.choice(SENTENCES)
    while choice == previous and len(SENTENCES) > 1:
        choice = random.choice(SENTENCES)
    return choice


def count_correct_chars(target, typed):
    """Count how many typed characters match the target at the same position."""
    correct = 0
    for i in range(min(len(target), len(typed))):
        if typed[i] == target[i]:
            correct += 1
    return correct


def calculate_wpm(correct_chars, seconds):
    """Standard WPM: 5 characters = 1 word."""
    if seconds <= 0:
        return 0.0
    words = correct_chars / 5
    return round(words / (seconds / 60), 1)


def calculate_accuracy(target, typed):
    """Accuracy percentage of typed characters."""
    if len(typed) == 0:
        return 0.0
    correct = count_correct_chars(target, typed)
    return round(correct / len(typed) * 100, 1)


def get_rating(wpm):
    """Return a rating string based on WPM."""
    if wpm < 20:
        return "Beginner"
    elif wpm < 40:
        return "Average"
    elif wpm < 60:
        return "Good"
    elif wpm < 80:
        return "Fast"
    return "Master"


def pick_font(root, candidates, fallback):
    """Return the first font family from `candidates` installed on this system."""
    installed = set(tkfont.families(root))
    for name in candidates:
        if name in installed:
            return name
    return fallback


# ----------------------------------------------------------------------------
# CUSTOM WIDGET: flat button with hover effect (looks the same on all OSes)
# ----------------------------------------------------------------------------
class FlatButton(tk.Label):
    def __init__(self, parent, text, command, bg, hover, fg, font, padx=20, pady=9):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font,
                         padx=padx, pady=pady, cursor="hand2")
        self.base_bg, self.hover_bg, self.command = bg, hover, command
        self.bind("<Enter>", lambda e: self.config(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self.base_bg))
        self.bind("<Button-1>", lambda e: self.command())

    def restyle(self, bg, hover, fg):
        self.base_bg, self.hover_bg = bg, hover
        self.config(bg=bg, fg=fg)


# ----------------------------------------------------------------------------
# MAIN APPLICATION
# ----------------------------------------------------------------------------
class TypingSpeedTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Typing Speed Tester")
        self.root.minsize(880, 700)
        self.center_window(900, 740)

        self.ui = pick_font(root, ["Segoe UI", "SF Pro Text", "Helvetica Neue",
                                   "Ubuntu", "DejaVu Sans", "Arial"], "TkDefaultFont")
        self.mono = pick_font(root, ["Consolas", "Menlo", "JetBrains Mono",
                                     "DejaVu Sans Mono", "Courier New"], "TkFixedFont")

        # State
        self.theme_name = "dark"
        self.t = THEMES[self.theme_name]
        self.fullscreen = False
        self.scale = 1.0
        self.content_w = BASE_CONTENT_WIDTH
        self.target_text = ""
        self.start_time = None
        self.time_limit = 60
        self.running = False
        self.finished = False
        self.tab_armed = False      # True after Tab is pressed, waiting for Enter
        self.best_wpm = 0.0
        self.tests_done = 0
        self.timer_job = None
        self.progress = 1.0

        # Global key bindings
        self.root.bind("<Tab>", self.on_tab)
        self.root.bind("<Return>", self.on_enter)
        self.root.bind("<KP_Enter>", self.on_enter)
        self.root.bind("<F11>", lambda e: self.set_fullscreen(not self.fullscreen))
        self.root.bind("<Escape>", self.on_escape)
        self.root.bind("<Control-n>", lambda e: self.reset_test())

        self.build_ui()
        self.reset_test()

    def center_window(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = max(0, (self.root.winfo_screenheight() - h) // 2 - 20)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def f(self, n):
        """Scale a size (font / padding) for the current screen mode."""
        return max(1, int(round(n * self.scale)))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()
        t, f = self.t, self.f
        self.root.configure(bg=t["bg"])

        # Content is centred in the window and has a fixed width,
        # so it looks good both windowed and in full screen.
        outer = tk.Frame(self.root, bg=t["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center", width=self.content_w)

        # ---- Header ----
        header = tk.Frame(outer, bg=t["bg"])
        header.pack(fill="x")

        title_box = tk.Frame(header, bg=t["bg"])
        title_box.pack(side="left")
        title_row = tk.Frame(title_box, bg=t["bg"])
        title_row.pack(anchor="w")
        tk.Label(title_row, text="Typing ", font=(self.ui, f(24), "bold"),
                 bg=t["bg"], fg=t["text"]).pack(side="left")
        tk.Label(title_row, text="Speed Tester", font=(self.ui, f(24), "bold"),
                 bg=t["bg"], fg=t["accent"]).pack(side="left")
        tk.Label(title_box, text="Measure your speed and accuracy",
                 font=(self.ui, f(11)), bg=t["bg"], fg=t["muted"]).pack(anchor="w")

        controls = tk.Frame(header, bg=t["bg"])
        controls.pack(side="right")

        btn_font = (self.ui, f(10), "bold")
        self.time_btns = {}
        for secs in TIME_OPTIONS:
            btn = FlatButton(controls, f"{secs}s", lambda s=secs: self.set_time_limit(s),
                             t["sec"], t["sec_hover"], t["muted"],
                             btn_font, padx=f(12), pady=f(7))
            btn.pack(side="left", padx=(0, 6))
            self.time_btns[secs] = btn
        self.style_time_buttons()

        FlatButton(controls, "Light" if self.theme_name == "dark" else "Dark",
                   self.toggle_theme, t["sec"], t["sec_hover"], t["text"],
                   btn_font, padx=f(12), pady=f(7)).pack(side="left", padx=(8, 0))
        FlatButton(controls, "Exit Full" if self.fullscreen else "Full Screen",
                   lambda: self.set_fullscreen(not self.fullscreen),
                   t["sec"], t["sec_hover"], t["text"],
                   btn_font, padx=f(12), pady=f(7)).pack(side="left", padx=(8, 0))

        # ---- Stat cards ----
        stats = tk.Frame(outer, bg=t["bg"])
        stats.pack(fill="x", pady=(f(22), 0))
        for i in range(4):
            stats.columnconfigure(i, weight=1, uniform="stat")
        self.time_val = self.make_stat(stats, 0, "TIME LEFT", "60s", t["text"])
        self.wpm_val = self.make_stat(stats, 1, "WPM", "0", t["accent"])
        self.acc_val = self.make_stat(stats, 2, "ACCURACY", "0%", t["good"])
        self.best_val = self.make_stat(stats, 3, "BEST WPM", "0", t["warn"])

        # ---- Progress bar (time) ----
        self.bar = tk.Canvas(outer, height=f(8), bg=t["bg"], highlightthickness=0)
        self.bar.pack(fill="x", pady=(f(16), 0))
        self.bar.bind("<Configure>", lambda e: self.draw_progress(self.progress))

        # ---- Text card ----
        text_card = tk.Frame(outer, bg=t["card"], highlightthickness=1,
                             highlightbackground=t["border"])
        text_card.pack(fill="x", pady=(f(18), 0))
        self.text_display = tk.Text(
            text_card, height=3, width=10, wrap="word", font=(self.mono, f(19)),
            bg=t["card"], fg=t["dim"], relief="flat", bd=0,
            padx=f(24), pady=f(22), spacing2=f(8), cursor="arrow",
            highlightthickness=0, state="disabled",
        )
        self.text_display.pack(fill="x")
        self.text_display.tag_config("correct", foreground=t["good"])
        self.text_display.tag_config("wrong", foreground=t["bad"], background=t["bad_bg"])
        self.text_display.tag_config("current", foreground=t["text"], background=t["cur_bg"])

        # ---- Typing entry ----
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            outer, textvariable=self.entry_var, font=(self.mono, f(18)),
            bg=t["input"], fg=t["text"], insertbackground=t["accent"],
            disabledbackground=t["input"], disabledforeground=t["muted"],
            relief="flat", highlightthickness=2,
            highlightbackground=t["border"], highlightcolor=t["accent"],
        )
        self.entry.pack(fill="x", pady=(f(14), 0), ipady=f(12))
        self.entry_var.trace_add("write", self.on_type)
        # Block pasting so the test stays fair
        for seq in ("<<Paste>>", "<Control-v>", "<Shift-Insert>", "<Button-2>"):
            self.entry.bind(seq, lambda e: "break")

        # ---- Status area (hint OR result summary) ----
        self.status_area = tk.Frame(outer, bg=t["bg"], height=f(104))
        self.status_area.pack(fill="x", pady=(f(16), 0))
        self.status_area.pack_propagate(False)

        self.hint_label = tk.Label(
            self.status_area,
            text="Start typing to begin. The timer starts on your first keystroke.",
            font=(self.ui, f(11)), bg=t["bg"], fg=t["muted"])

        self.result_frame = tk.Frame(self.status_area, bg=t["card"], highlightthickness=1,
                                     highlightbackground=t["border"])
        for i in range(4):
            self.result_frame.columnconfigure(i, weight=1, uniform="res")
        self.res_vals = {}
        for i, (key, cap, colour) in enumerate([
            ("wpm", "FINAL WPM", t["accent"]), ("acc", "ACCURACY", t["good"]),
            ("words", "WORDS TYPED", t["text"]), ("level", "LEVEL", t["warn"]),
        ]):
            tk.Label(self.result_frame, text=cap, font=(self.ui, f(9), "bold"),
                     bg=t["card"], fg=t["muted"]).grid(row=0, column=i, pady=(f(14), 0))
            lbl = tk.Label(self.result_frame, text="-", font=(self.ui, f(24), "bold"),
                           bg=t["card"], fg=colour)
            lbl.grid(row=1, column=i, pady=(0, f(12)))
            self.res_vals[key] = lbl

        # ---- Buttons ----
        btns = tk.Frame(outer, bg=t["bg"])
        btns.pack(pady=(f(14), 0))
        FlatButton(btns, "Restart", lambda: self.reset_test(new_text=False),
                   t["sec"], t["sec_hover"], t["text"],
                   (self.ui, f(11), "bold"), padx=f(26), pady=f(10)).pack(side="left", padx=6)
        FlatButton(btns, "Next Test", self.reset_test,
                   t["accent"], t["accent_hover"], t["btn_text"],
                   (self.ui, f(11), "bold"), padx=f(26), pady=f(10)).pack(side="left", padx=6)

        # ---- Footer (shortcut hints, changes with state) ----
        self.footer = tk.Label(outer, text="", font=(self.ui, f(10)),
                               bg=t["bg"], fg=t["dim"])
        self.footer.pack(pady=(f(12), 0))

        self.update_best_label()
        self.update_footer()

    def make_stat(self, parent, col, caption, value, colour):
        t, f = self.t, self.f
        card = tk.Frame(parent, bg=t["card"], highlightthickness=1,
                        highlightbackground=t["border"])
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 10, 0))
        tk.Label(card, text=caption, font=(self.ui, f(9), "bold"),
                 bg=t["card"], fg=t["muted"]).pack(anchor="w", padx=f(18), pady=(f(14), 0))
        lbl = tk.Label(card, text=value, font=(self.ui, f(26), "bold"),
                       bg=t["card"], fg=colour)
        lbl.pack(anchor="w", padx=f(18), pady=(0, f(12)))
        return lbl

    # ------------------------------------------------------------------
    # Small UI helpers
    # ------------------------------------------------------------------
    def style_time_buttons(self):
        t = self.t
        for secs, btn in self.time_btns.items():
            if secs == self.time_limit:
                btn.restyle(t["accent"], t["accent_hover"], t["btn_text"])
            else:
                btn.restyle(t["sec"], t["sec_hover"], t["muted"])

    def draw_progress(self, fraction):
        """Draw the time bar; colour changes as time runs out."""
        self.progress = fraction
        self.bar.delete("all")
        t = self.t
        h = self.f(8)
        width = self.bar.winfo_width()
        if width <= 1:
            width = self.content_w
        self.bar.create_rectangle(0, 0, width, h, fill=t["border"], outline="")
        if fraction > 0:
            colour = t["accent"] if fraction > 0.5 else t["warn"] if fraction > 0.2 else t["bad"]
            self.bar.create_rectangle(0, 0, int(width * fraction), h, fill=colour, outline="")

    def update_best_label(self):
        self.best_val.config(text=f"{self.best_wpm:g}")

    def update_footer(self):
        """Footer text depends on the state: normal, finished, or Tab pressed."""
        t = self.t
        if self.tab_armed:
            self.footer.config(text="Tab pressed  -  now press Enter to start the next test",
                               fg=t["accent"], font=(self.ui, self.f(10), "bold"))
        elif self.finished:
            self.footer.config(text="Test complete  -  press Tab, then Enter for the next test",
                               fg=t["text"], font=(self.ui, self.f(10), "bold"))
        else:
            self.footer.config(
                text="Tab + Enter: next test      Esc: restart      Ctrl+N: new text      F11: full screen",
                fg=t["dim"], font=(self.ui, self.f(10)))

    def toggle_theme(self):
        # Switching theme rebuilds the window, so the current test restarts
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.t = THEMES[self.theme_name]
        self.build_ui()
        self.reset_test(new_text=False)

    def set_time_limit(self, secs):
        self.time_limit = secs
        self.style_time_buttons()
        self.reset_test(new_text=False)

    # ------------------------------------------------------------------
    # Full screen
    # ------------------------------------------------------------------
    def set_fullscreen(self, on):
        """Turn full screen on/off and re-scale the interface to fit."""
        self.fullscreen = on
        self.root.attributes("-fullscreen", on)
        if on:
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.scale = min(1.5, max(1.0, sh / 800))
            self.content_w = min(sw - 160, int(BASE_CONTENT_WIDTH * self.scale * 1.1))
        else:
            self.scale = 1.0
            self.content_w = BASE_CONTENT_WIDTH
        self.build_ui()
        self.reset_test(new_text=False)   # the test restarts after a mode change

    def on_escape(self, event=None):
        if self.fullscreen:
            self.set_fullscreen(False)
        else:
            self.reset_test(new_text=False)

    # ------------------------------------------------------------------
    # Tab -> Enter : next test
    # ------------------------------------------------------------------
    def on_tab(self, event=None):
        """Tab 'arms' the shortcut; the next Enter starts a new test."""
        self.tab_armed = True
        self.update_footer()
        return "break"       # stop Tk from moving focus away from the typing box

    def on_enter(self, event=None):
        if self.tab_armed:
            self.reset_test()        # new text
        return "break"

    # ------------------------------------------------------------------
    # Test control
    # ------------------------------------------------------------------
    def cancel_timer(self):
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def reset_test(self, new_text=True):
        self.cancel_timer()
        self.running = False
        self.finished = False
        self.tab_armed = False
        self.start_time = None

        if new_text or not self.target_text:
            self.target_text = get_random_text(self.target_text)

        self.text_display.config(state="normal")
        self.text_display.delete("1.0", "end")
        self.text_display.insert("1.0", self.target_text)
        self.text_display.config(state="disabled")

        self.entry.config(state="normal")
        self.entry_var.set("")
        self.entry.focus_set()

        self.time_val.config(text=f"{self.time_limit}s", fg=self.t["text"])
        self.wpm_val.config(text="0")
        self.acc_val.config(text="0%")
        self.draw_progress(1.0)
        self.highlight("")

        self.result_frame.pack_forget()
        self.hint_label.pack(expand=True)
        self.update_footer()

    def start_test(self):
        self.running = True
        self.start_time = time.time()
        self.update_timer()

    def update_timer(self):
        """Runs every 50 ms while the test is active."""
        if not self.running:
            return
        elapsed = time.time() - self.start_time
        remaining = max(0.0, self.time_limit - elapsed)
        fraction = remaining / self.time_limit

        self.time_val.config(text=f"{math.ceil(remaining)}s",
                             fg=self.t["bad"] if fraction <= 0.2 else self.t["text"])
        self.draw_progress(fraction)

        # Live WPM (ignore the first 2 seconds, it would be misleading)
        if elapsed >= 2:
            correct = count_correct_chars(self.target_text, self.entry_var.get())
            self.wpm_val.config(text=f"{calculate_wpm(correct, elapsed):.0f}")

        if remaining <= 0:
            self.finish_test()
        else:
            self.timer_job = self.root.after(50, self.update_timer)

    def finish_test(self):
        if self.finished:
            return
        self.finished = True
        self.running = False
        self.cancel_timer()

        typed = self.entry_var.get()
        elapsed = max(0.5, min(time.time() - self.start_time, self.time_limit))
        correct = count_correct_chars(self.target_text, typed)
        wpm = calculate_wpm(correct, elapsed)
        accuracy = calculate_accuracy(self.target_text, typed)
        words_typed = len(typed.strip().split())

        self.entry.config(state="disabled")
        self.wpm_val.config(text=f"{wpm:g}")
        self.acc_val.config(text=f"{accuracy:g}%")
        self.time_val.config(text=f"{max(0, self.time_limit - elapsed):.0f}s",
                             fg=self.t["text"])

        self.tests_done += 1
        if wpm > self.best_wpm:
            self.best_wpm = wpm
            self.update_best_label()

        self.res_vals["wpm"].config(text=f"{wpm:g}")
        self.res_vals["acc"].config(text=f"{accuracy:g}%")
        self.res_vals["words"].config(text=str(words_typed))
        self.res_vals["level"].config(text=get_rating(wpm))

        self.hint_label.pack_forget()
        self.result_frame.pack(fill="both", expand=True)
        self.update_footer()

    # ------------------------------------------------------------------
    # Typing events
    # ------------------------------------------------------------------
    def on_type(self, *args):
        if self.finished:
            return
        typed = self.entry_var.get()

        # Typing cancels a pending Tab -> Enter
        if self.tab_armed:
            self.tab_armed = False
            self.update_footer()

        if not self.running and typed:
            self.start_test()

        self.highlight(typed)

        if typed:
            self.acc_val.config(
                text=f"{calculate_accuracy(self.target_text, typed):g}%")

        # Finish early when the whole sentence has been typed
        if len(typed) >= len(self.target_text):
            self.finish_test()

    def highlight(self, typed):
        """Colour each target character: green = correct, red = wrong, box = next."""
        self.text_display.config(state="normal")
        for tag in ("correct", "wrong", "current"):
            self.text_display.tag_remove(tag, "1.0", "end")

        for i, ch in enumerate(typed[:len(self.target_text)]):
            start, end = f"1.0+{i}c", f"1.0+{i + 1}c"
            tag = "correct" if ch == self.target_text[i] else "wrong"
            self.text_display.tag_add(tag, start, end)

        if len(typed) < len(self.target_text):
            self.text_display.tag_add("current", f"1.0+{len(typed)}c",
                                      f"1.0+{len(typed) + 1}c")
        self.text_display.config(state="disabled")


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    root = tk.Tk()
    TypingSpeedTester(root)
    root.mainloop()


if __name__ == "__main__":
    main()