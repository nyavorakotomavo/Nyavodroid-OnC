#!/bin/bash
# push_onc.sh — Crée le repo OnC et push le code
# Exécuter depuis la racine du projet Nyavodroid

set -e

REPO="OnC"

echo "🧹 Étape 1 : Suppression des fichiers morts"
rm -f patch.py patch2.py patch3.py patch4.py
rm -f fix_cf.py fix_prompt.py cf_test.py
rm -f post_content.py.bak post_story.py.bak
rm -f QWEN.md profile.png vis_slide_1.png vis_story.png vis_texte.png kataconmb.zip
rm -rf __pycache__
echo "  ✅ Fichiers morts supprimés"

echo ""
echo "📦 Étape 2 : Initialisation git"
git init -b main
git add -A
git status

echo ""
echo "📝 Étape 3 : Commit"
git commit -m "feat: séparation logique/style — themes YAML + content_config v2

- themes/nyavo.yaml, themes/vis.yaml : style extrait des configs Python
- content_config.py : loader YAML unifié, fallback legacy .py
- get_font + wrap_text_pillow : logique unifiée (plus de duplication)
- pyyaml ajouté à requirements.txt + workflows
- Fichiers morts supprimés (patch*.py, fix*.py, *.bak)"

echo ""
echo "🔗 Étape 4 : Connexion au repo OnC"
# Crée le repo via GitHub CLI (nécessite gh auth)
gh repo create "$REPO" --private --source=. --push 2>/dev/null || {
    echo "  ℹ️  Repo peut-être déjà existant, ajout du remote..."
    git remote add origin "https://github.com/$(gh api user -q .login)/$REPO.git" 2>/dev/null || true
    git remote set-url origin "https://github.com/$(gh api user -q .login)/$REPO.git"
    git push -u origin main
}

echo ""
echo "✅ Terminé ! Repo : https://github.com/$(gh api user -q .login)/$REPO"
