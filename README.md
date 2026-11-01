# Rangement C

Application web qui range un dossier Windows (Téléchargements, Bureau, Documents…) par **type**, par **date** ou par **type puis année**.

- Fonctionne dans **Microsoft Edge** ou **Google Chrome** (API File System Access).
- Tout se passe en local : aucun fichier n'est envoyé sur Internet.
- Un aperçu est affiché avant le rangement. Aucun fichier n'est supprimé, et le dernier rangement peut être annulé.
- Le navigateur bloque l'accès aux dossiers système (`C:\`, `Windows`, `Program Files`, `AppData`).

## Structure
- `index.html` : l'application web (statique, déployée sur Vercel)
- `desktop/` : version de bureau en Python (tkinter), lancée avec `Lancer_Rangement_C.bat`
