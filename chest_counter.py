"""Fortnite Chest Counter - version Windows.

Capture l'ecran (comme OBS) et detecte la lueur doree des coffres.
Aucune injection, aucune lecture memoire, aucun fichier du jeu modifie.
"""
import json
import os
import time
import tkinter as tk
from tkinter import messagebox

import cv2
import mss
import numpy as np

SAVE_FILE = os.path.join(os.path.expanduser('~'), 'fortnite_chest_counter.json')
ANALYSIS_W = 480
CONFIRM_FRAMES = 3
TRACK_TIMEOUT = 1.5
MATCH_DIST = 60
RECOUNT_COOLDOWN = 20.0
GLOBAL_COOLDOWN = 0.7

BG, PANEL = '#0b0d1a', '#141830'
BLUE, VIOLET, GOLD, MUTED = '#1fa2ff', '#8a2be2', '#ffcc33', '#8b93b8'


def load_save():
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'record': 0, 'games': []}


def write_save(data):
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class App:
    def __init__(self, root):
        self.root = root
        root.title('Fortnite Chest Counter')
        root.configure(bg=BG)
        root.geometry('560x720')
        root.attributes('-topmost', True)

        self.save = load_save()
        self.running = False
        self.paused = False
        self.count = 0
        self.opened = 0
        self.elapsed_before = 0.0
        self.t_start = None
        self.tracks = []
        self.next_id = 1
        self.recent = []
        self.last_detect = 0.0
        self.sct = mss.mss()
        self.sens = tk.IntVar(value=5)
        self.min_size = tk.IntVar(value=25)
        self.auto = tk.BooleanVar(value=True)
        self.show_preview = tk.BooleanVar(value=False)

        tk.Label(root, text='FORTNITE CHEST COUNTER', bg=BG, fg=BLUE,
                 font=('Impact', 22)).pack(pady=(14, 0))
        self.status = tk.Label(root, text='EN ATTENTE', bg=BG, fg=MUTED,
                               font=('Segoe UI', 10, 'bold'))
        self.status.pack()

        self.big = tk.Label(root, text='0', bg=BG, fg='white', font=('Impact', 130))
        self.big.pack()
        tk.Label(root, text='COFFRES DETECTES', bg=BG, fg=MUTED,
                 font=('Segoe UI', 11, 'bold')).pack()

        row = tk.Frame(root, bg=BG)
        row.pack(pady=12)
        self.lbl_open = self.stat(row, 'OUVERTS (estim.)', GOLD)
        self.lbl_cpm = self.stat(row, 'COFFRES / MIN', BLUE)
        self.lbl_time = self.stat(row, 'DUREE', '#c77dff')

        btns = tk.Frame(root, bg=BG)
        btns.pack(pady=6)
        self.btn(btns, 'START', '#22a55e', self.start)
        self.btn(btns, 'PAUSE', '#d97706', self.pause)
        self.btn(btns, 'RESET', '#475569', self.reset)
        btns2 = tk.Frame(root, bg=BG)
        btns2.pack(pady=4)
        self.btn(btns2, '+1 COFFRE', VIOLET, self.add_manual)
        self.btn(btns2, '-1 COFFRE', '#4c1d95', self.remove)

        opts = tk.Frame(root, bg=BG)
        opts.pack(pady=8)
        tk.Checkbutton(opts, text='Detection automatique', variable=self.auto, bg=BG, fg='white',
                       selectcolor=PANEL, activebackground=BG).grid(row=0, column=0, columnspan=2)
        tk.Checkbutton(opts, text='Fenetre de debug', variable=self.show_preview, bg=BG, fg='white',
                       selectcolor=PANEL, activebackground=BG).grid(row=0, column=2)
        tk.Label(opts, text='Sensibilite', bg=BG, fg=MUTED).grid(row=1, column=0)
        tk.Scale(opts, from_=1, to=10, orient='horizontal', variable=self.sens, bg=BG, fg='white',
                 highlightthickness=0, troughcolor=PANEL, length=160).grid(row=1, column=1, columnspan=2)
        tk.Label(opts, text='Taille min.', bg=BG, fg=MUTED).grid(row=2, column=0)
        tk.Scale(opts, from_=5, to=120, orient='horizontal', variable=self.min_size, bg=BG, fg='white',
                 highlightthickness=0, troughcolor=PANEL, length=160).grid(row=2, column=1, columnspan=2)

        self.lbl_record = tk.Label(root, text='', bg=BG, fg=GOLD, font=('Segoe UI', 12, 'bold'))
        self.lbl_record.pack(pady=4)
        tk.Label(root, text='Historique', bg=BG, fg=BLUE, font=('Segoe UI', 10, 'bold')).pack()
        self.hist = tk.Listbox(root, bg=PANEL, fg='white', height=7, borderwidth=0,
                               highlightthickness=0, font=('Consolas', 10))
        self.hist.pack(fill='x', padx=20, pady=4)
        tk.Label(root, text='Raccourcis : + ajouter | - retirer | Espace start/pause | R reset',
                 bg=BG, fg=MUTED, font=('Segoe UI', 8)).pack()

        root.bind('<plus>', lambda e: self.add_manual())
        root.bind('<KP_Add>', lambda e: self.add_manual())
        root.bind('<minus>', lambda e: self.remove())
        root.bind('<KP_Subtract>', lambda e: self.remove())
        root.bind('<space>', lambda e: self.pause() if self.running and not self.paused else self.start())
        root.bind('<r>', lambda e: self.reset())
        root.protocol('WM_DELETE_WINDOW', self.on_close)

        self.refresh_record()
        self.tick()
        self.detect_loop()

    def stat(self, parent, title, color):
        f = tk.Frame(parent, bg=PANEL, padx=14, pady=8)
        f.pack(side='left', padx=6)
        v = tk.Label(f, text='0', bg=PANEL, fg=color, font=('Impact', 24))
        v.pack()
        tk.Label(f, text=title, bg=PANEL, fg=MUTED, font=('Segoe UI', 7, 'bold')).pack()
        return v

    def btn(self, parent, text, color, cmd):
        tk.Button(parent, text=text, command=cmd, bg=color, fg='white', relief='flat',
                  font=('Segoe UI', 11, 'bold'), padx=14, pady=6, cursor='hand2',
                  activebackground=color).pack(side='left', padx=5)

    def elapsed(self):
        if self.t_start and not self.paused:
            return self.elapsed_before + time.time() - self.t_start
        return self.elapsed_before

    def set_status(self, text, color):
        self.status.config(text=text, fg=color)

    def start(self):
        if self.running and self.paused:
            self.paused = False
            self.t_start = time.time()
        elif not self.running:
            self.running = True
            self.paused = False
            self.t_start = time.time()
        self.set_status('COMPTAGE EN COURS', '#3ddc84')

    def pause(self):
        if self.running and not self.paused:
            self.elapsed_before = self.elapsed()
            self.paused = True
            self.t_start = None
            self.set_status('EN PAUSE', GOLD)

    def reset(self):
        if self.count > 0:
            if not messagebox.askyesno('Reset', 'Reinitialiser ? La partie sera sauvegardee.'):
                return
            self.save_game()
        self.running = self.paused = False
        self.count = self.opened = 0
        self.elapsed_before = 0.0
        self.t_start = None
        self.tracks.clear()
        self.recent.clear()
        self.hist.delete(0, 'end')
        self.big.config(text='0')
        self.set_status('EN ATTENTE', MUTED)
        self.refresh_record()

    def fmt(self, s):
        s = int(s)
        return f'{s // 60:02d}:{s % 60:02d}'

    def log(self, text):
        self.hist.insert(0, f'#{self.count:<3} {self.fmt(self.elapsed())}  {text}')

    def add_chest(self, text):
        self.count += 1
        self.big.config(text=str(self.count), fg=GOLD)
        self.root.after(350, lambda: self.big.config(fg='white'))
        self.log(text)
        if self.count > self.save['record']:
            self.save['record'] = self.count
            write_save(self.save)
            self.refresh_record()
        try:
            import winsound
            winsound.Beep(1200, 120)
        except Exception:
            pass

    def add_manual(self):
        if not self.running:
            self.start()
        self.add_chest('ajout manuel')

    def remove(self):
        if self.count > 0:
            self.count -= 1
            self.big.config(text=str(self.count))
            self.log('coffre retire')

    def save_game(self):
        mins = self.elapsed() / 60
        self.save['games'].insert(0, {
            'date': time.strftime('%d/%m/%Y %H:%M'), 'count': self.count,
            'duration': self.fmt(self.elapsed()),
            'cpm': round(self.count / mins, 1) if mins > 0 else 0})
        self.save['games'] = self.save['games'][:10]
        write_save(self.save)

    def refresh_record(self):
        last = self.save['games'][0] if self.save['games'] else None
        txt = f"RECORD : {self.save['record']} coffres"
        if last:
            txt += f"   |   derniere partie : {last['count']}"
        self.lbl_record.config(text=txt)

    def tick(self):
        mins = self.elapsed() / 60
        self.lbl_time.config(text=self.fmt(self.elapsed()))
        self.lbl_cpm.config(text=f'{self.count / mins:.1f}' if mins > 0.05 else '0.0')
        self.lbl_open.config(text=str(self.opened))
        self.root.after(500, self.tick)

    def detect_loop(self):
        if self.running and not self.paused and self.auto.get():
            try:
                self.detect()
            except Exception as e:
                self.set_status(f'ERREUR : {e}', '#ff4d6d')
        self.root.after(120, self.detect_loop)

    def detect(self):
        mon = self.sct.monitors[1]
        img = np.array(self.sct.grab(mon))[:, :, :3]
        h0, w0 = img.shape[:2]
        scale = ANALYSIS_W / w0
        small = cv2.resize(img, (ANALYSIS_W, int(h0 * scale)), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        s = self.sens.get()
        lo = np.array([17, 110 - s * 6, 170 - s * 8])
        hi = np.array([31, 255, 255])
        mask = cv2.inRange(hsv, lo, hi)
        h = mask.shape[0]
        mask[:int(h * 0.08), :] = 0
        mask[int(h * 0.88):, :] = 0
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
        blobs = []
        for i in range(1, n):
            x, y, bw, bh, area = stats[i]
            if area >= self.min_size.get() and bw / bh < 3 and bh / bw < 3 and area / (bw * bh) > 0.25:
                blobs.append((cents[i][0], cents[i][1], area, (x, y, bw, bh)))
        self.update_tracks(blobs, time.time())
        if self.show_preview.get():
            for t in self.tracks:
                x, y, bw, bh = t['box']
                col = (0, 220, 0) if t['counted'] else (0, 200, 255)
                cv2.rectangle(small, (x, y), (x + bw, y + bh), col, 2)
            cv2.imshow('Debug detection (Echap pour fermer)', small)
            if cv2.waitKey(1) == 27:
                self.show_preview.set(False)
                cv2.destroyAllWindows()
        elif cv2.getWindowProperty('Debug detection (Echap pour fermer)', cv2.WND_PROP_VISIBLE) >= 0 if False else False:
            pass

    def update_tracks(self, blobs, now):
        used = set()
        for cx, cy, area, box in blobs:
            best, best_d = None, MATCH_DIST
            for t in self.tracks:
                if t['id'] in used:
                    continue
                d = np.hypot(t['x'] - cx, t['y'] - cy)
                if d < best_d:
                    best, best_d = t, d
            if best:
                best['x'] = best['x'] * 0.6 + cx * 0.4
                best['y'] = best['y'] * 0.6 + cy * 0.4
                best['max'] = max(best['max'], area)
                best['frames'] += 1
                best['seen'] = now
                best['box'] = box
                used.add(best['id'])
            else:
                self.tracks.append({'id': self.next_id, 'x': cx, 'y': cy, 'max': area, 'frames': 1,
                                    'counted': False, 'seen': now, 'box': box})
                self.next_id += 1
        for t in self.tracks:
            if not t['counted'] and t['frames'] >= CONFIRM_FRAMES:
                t['counted'] = True
                dup = any(now - r[2] < RECOUNT_COOLDOWN and np.hypot(r[0] - t['x'], r[1] - t['y']) < MATCH_DIST * 1.5
                          for r in self.recent)
                if not dup and now - self.last_detect > GLOBAL_COOLDOWN:
                    self.last_detect = now
                    self.recent.append((t['x'], t['y'], now))
                    self.add_chest('coffre detecte')
        alive = []
        for t in self.tracks:
            if now - t['seen'] > TRACK_TIMEOUT:
                if t['counted'] and t['max'] > self.min_size.get() * 4 and t['frames'] > 8:
                    self.opened += 1
            else:
                alive.append(t)
        self.tracks = alive
        self.recent = [r for r in self.recent if now - r[2] < RECOUNT_COOLDOWN]

    def on_close(self):
        if self.count > 0:
            self.save_game()
        cv2.destroyAllWindows()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
