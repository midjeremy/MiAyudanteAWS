<?php
// Login obligatorio: toda página del sitio, salvo login.php, registro.php y logout.php,
// debe incluir este archivo antes de mostrar contenido.
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

function hay_sesion(): bool{
    return !empty($_SESSION['usuario']) && !empty($_SESSION['token_acceso']);
}

// Páginas: sin sesión, redirige al login (ruta absoluta para que sirva también desde pages/)
function requerir_sesion(): void{
    if (!hay_sesion()) {
        header('Location: /templates/login.php');
        exit();
    }
}

// Endpoints JSON (como chat.php): sin sesión responde 401 en vez de redirigir
function requerir_sesion_json(): void{
    if (!hay_sesion()) {
        http_response_code(401);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['error' => 'Debes iniciar sesión.'], JSON_UNESCAPED_UNICODE);
        exit();
    }
    // Libera el bloqueo de la sesión: si no, una respuesta lenta del asistente
    // dejaría esperando cualquier otra página que abra el mismo usuario
    session_write_close();
}
