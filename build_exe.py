import os
import sys
import shutil

def main():
    print("=" * 60)
    print("  Préparation et compilation de l'exécutable Windows (.exe)")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # 1. Vérification des polices arabes
    fonts_dir = os.path.join(base_dir, "fonts")
    dot_fonts_dir = os.path.join(base_dir, ".fonts")

    if os.path.exists(dot_fonts_dir) and not os.path.exists(fonts_dir):
        print("-> Copie des polices depuis .fonts vers fonts...")
        shutil.copytree(dot_fonts_dir, fonts_dir)
    elif os.path.exists(fonts_dir) and not os.path.exists(dot_fonts_dir):
        print("-> Copie des polices depuis fonts vers .fonts...")
        shutil.copytree(fonts_dir, dot_fonts_dir)

    # 2. Définition du séparateur PyInstaller (; sur Windows, : sur Linux/macOS)
    sep = ";" if sys.platform == "win32" else ":"

    # 3. Arguments PyInstaller
    args = [
        "editeur_desktop.py",
        "--name=Editeur_Fiches_Pedagogiques",
        "--onefile",
        "--noconsole",
        "--clean",
        f"--add-data=fonts{sep}fonts",
        f"--add-data=.fonts{sep}.fonts",
        "--hidden-import=fitz",
        "--hidden-import=pymupdf",
        "--hidden-import=arabic_reshaper",
        "--hidden-import=bidi",
        "--hidden-import=bidi.algorithm",
        "--hidden-import=reportlab",
        "--hidden-import=tkinter",
    ]

    print("-> Lancement de PyInstaller avec les options suivantes :")
    for a in args:
        print(f"   {a}")
    print("\nVeuillez patienter pendant l'assemblage...\n")

    import PyInstaller.__main__
    PyInstaller.__main__.run(args)

    # 4. Vérification du résultat
    ext = ".exe" if sys.platform == "win32" else ""
    built_path = os.path.join(base_dir, "dist", f"Editeur_Fiches_Pedagogiques{ext}")
    target_path = os.path.join(base_dir, f"Editeur_Fiches_Pedagogiques{ext}")

    if os.path.exists(built_path):
        print("\n" + "=" * 60)
        print("  COMPILATION TERMINÉE AVEC SUCCÈS !")
        print(f"  Fichier créé : {target_path}")
        print("=" * 60)
        shutil.copy2(built_path, target_path)
    else:
        print("\n[!] Attention : le fichier attendu dans dist/ n'a pas été trouvé.")

if __name__ == "__main__":
    main()
