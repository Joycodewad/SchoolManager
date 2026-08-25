"""Signature manuscrite enregistrée par l'utilisateur lui-même.

Le tracé fait à l'écran arrive en PNG encodé. Chacun enregistre la sienne :
il n'y a pas de point d'entrée pour signer à la place d'un autre.
"""

import base64
import io
import os

from PIL import Image as PillowImage, ImageDraw

from django.core.files.base import ContentFile
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from ekdschoolmanager.models import CustomUser
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph

from ekdschoolmanager.reportcard_pdf import (
    OFFICIAL_FOOT, SIGNATURE_BOX, official_subjects_table, signature_cell, signature_image,
)
from ekdschoolmanager.reportcards import signature_path

# Le plus petit PNG valide : un pixel, en-tête comprise.
PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
DATA_URL = "data:image/png;base64," + base64.b64encode(PIXEL_PNG).decode()


class MySignatureTests(APITestCase):
    url = "/api/me/signature/"

    def setUp(self):
        self.user = CustomUser.objects.create_user(username="proviseur", password="x")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def tearDown(self):
        self.user.refresh_from_db()
        self.user.signature.delete(save=False)

    def test_au_depart_aucune_signature(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_signature"])
        self.assertIsNone(response.data["signature"])

    def test_le_trace_est_enregistre(self):
        response = self.client.put(self.url, {"image": DATA_URL}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["has_signature"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.signature)

    def test_une_nouvelle_signature_remplace_l_ancienne(self):
        """Signer à nouveau ne laisse pas le fichier précédent sur le disque."""
        self.client.put(self.url, {"image": DATA_URL}, format="json")
        self.user.refresh_from_db()
        first = self.user.signature.path

        self.client.put(self.url, {"image": DATA_URL}, format="json")
        self.user.refresh_from_db()
        self.assertFalse(os.path.exists(first) and self.user.signature.path != first)

    def test_un_contenu_qui_n_est_pas_un_png_est_refuse(self):
        payload = "data:image/png;base64," + base64.b64encode(b"pas une image").decode()
        response = self.client.put(self.url, {"image": payload}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.data)

    def test_une_charge_utile_illisible_est_refusee(self):
        response = self.client.put(self.url, {"image": "n'importe quoi"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_une_signature_trop_lourde_est_refusee(self):
        heavy = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 600_000).decode()
        response = self.client.put(self.url, {"image": heavy}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("512", str(response.data))

    def test_la_signature_se_supprime(self):
        self.client.put(self.url, {"image": DATA_URL}, format="json")
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["has_signature"])

    def test_il_faut_etre_connecte(self):
        self.client.credentials()
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_le_bulletin_ignore_un_fichier_disparu(self):
        """Signature effacée du disque : le PDF s'imprime sans image."""
        self.user.signature.save("signature-test.png", ContentFile(PIXEL_PNG), save=True)
        path = self.user.signature.path
        self.assertEqual(signature_path(self.user), path)

        os.remove(path)
        self.assertEqual(signature_path(self.user), "")


class SignatureFramingTests(APITestCase):
    """Cadrage : le tracé occupe sa colonne sans marge morte ni déformation."""

    url = "/api/me/signature/"

    def setUp(self):
        self.user = CustomUser.objects.create_user(username="proviseur", password="x")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def tearDown(self):
        self.user.refresh_from_db()
        self.user.signature.delete(save=False)

    @staticmethod
    def drawn_in_a_corner():
        """Un tracé dans un coin d'un grand cadre, comme on signe vraiment."""
        canvas = PillowImage.new("RGBA", (900, 300), (255, 255, 255, 255))
        ImageDraw.Draw(canvas).line(
            [(60, 90), (110, 40), (150, 110), (200, 50)], fill=(17, 24, 39, 255), width=5,
        )
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_le_vide_autour_du_trace_est_rogne(self):
        """Sans rognage, le bulletin réduirait le cadre entier, marges comprises."""
        self.client.put(
            self.url,
            {"image": "data:image/png;base64," + base64.b64encode(self.drawn_in_a_corner()).decode()},
            format="json",
        )
        self.user.refresh_from_db()
        saved = PillowImage.open(self.user.signature.path)
        self.assertLess(saved.width, 400)
        self.assertLess(saved.height, 200)

    def test_le_fond_devient_transparent(self):
        """Un pavé blanc masquerait le filigrane du bulletin."""
        self.client.put(
            self.url,
            {"image": "data:image/png;base64," + base64.b64encode(self.drawn_in_a_corner()).decode()},
            format="json",
        )
        self.user.refresh_from_db()
        saved = PillowImage.open(self.user.signature.path).convert("RGBA")
        self.assertEqual(saved.getpixel((0, 0))[3], 0)

    def test_la_signature_suit_l_alignement_de_son_bloc(self):
        """Bloc du pied de page aligné à gauche ; colonne de grille centrée."""
        self.user.signature.save(
            "signature-cadrage.png", ContentFile(self.drawn_in_a_corner()), save=True,
        )
        self.assertEqual(signature_image(self.user.signature.path).hAlign, "LEFT")
        self.assertEqual(
            signature_image(self.user.signature.path, align="CENTER").hAlign, "CENTER",
        )

    def test_la_signature_tient_dans_sa_boite_sans_s_etirer(self):
        self.user.signature.save(
            "signature-echelle.png", ContentFile(self.drawn_in_a_corner()), save=True,
        )
        image = signature_image(self.user.signature.path)
        max_width, max_height = SIGNATURE_BOX
        self.assertLessEqual(round(image.drawWidth, 3), round(max_width, 3))
        self.assertLessEqual(round(image.drawHeight, 3), round(max_height, 3))
        # 900x300 : le rapport 3/1 du cadre d'origine est conservé.
        self.assertAlmostEqual(image.drawWidth / image.drawHeight, 900 / 300, delta=0.6)

    def test_un_fichier_illisible_ne_casse_pas_l_edition(self):
        self.assertIsNone(signature_image("/introuvable/signature.png"))

    def test_le_bloc_signataire_intercale_la_signature_entre_titre_et_nom(self):
        """Fonction, signature, nom : dans cet ordre, sans rien entre eux."""
        self.user.signature.save(
            "signature-bloc.png", ContentFile(self.drawn_in_a_corner()), save=True,
        )
        parts = signature_cell(
            {"title": "Le Proviseur", "name": "Komla AMAH",
             "signature": self.user.signature.path},
            OFFICIAL_FOOT,
        )
        self.assertEqual([type(part) for part in parts], [Paragraph, Image, Paragraph])
        self.assertIn("Le Proviseur", parts[0].text)
        self.assertEqual(parts[2].text, "Komla AMAH")

    def test_une_signature_de_matiere_n_agrandit_pas_sa_ligne(self):
        """Exigence de la grille : la ligne garde exactement sa hauteur."""
        self.user.signature.save(
            "signature-grille.png", ContentFile(self.drawn_in_a_corner()), save=True,
        )

        def card():
            return {
                "line_columns": [{"id": 1, "name": "Note inter."}],
                "groups": [{"name": "", "subjects": [{
                    "class_subject_id": 11, "subject": "Mathématiques", "coefficient": "4",
                    "scores": {"1": "11.50"}, "average": "9.65", "weighted": "38.60",
                    "rank": 3, "teacher": "Kpakpadja TCHAGBA", "appreciation": "Passable",
                }]}],
                "coefficient_total": "4", "weighted_total": "38.60",
            }

        plain = official_subjects_table(card(), {"show_score_detail": True})
        signed = official_subjects_table(card(), {
            "show_score_detail": True,
            "teacher_signatures": {11: self.user.signature.path},
        })
        self.assertEqual(plain.wrap(178 * mm, 0), signed.wrap(178 * mm, 0))
        self.assertEqual(plain._rowHeights, signed._rowHeights)
