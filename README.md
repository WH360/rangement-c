# Rangement C

Application web qui range un dossier Windows (Téléchargements, Bureau, Documents…) par **type**, par **date** ou par **type puis année**.

- Fonctionne dans **Microsoft Edge** ou **Google Chrome** (API File System Access).
- Tout se passe en local : aucun fichier n'est envoyé sur Internet.
- Un aperçu est affiché avant le rangement. Aucun fichier n'est supprimé, et le dernier rangement peut être annulé.
- **Par sujet** : lit le texte des PDF, Word et TXT (localement) pour classer en Factures, CV & Candidatures, Articles scientifiques, Protocoles & Labo, Administratif, Banque, Voyages, Cours.
- **Sous-dossiers** : analyse le contenu de chaque sous-dossier et le déplace en entier dans la bonne catégorie (les dossiers mélangés, les logiciels et les dossiers vides restent en place).
- **Doublons** : détecte les fichiers identiques (SHA-256) dans tous les sous-dossiers et peut déplacer les copies dans `_Doublons`.
- Le navigateur bloque l'accès aux dossiers système (`C:\`, `Windows`, `Program Files`, `AppData`).

## Structure
- `index.html` : l'application web (statique, déployée sur Vercel)
- `vendor/` : pdf.js et JSZip (lecture des PDF et Word, embarqués)
- `desktop/` : version de bureau en Python (tkinter), lancée avec `Lancer_Rangement_C.bat`
