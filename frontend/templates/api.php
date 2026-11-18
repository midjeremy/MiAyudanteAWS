<?php
// Dirección interna de Django: en el servidor, PHP y Django están en la misma máquina (Nginx define
// MIAYUDANTE_API_URL=http://127.0.0.1:8000). Para probar en local contra producción, definir la variable
// con el dominio HTTPS (https://mi-ayudante.cl): la IP por HTTP responde 301 y cURL no lo sigue.
// No usar el dominio público como valor por defecto: Django vería la IP del propio servidor y todos los
// visitantes compartirían el mismo límite de intentos de login.
define('API_BASE_URL', getenv('MIAYUDANTE_API_URL') ?: 'http://127.0.0.1:8000');

// $espera: segundos máximos de la llamada. El asistente (chat.php) necesita más que el resto (50 s).
function api_solicitud(string $metodo, string $ruta, ?array $datos = null, ?string $token = null, int $espera = 5): array{
    $cabeceras = [
        'Accept: application/json',
        // Django limita los intentos de login por IP: se envía la del visitante
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
        CURLOPT_TIMEOUT => $espera,
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