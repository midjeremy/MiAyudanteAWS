<?php
require_once 'api.php';

//Iniciar la sesión para poder acceder a ella
session_start();

// Revocar los JWT en la API antes de olvidarlos: sin esto seguían sirviendo hasta vencer (1 hora el de acceso)
if (!empty($_SESSION['token_acceso']) || !empty($_SESSION['token_refresco'])) {
    api_post('/api/v1/auth/logout/', ['refresh' => $_SESSION['token_refresco'] ?? ''], $_SESSION['token_acceso'] ?? null);
}

//Limpiar todas las variables de sesión
$_SESSION = array();

//Destruir la sesión por completo
session_destroy();

//Redirigir al usuario al archivo de login
header("Location: login.php");
exit();
?>
