<?php
// Dirección de la API Django: ajusta la IP/URL por defecto si no estás en local
define('API_BASE_URL', getenv('MIAYUDANTE_API_URL') ?: 'http://44.196.193.153');

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