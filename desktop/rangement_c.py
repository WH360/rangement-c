# -*- coding: utf-8 -*-
"""
Rangement C - organiseur de dossiers pour Windows
- Range les fichiers d'un dossier par TYPE ou par DATE
- Aperçu avant de déplacer, rien n'est supprimé
- Bouton "Annuler" pour tout remettre en place
- Refuse les dossiers système (C:\\, Windows, Program Files, AppData...)
"""
import os
import sys
import json
import shutil
import datetime
from pathlib import Path

APP_DIR = Path.home() / ".rangement_c"
JOURNAL_DIR = APP_DIR / "journaux"

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff",
               ".heic", ".svg", ".ico", ".raw", ".cr2", ".nef"},
    "PDF": {".pdf"},
    "Documents Word": {".doc", ".docx", ".odt", ".rtf"},
    "Tableurs": {".xls", ".xlsx", ".xlsm", ".csv", ".ods", ".tsv"},
    "Présentations": {".ppt", ".pptx", ".odp", ".key"},
    "Textes": {".txt", ".md", ".log"},
    "Vidéos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Musique": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Installateurs": {".exe", ".msi", ".msix", ".appx", ".iso", ".apk"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".r", ".ipynb",
             ".java", ".c", ".cpp", ".h", ".sh", ".bat", ".ps1", ".sql", ".yml", ".yaml"},
    "Science": {".fcs", ".ab1", ".fasta", ".fa", ".gb", ".pzfx", ".sav", ".spv",
                ".czi", ".lif", ".nd2", ".mzml", ".raw_ms"},
    "Polices": {".ttf", ".otf", ".woff", ".woff2"},
}
EXT_TO_CAT = {ext: cat for cat, exts in CATEGORIES.items() for ext in exts}
OTHER = "Autres"

# Fichiers jamais déplacés
SKIP_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
SKIP_EXTS = {".lnk", ".url", ".crdownload", ".part", ".tmp", ".partial", ".download"}

MOIS = ["01-Janvier", "02-Février", "03-Mars", "04-Avril", "05-Mai", "06-Juin",
        "07-Juillet", "08-Août", "09-Septembre", "10-Octobre", "11-Novembre", "12-Décembre"]


# ---------------------------------------------------------------- sécurité
def protection_reason(folder):
    """Renvoie une raison si le dossier est interdit, sinon None."""
    p = Path(folder).resolve()
    s = str(p).lower().replace("/", "\\")
    if not p.is_dir():
        return "Ce dossier n'existe pas."
    if p.parent == p:  # racine d'un disque, ex. C:\
        return "La racine du disque (C:\\) ne peut pas être rangée : Windows ne démarrerait plus."
    forbidden = ["\\windows", "\\program files", "\\programdata", "\\appdata",
                 "\\$recycle.bin", "\\system volume information", "\\recovery",
                 "\\perflogs", "\\onedrivetemp"]
    for f in forbidden:
        if f in s:
            return "Dossier système/logiciel : le ranger casserait des programmes."
    if p == Path.home().resolve():
        return ("Ton dossier utilisateur racine contient des fichiers système. "
                "Choisis plutôt Téléchargements, Bureau, Documents...")
    if APP_DIR.resolve() in [p, *p.parents]:
        return "Dossier interne de l'application."
    return None


def _is_hidden(path):
    if path.name.startswith("."):
        return True
    try:
        attrs = os.stat(path).st_file_attributes  # Windows uniquement
        return bool(attrs & 0x2 or attrs & 0x4)   # caché ou système
    except AttributeError:
        return False
    except OSError:
        return True


# ---------------------------------------------------------------- logique
def category_of(path):
    return EXT_TO_CAT.get(path.suffix.lower(), OTHER)


def target_subfolder(path, mode):
    if mode == "date":
        d = datetime.datetime.fromtimestamp(path.stat().st_mtime)
        return Path(str(d.year)) / MOIS[d.month - 1]
    if mode == "type_date":
        d = datetime.datetime.fromtimestamp(path.stat().st_mtime)
        return Path(category_of(path)) / str(d.year)
    return Path(category_of(path))


def _unique(dst, taken):
    if not dst.exists() and str(dst).lower() not in taken:
        return dst
    stem, suf, i = dst.stem, dst.suffix, 2
    while True:
        cand = dst.with_name(f"{stem} ({i}){suf}")
        if not cand.exists() and str(cand).lower() not in taken:
            return cand
        i += 1


def plan_moves(folder, mode="type"):
    """Liste des déplacements prévus [(src, dst, taille)] — ne touche à rien."""
    reason = protection_reason(folder)
    if reason:
        raise PermissionError(reason)
    folder = Path(folder).resolve()
    plan, taken = [], set()
    for entry in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
        try:
            if not entry.is_file() or entry.is_symlink():
                continue
            if entry.name.lower() in SKIP_NAMES or entry.suffix.lower() in SKIP_EXTS:
                continue
            if _is_hidden(entry):
                continue
            dst = _unique(folder / target_subfolder(entry, mode) / entry.name, taken)
            taken.add(str(dst).lower())
            plan.append((entry, dst, entry.stat().st_size))
        except OSError:
            continue
    return plan


def apply_moves(plan, folder):
    """Exécute le plan, écrit un journal pour pouvoir annuler."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    done, errors = [], []
    for src, dst, _ in plan:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst = _unique(dst, set())
            shutil.move(str(src), str(dst))
            done.append({"src": str(src), "dst": str(dst)})
        except Exception as e:  # fichier ouvert, droits...
            errors.append(f"{src.name} : {e}")
    journal = None
    if done:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        journal = JOURNAL_DIR / f"rangement_{stamp}.json"
        journal.write_text(json.dumps({"dossier": str(folder), "date": stamp,
                                       "deplacements": done}, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    return done, errors, journal


def list_journals():
    if not JOURNAL_DIR.exists():
        return []
    return sorted(JOURNAL_DIR.glob("rangement_*.json"), reverse=True)


def undo(journal_path):
    data = json.loads(Path(journal_path).read_text(encoding="utf-8"))
    restored, errors = 0, []
    for m in reversed(data["deplacements"]):
        src, dst = Path(m["src"]), Path(m["dst"])
        try:
            if not dst.exists():
                errors.append(f"{dst.name} : introuvable (déplacé ou supprimé depuis)")
                continue
            back = src if not src.exists() else _unique(src, set())
            back.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(back))
            restored += 1
            # supprime les sous-dossiers devenus vides
            parent = dst.parent
            root = Path(data["dossier"])
            while parent != root and root in parent.parents:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        except Exception as e:
            errors.append(f"{dst.name} : {e}")
    Path(journal_path).rename(Path(journal_path).with_suffix(".annule"))
    return restored, errors


def human_size(n):
    for u in ["o", "Ko", "Mo", "Go", "To"]:
        if n < 1024:
            return f"{n:.0f} {u}" if u == "o" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} Po"


def known_folders():
    """Téléchargements / Bureau / Documents (gère OneDrive)."""
    h = Path.home()
    cands = {
        "Téléchargements": [h / "Downloads", h / "Téléchargements"],
        "Bureau": [h / "Desktop", h / "OneDrive" / "Desktop", h / "OneDrive" / "Bureau", h / "Bureau"],
        "Documents": [h / "Documents", h / "OneDrive" / "Documents"],
        "Images": [h / "Pictures", h / "OneDrive" / "Pictures", h / "OneDrive" / "Images"],
    }
    out = {}
    for name, paths in cands.items():
        for p in paths:
            if p.is_dir():
                out[name] = p
                break
    return out


# ---------------------------------------------------------------- interface
def main():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("Rangement C")
    root.geometry("980x620")
    root.minsize(760, 480)
    try:
        root.tk.call("tk", "scaling", 1.3)
    except tk.TclError:
        pass

    state = {"folder": None, "plan": []}
    mode = tk.StringVar(value="type")
    folder_var = tk.StringVar(value="Aucun dossier choisi")
    status = tk.StringVar(value="1) Choisis un dossier   2) Aperçu   3) Ranger")

    style = ttk.Style()
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass
    style.configure("Big.TButton", padding=(14, 8))

    # --- barre dossier
    top = ttk.Frame(root, padding=10)
    top.pack(fill="x")
    ttk.Label(top, text="Dossier :", font=("Segoe UI", 10, "bold")).pack(side="left")
    ttk.Label(top, textvariable=folder_var, foreground="#1f4e79").pack(side="left", padx=6)

    quick = ttk.Frame(root, padding=(10, 0))
    quick.pack(fill="x")

    def set_folder(p):
        reason = protection_reason(p)
        if reason:
            messagebox.showwarning("Dossier refusé", reason)
            return
        state["folder"] = Path(p)
        folder_var.set(str(p))
        preview()

    for name, p in known_folders().items():
        ttk.Button(quick, text=name, command=lambda p=p: set_folder(p)).pack(side="left", padx=3)
    ttk.Button(quick, text="Autre dossier…",
               command=lambda: (lambda d: d and set_folder(d))(filedialog.askdirectory())
               ).pack(side="left", padx=3)

    # --- mode
    modes = ttk.LabelFrame(root, text="Ranger par", padding=8)
    modes.pack(fill="x", padx=10, pady=8)
    for txt, val in [("Type (Images, PDF, Vidéos…)", "type"),
                     ("Date (Année / Mois)", "date"),
                     ("Type puis année", "type_date")]:
        ttk.Radiobutton(modes, text=txt, value=val, variable=mode,
                        command=lambda: state["folder"] and preview()).pack(side="left", padx=10)

    # --- tableau
    mid = ttk.Frame(root, padding=(10, 0))
    mid.pack(fill="both", expand=True)
    cols = ("fichier", "vers", "taille")
    tree = ttk.Treeview(mid, columns=cols, show="headings")
    tree.heading("fichier", text="Fichier")
    tree.heading("vers", text="Ira dans")
    tree.heading("taille", text="Taille")
    tree.column("fichier", width=420)
    tree.column("vers", width=360)
    tree.column("taille", width=90, anchor="e")
    sb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def preview():
        tree.delete(*tree.get_children())
        if not state["folder"]:
            return
        try:
            plan = plan_moves(state["folder"], mode.get())
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return
        state["plan"] = plan
        counts = {}
        for src, dst, size in plan:
            rel = dst.parent.relative_to(state["folder"])
            tree.insert("", "end", values=(src.name, str(rel), human_size(size)))
            top_cat = rel.parts[0]
            counts[top_cat] = counts.get(top_cat, 0) + 1
        total = sum(s for *_, s in plan)
        if plan:
            resume = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])[:6])
            status.set(f"{len(plan)} fichiers à ranger ({human_size(total)})  —  {resume}")
        else:
            status.set("Rien à ranger ici : les fichiers sont déjà dans des sous-dossiers.")

    def do_apply():
        if not state["plan"]:
            messagebox.showinfo("Rangement C", "Rien à ranger. Clique d'abord sur un dossier.")
            return
        if not messagebox.askyesno("Confirmer",
                                   f"Déplacer {len(state['plan'])} fichiers dans des sous-dossiers ?\n\n"
                                   "Rien n'est supprimé, et tu pourras annuler."):
            return
        root.config(cursor="watch")
        root.update()
        done, errors, _ = apply_moves(state["plan"], state["folder"])
        root.config(cursor="")
        msg = f"{len(done)} fichiers rangés."
        if errors:
            msg += f"\n\n{len(errors)} non déplacés (souvent : fichier ouvert) :\n" + "\n".join(errors[:10])
        messagebox.showinfo("Terminé", msg)
        preview()

    def do_undo():
        js = list_journals()
        if not js:
            messagebox.showinfo("Annuler", "Aucun rangement à annuler.")
            return
        data = json.loads(js[0].read_text(encoding="utf-8"))
        if not messagebox.askyesno("Annuler",
                                   f"Remettre en place les {len(data['deplacements'])} fichiers "
                                   f"du dernier rangement ?\n\nDossier : {data['dossier']}"):
            return
        n, errors = undo(js[0])
        msg = f"{n} fichiers remis à leur place."
        if errors:
            msg += "\n\n" + "\n".join(errors[:10])
        messagebox.showinfo("Annuler", msg)
        if state["folder"]:
            preview()

    def open_folder():
        if state["folder"] and sys.platform == "win32":
            os.startfile(state["folder"])

    # --- bas
    bottom = ttk.Frame(root, padding=10)
    bottom.pack(fill="x")
    ttk.Label(bottom, textvariable=status, wraplength=900).pack(fill="x", pady=(0, 8))
    btns = ttk.Frame(bottom)
    btns.pack(fill="x")
    ttk.Button(btns, text="✔ Ranger maintenant", style="Big.TButton", command=do_apply).pack(side="left")
    ttk.Button(btns, text="↶ Annuler le dernier rangement", style="Big.TButton",
               command=do_undo).pack(side="left", padx=8)
    ttk.Button(btns, text="Ouvrir le dossier", command=open_folder).pack(side="right")

    root.mainloop()


if __name__ == "__main__":
    main()
