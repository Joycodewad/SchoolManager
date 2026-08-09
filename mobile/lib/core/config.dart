/// Réglages d'environnement de l'application.
library;

class AppConfig {
  /// Adresse de l'API Django.
  ///
  /// Se surcharge au lancement sans retoucher le code :
  /// `flutter run --dart-define=API_URL=http://192.168.1.10:8000/api`
  ///
  /// Le défaut vise `10.0.2.2`, l'alias de la machine hôte vu depuis
  /// l'émulateur Android — `localhost` y désignerait le téléphone lui-même,
  /// et l'application ne joindrait rien.
  static const String apiUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://10.0.2.2:8000/api',
  );

  /// Délai au-delà duquel une requête est abandonnée. Sur un réseau mobile
  /// lent, mieux vaut un message clair qu'un écran qui tourne sans fin.
  static const Duration requestTimeout = Duration(seconds: 20);
}
