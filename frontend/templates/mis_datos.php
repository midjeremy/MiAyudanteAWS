<?php
// [LEY 21.719] ARCHIVO NUEVO. Derechos de acceso y portabilidad: descarga los datos del titular
// (cuenta, consentimientos y resultados del test) en JSON, tal como los entrega Django.
session_start();
require_once 'api.php';

$token = $_SESSION['token_acceso'] ?? null;
if (!isset($_SESSION['usuario']) || $token === null) {
    header('Location: login.php');
    exit;
}

$r = api_solicitud('GET', '/api/v1/auth/mis-datos/', null, $token);

if ($r['codigo'] === 401) {
    // El token venció: se pide iniciar sesión de nuevo
    $_SESSION['flash_privacidad'] = ['tipo' => 'error', 'texto' => 'Tu sesión expiró. Cierra sesión e inicia de nuevo para descargar tus datos.'];
    header('Location: perfil.php#privacidad');
    exit;
}
if ($r['codigo'] !== 200 || !is_array($r['datos'])) {
    $_SESSION['flash_privacidad'] = ['tipo' => 'error', 'texto' => 'No pudimos preparar tus datos. Inténtalo más tarde.'];
    header('Location: perfil.php#privacidad');
    exit;
}

header('Content-Type: application/json; charset=utf-8');
header('Content-Disposition: attachment; filename="mis-datos-mi-ayudante.json"');
header('Cache-Control: no-store');   // datos personales: que el navegador no los guarde en caché
echo json_encode($r['datos'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
exit;
