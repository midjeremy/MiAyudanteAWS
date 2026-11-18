<?php
// Dirección de la API Django: ajusta la IP/URL por defecto si no estás en local
// Usar el dominio HTTPS: la IP por HTTP responde 301 hacia https://mi-ayudante.cl y cURL no lo sigue
define('API_BASE_URL', getenv('MIAYUDANTE_API_URL') ?: 'https://mi-ayudante.cl');

function api_solicitud(string $metodo, string $ruta, ?array $datos = null, ?string $token = null): array{
    $cabeceras = [
        'Accept: application/json',
        'X-Forwarded-For: ' . ($_SERVER['REMOTE_ADDR'] ?? ''),
    ];
    if ($datos !== null) {
        $cabeceras[] = 'Content-Type: application/json';
    }
    if ($token !== null) {
        $cabeceras[] = 'Authorization: Bearer ' . $token;
    }

    $ch = curl_init(API_BASE_URL . $ruta);
    curl_setopt_array($ch,[
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 5,
        CURLOPT_CUSTOMREQUEST => $metodo,
        CURLOPT_HTTPHEADER => $cabeceras,
    ]);
    if ($datos !== null) {
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($datos));
    }
    $respuesta = curl_exec($ch);
    $codigo = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if ($respuesta === false) {
        // Deja el motivo real en el log de PHP (DNS, TLS, timeout...) en vez de fallar en silencio
        error_log('api_solicitud ' . $metodo . ' ' . $ruta . ': ' . curl_error($ch));
    }

    return [
        'codigo' => $codigo,
        'datos' => ($respuesta === false) ? null : json_decode($respuesta, true),
    ];
}

function api_get(string $ruta): ?array{
    $resultado = api_solicitud('GET', $ruta);
    return ($resultado['codigo'] === 200) ? $resultado['datos'] : null;
}

function api_post(string $ruta, array $datos, ?string $token = null): array{
    return api_solicitud('POST', $ruta, $datos, $token);
}