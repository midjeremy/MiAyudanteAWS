<?php
//Iniciar la sesión para poder acceder a ella
session_start();

//Limpiar todas las variables de sesión
$_SESSION = array();

//Destruir la sesión por completo
session_destroy();

//Redirigir al usuario al archivo de login
header("Location: login.php");
exit();
?>