<?php
// Puente entre el widget del asistente y Django: Nginx no publica /api/chatbot/.
require_once 'api.php';

// Debe ser mayor que el tiempo máximo de OpenAI en chatbot/services.py
const ESPERA_ASISTENTE = 35;

function responder(int $codigo, array $datos): void{
    http_response_code($codigo);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($datos, JSON_UNESCAPED_UNICODE);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    responder(405, ['error' => 'Método no permitido.']);
}

// Exigir JSON impide que otro sitio use este puente desde el navegador de un visitante
if (!str_starts_with($_SERVER['CONTENT_TYPE'] ?? '', 'application/json')) {
    responder(415, ['error' => 'El mensaje debe enviarse como JSON.']);
}

$datos = json_decode(file_get_contents('php://input'), true);
if (!is_array($datos)) {
    responder(400, ['error' => 'No pudimos leer tu mensaje.']);
}

$resultado = api_solicitud('POST', '/api/chatbot/', [
    'mensaje' => $datos['mensaje'] ?? '',
    'historial' => $datos['historial'] ?? [],
], null, ESPERA_ASISTENTE);

$codigo = $resultado['codigo'];
$respuesta = $resultado['datos'];

if ($codigo === 200 && isset($respuesta['respuesta'])) {
    responder(200, ['respuesta' => $respuesta['respuesta']]);
}
if ($codigo === 400 && isset($respuesta['error'])) {
    responder(400, ['error' => $respuesta['error']]);
}
if ($codigo === 429) {
    responder(429, ['error' => 'Enviaste muchos mensajes seguidos. Espera un minuto e inténtalo de nuevo.']);
}
responder(502, ['error' => 'El asistente no está disponible en este momento. Inténtalo más tarde.']);
