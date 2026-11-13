# Tests de prétraitement : couverture et travaux restants

Cette note conserve la trace des vérifications non couvertes ou encore à décider avant de considérer le prétraitement comme généralisable à des sources externes. Les fonctions de préparation sont dans `script/preprocessing/preprocessing.py`, le CLI dans `script/preprocessing/preprocess_dataset.py`. La suite `test_preprocess_lyon63v.py` couvre des fixtures synthétiques, des erreurs contrôlées, le CLI générique par dossier et une intégration sur Lyon63V si les fichiers sont présents.

## État actuel

- La suite vérifie la conservation des lignes de demande, des répétitions et des trajets courts, les erreurs de champs, les coordonnées et horaires, le tri stable de l'export, plusieurs références réseau/arrêt, l'ODLayer, les empreintes des sources et les fichiers de sortie.
- Le jeu de tests synthétique ne garantit pas que toutes les variantes légitimes du format MnMS ou des exports de tiers soient acceptées.
- L'intégration Lyon63V est une seule source réelle et ne remplace pas un essai sur un second jeu de données indépendant.
- Le CLI accepte `--input-dir`, des noms de fichiers configurables et une sortie par défaut dans `PREPROCESSED`; les chemins explicites restent possibles.
- Le script refuse les cas où un nom de sortie correspondrait exactement à l'un des fichiers source.
- Un journal consolidé `review_log.csv` et un gabarit vide `review_decisions_template.csv` sont produits. Ils expliquent les anomalies et enregistrent les décisions humaines, mais ne les appliquent pas.

## Tests restants recommandés

1. **Contrat MnMS et variantes réelles**
   - Tester les variantes de casse/structure réelles acceptées par les lecteurs MnMS, notamment les champs et formes des couches, lignes, sections, horaires, arrêts et géométries.
   - Tester chaque format de demande admis par `CSVDemandManager`, dont les éventuelles colonnes facultatives, contraintes de tri et valeurs de services.
   - Comparer les exports générés par ce script avec le chargement effectif par MnMS, pas uniquement avec le parseur CSV.

2. **Autres jeux de données**
   - Faire un essai sur au moins un dataset indépendant (autre ville ou autre source) en documentant SCR, unités, schéma, date/version, licence et provenance.
   - Vérifier les réseaux sans transport collectif, sans arrêts, avec plusieurs couches et avec les modes autres que le bus.
   - Ne pas déclarer la généralisation terminée avant revue métier des avertissements et contrôles sur cet autre dataset.

3. **Sécurité des sorties et non-destruction**
   - Définir et tester le comportement souhaité si des fichiers de sortie existent déjà : actuellement, ils peuvent être remplacés ; envisager un refus par défaut et une option explicite d'écrasement.
   - Tester une erreur d'écriture (permissions, espace disque) et garantir une erreur contrôlée, sans résumé prétendant que les sorties ont été produites.
   - Comparer les lignes sources et sorties comme enregistrements CSV pour les cas où le parseur peut les lire ; conserver une copie/hash des octets sources comme preuve de non-modification.

4. **CSV complexes et grandes tailles**
   - Tester séparateurs/quotes, guillemets échappés, champs multilignes, lignes avec séparateurs dans du texte cité, BOM et encodages documentés.
   - Tester le CSV vide, une dernière ligne sans saut de ligne, plusieurs lignes vides, colonnes avec espaces dans les en-têtes et valeurs contenant des espaces significatifs.
   - Mesurer temps et mémoire sur une demande beaucoup plus grande que Lyon63V : le script charge actuellement toutes les lignes en mémoire.
   - Vérifier les horodatages qui franchissent minuit. Le format actuel est une heure de journée et l'ordre est contrôlé sans date ; il ne permet pas de décider seul si un retour à une heure plus tôt est un désordre ou le lendemain.

5. **Sémantique du modèle et géométrie**
   - Confirmer avec les mainteneurs les champs de tronçon obligatoires, le référentiel effectif des IDs (clé JSON versus champ `id`) et l'admissibilité de longueurs nulles.
   - Tester le contrôle de cohérence entre la longueur déclarée du tronçon et la géométrie, mais le garder informatif tant que la règle/unité n'est pas établie.
   - Tester les nœuds dont clé et `id` divergent, les IDs répétés sous des clés différentes, les arrêts sans section, et les types inattendus de `LAYERS`, `LINES`, `STOPS` ou `SECTIONS`.
   - Valider les connexions entre ODLayer et le réseau ainsi que les attributs des lignes (ordre et cohérence sections-arrêts, horaires), pas seulement les coordonnées OD.
   - Définir les règles de SCR/unités par jeu de données ; ne jamais déduire une erreur de coordonnées uniquement de leur amplitude.

6. **Politique d'export**
   - Décider si l'export « pour simulation » doit être bloqué uniquement par les erreurs de demande, ou également par les erreurs réseau et ODLayer ; les tests actuels codent le comportement actuel (blocage selon erreurs de demande).
   - Décider si les avertissements sont acceptables pour l'export et éventuellement proposer un mode strict séparé ; aucune règle ne doit supprimer automatiquement de lignes.
   - Tester que le code retour reflète bien les erreurs de tous les datasets, et que les comptes distinguent erreurs fichier/schéma et lignes bloquées.
   - Si une étape d'application des décisions humaines est ajoutée, tester qu'elle refuse toute décision incomplète/non validée et qu'elle ne modifie qu'une copie dérivée, jamais les sources.

## Critère de clôture proposé

La généralisation sera raisonnablement prête lorsque les tests synthétiques passent, les entrées sont lues par les loaders MnMS sur les formats supportés, un deuxième dataset indépendant est validé, les risques de collision/écrasement de sorties sont tranchés, et les décisions SCR/horodatage/export ont été documentées. Cette liste est volontairement conservée comme trace des travaux restants, même si ces tests ou validations ne sont pas inclus dans une branche principale.
