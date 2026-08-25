"""Signatures imprimées au pied du bulletin.

Les intitulés — « Le Proviseur », « Le Censeur » — appartiennent à la maquette.
Ce qui se règle, c'est le nom inscrit dessous, et il vient des rôles de
l'établissement plutôt que d'une saisie à part : un changement de proviseur
suit tout seul.
"""

from django.test import TestCase

from ekdschoolmanager.models import CustomUser, School, SchoolMembership
from ekdschoolmanager.reportcard_pdf import footer_block, official_footer
from ekdschoolmanager.reportcards import role_holders, settings_for, signatories_for


class SignatoryTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(username="fondateur", password="x")
        self.owner.first_name, self.owner.last_name = "Kossi", "AMEGAN"
        self.owner.save()
        self.school = School.objects.create(
            name="Lycée d'Amou-Oblo", code="lycee-amou-oblo", owner=self.owner, city="Amou-Oblo",
        )
        self.configuration = settings_for(self.school)

    def hire(self, role, first, last):
        user = CustomUser.objects.create_user(username=f"{role}-{last}", password="x", role=role)
        user.first_name, user.last_name = first, last
        user.save()
        SchoolMembership.objects.create(
            school=self.school, user=user, role=role, is_active=True,
        )
        return user

    def test_les_roles_de_l_ecole_fournissent_les_noms(self):
        self.hire(CustomUser.Role.PROVISEUR, "Sena", "KIMÉYALOU")
        self.hire(CustomUser.Role.CENSEUR, "Afi", "TCHAGBA")
        self.assertEqual(
            {row["key"]: row["name"] for row in role_holders(self.school)},
            {"censor": "Afi TCHAGBA", "founder": "Kossi AMEGAN", "principal": "Sena KIMÉYALOU"},
        )

    def test_un_poste_vacant_rend_un_nom_vide(self):
        """Le paramétrage peut alors annoncer « poste vacant » plutôt que rien."""
        holders = {row["key"]: row["name"] for row in role_holders(self.school)}
        self.assertEqual(holders["principal"], "")
        self.assertEqual(holders["censor"], "")

    def test_seul_le_proviseur_signe_par_defaut(self):
        """Réglage d'usage : le proviseur, et lui seul."""
        self.hire(CustomUser.Role.PROVISEUR, "Sena", "KIMÉYALOU")
        self.hire(CustomUser.Role.CENSEUR, "Afi", "TCHAGBA")
        self.assertEqual(
            [row["key"] for row in signatories_for(self.school, self.configuration)],
            ["principal"],
        )

    def test_un_poste_vacant_ne_produit_pas_de_signature_orpheline(self):
        """Case cochée mais personne au poste : rien ne s'imprime."""
        self.configuration.show_censor_name = True
        self.assertEqual(signatories_for(self.school, self.configuration), [])

    def test_les_trois_signataires_s_impriment_dans_l_ordre(self):
        self.hire(CustomUser.Role.PROVISEUR, "Sena", "KIMÉYALOU")
        self.hire(CustomUser.Role.CENSEUR, "Afi", "TCHAGBA")
        self.configuration.show_censor_name = True
        self.configuration.show_founder_name = True
        self.assertEqual(
            [row["key"] for row in signatories_for(self.school, self.configuration)],
            ["censor", "founder", "principal"],
        )

    # ── Rendu ────────────────────────────────────────────────────────────────

    @staticmethod
    def cell_text(table):
        """Texte des paragraphes d'un tableau ReportLab, mis bout à bout.

        Une cellule peut empiler plusieurs flowables — titre, signature, nom —
        d'où la descente dans les listes.
        """
        def walk(node):
            if isinstance(node, (list, tuple)):
                return " ".join(walk(item) for item in node)
            return getattr(node, "text", "")

        return walk(table._cellvalues)

    def signatures(self, **kwargs):
        return official_footer({"city": "Amou-Oblo"}, "", **kwargs)[2]

    def test_le_nom_du_proviseur_s_imprime_sous_son_titre(self):
        rows = [{"key": "principal", "title": "Le Proviseur", "name": "Sena KIMÉYALOU"}]
        printed = self.cell_text(self.signatures(signatories=rows))
        self.assertIn("Le Proviseur", printed)
        self.assertIn("Sena KIMÉYALOU", printed)

    def test_le_titre_du_proviseur_reste_sans_son_nom(self):
        """La maquette officielle garde sa ligne à signer, nom ou pas."""
        printed = self.cell_text(self.signatures())
        self.assertIn("Le Proviseur", printed)
        self.assertIn("AMOU-OBLO, le", printed)

    def test_chaque_signataire_prend_sa_colonne(self):
        rows = [
            {"key": "censor", "title": "Le Censeur", "name": "Afi TCHAGBA"},
            {"key": "founder", "title": "Le Fondateur", "name": "Kossi AMEGAN"},
            {"key": "principal", "title": "Le Proviseur", "name": "Sena KIMÉYALOU"},
        ]
        table = self.signatures(signatories=rows)
        # Titulaire + censeur + fondateur + proviseur.
        self.assertEqual(len(table._cellvalues[0]), 4)
        printed = self.cell_text(table)
        for name in ("Afi TCHAGBA", "Kossi AMEGAN", "Sena KIMÉYALOU"):
            self.assertIn(name, printed)

    def test_la_maquette_standard_empile_les_signataires(self):
        rows = [
            {"key": "founder", "title": "Le Fondateur", "name": "Kossi AMEGAN"},
            {"key": "principal", "title": "Le Proviseur", "name": "Sena KIMÉYALOU"},
        ]
        printed = self.cell_text(footer_block({"city": "Amou-Oblo"}, "", signatories=rows))
        self.assertIn("LE FONDATEUR", printed)
        self.assertIn("Kossi AMEGAN", printed)
        self.assertIn("LE PROVISEUR", printed)
        self.assertIn("Sena KIMÉYALOU", printed)

    def test_la_maquette_standard_garde_son_intitule_sans_signataire(self):
        printed = self.cell_text(footer_block({"city": "Amou-Oblo"}, ""))
        self.assertIn("LE DIRECTEUR / PROVISEUR", printed)
