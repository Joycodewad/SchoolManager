import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';

/// Erreur d'API portant un message déjà lisible par l'utilisateur.
///
/// Django renvoie ses erreurs sous forme de dictionnaire champ → message ;
/// on les aplatit ici une bonne fois, pour que les écrans n'aient qu'à
/// afficher `error.message`.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.fields = const {}});

  final String message;
  final int? statusCode;
  final Map<String, String> fields;

  /// Vrai quand le jeton n'est plus valable : la session doit être fermée.
  bool get isUnauthorized => statusCode == 401 || statusCode == 403;

  @override
  String toString() => message;
}

/// Client HTTP de l'API Django.
///
/// Porte le jeton et le contexte courant (école, année) : le backend lit
/// `X-Academic-Year-ID` sur la plupart des vues, et l'oublier fait échouer la
/// requête avec « Sélectionnez une année académique ».
class ApiClient {
  ApiClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;

  String? _token;
  int? _yearId;

  /// Appelée quand le serveur rejette le jeton : la session doit se fermer.
  void Function()? onUnauthorized;

  void configure({String? token, int? yearId}) {
    _token = token;
    _yearId = yearId;
  }

  void clear() {
    _token = null;
    _yearId = null;
  }

  Map<String, String> _headers() => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Token $_token',
        if (_yearId != null) 'X-Academic-Year-ID': '$_yearId',
      };

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final cleaned = query?.entries
        .where((entry) => entry.value != null)
        .map((entry) => MapEntry(entry.key, '${entry.value}'));
    return Uri.parse('${AppConfig.apiUrl}$path').replace(
      queryParameters: cleaned == null || cleaned.isEmpty
          ? null
          : Map.fromEntries(cleaned),
    );
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _send(() => _http.get(_uri(path, query), headers: _headers()));

  Future<dynamic> post(String path, {Object? body}) => _send(
        () => _http.post(
          _uri(path),
          headers: _headers(),
          body: jsonEncode(body ?? const {}),
        ),
      );

  Future<dynamic> put(String path, {Object? body}) => _send(
        () => _http.put(
          _uri(path),
          headers: _headers(),
          body: jsonEncode(body ?? const {}),
        ),
      );

  Future<dynamic> patch(String path, {Object? body}) => _send(
        () => _http.patch(
          _uri(path),
          headers: _headers(),
          body: jsonEncode(body ?? const {}),
        ),
      );

  Future<dynamic> delete(String path) =>
      _send(() => _http.delete(_uri(path), headers: _headers()));

  Future<dynamic> _send(Future<http.Response> Function() request) async {
    http.Response response;
    try {
      response = await request().timeout(AppConfig.requestTimeout);
    } on TimeoutException {
      throw ApiException(
        'Le serveur met trop de temps à répondre. Réessayez.',
      );
    } catch (_) {
      // Panne réseau, serveur éteint, mauvaise adresse : de l'extérieur c'est
      // indiscernable, et le message doit rester actionnable.
      throw ApiException(
        'Impossible de joindre le serveur. Vérifiez votre connexion.',
      );
    }

    if (response.statusCode == 204 || response.body.isEmpty) return null;

    dynamic data;
    try {
      data = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      // Une page d'erreur HTML n'est pas exploitable : on ne la montre pas.
      if (response.statusCode >= 400) {
        throw ApiException(
          'Erreur du serveur (${response.statusCode}).',
          statusCode: response.statusCode,
        );
      }
      return null;
    }

    if (response.statusCode >= 400) {
      final failure = _describe(data, response.statusCode);
      if (failure.isUnauthorized) onUnauthorized?.call();
      throw failure;
    }
    return data;
  }

  /// Aplatit une erreur DRF en un message lisible, en gardant le détail par
  /// champ pour les formulaires qui savent l'exploiter.
  ApiException _describe(dynamic data, int statusCode) {
    if (data is Map) {
      final fields = <String, String>{};
      for (final entry in data.entries) {
        final value = entry.value;
        fields['${entry.key}'] =
            value is List ? value.join(' ') : '$value';
      }
      // `detail` et `message` sont les clés que DRF et les vues du projet
      // utilisent pour un message global ; elles priment sur le reste.
      final global = fields['detail'] ?? fields['message'] ?? fields['permission'];
      final message = global ??
          fields.entries.map((entry) => entry.value).join(' — ');
      return ApiException(
        message.isEmpty ? 'Une erreur est survenue.' : message,
        statusCode: statusCode,
        fields: fields,
      );
    }
    return ApiException('Une erreur est survenue.', statusCode: statusCode);
  }

  void dispose() => _http.close();
}
