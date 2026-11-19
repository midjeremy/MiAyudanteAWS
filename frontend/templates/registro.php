<?php
session_start();
require_once 'api.php';

$error = "";
$exito = "";

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $correo = trim($_POST["correo"] ?? "");
    $nombre = trim($_POST["nombre"] ?? "");
    $apellidos = trim($_POST["apellidos"] ?? "");
    $password = $_POST["password"] ?? "";
    // [LEY 21.719] Casillas de consentimiento y edad mínima (llegan solo si están marcadas)
    $acepta_privacidad = isset($_POST["acepta_privacidad"]);
    $mayor_14 = isset($_POST["mayor_14"]);

    if (empty($correo) || empty($nombre) || empty($apellidos) || empty($password)) {
        $error = "Por favor, completa todos los campos.";
    } elseif (!$acepta_privacidad) {
        // [LEY 21.719] Sin consentimiento expreso no se crea la cuenta (Django también lo valida)
        $error = "Debes aceptar la Política de privacidad para crear tu cuenta.";
    } elseif (!$mayor_14) {
        // [LEY 21.719] Art. 16 quáter: las cuentas son para personas de 14 años o más
        $error = "Las cuentas son para personas de 14 años o más. Puedes usar el buscador, el comparador, el test y el asistente sin crear una cuenta.";
    } else {
        // Django crea la cuenta, guarda la contraseña cifrada y la constancia del consentimiento
        $resultado = api_post('/api/v1/auth/registro/', [
            'correo' => $correo,
            'nombre' => $nombre,
            'apellidos' => $apellidos,
            'password' => $password,
            'acepta_privacidad' => true,   // [LEY 21.719]
            'mayor_14' => true,            // [LEY 21.719]
        ]);

        if ($resultado['codigo'] === 201) {
            $exito = "¡Cuenta creada con éxito! Redirigiendo al inicio de sesión...";
            header("refresh:2;url=login.php");
        } elseif (in_array($resultado['codigo'], [400, 409], true)) {
            $error = $resultado['datos']['error'] ?? "Revisa los datos ingresados.";
        } elseif ($resultado['codigo'] === 429) {
            $error = "Demasiados intentos. Espera un minuto e inténtalo de nuevo.";
        } else {
            $error = "No pudimos conectar con el servidor. Inténtalo más tarde.";
        }
    }
}
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Regístrate - Mi Ayudante</title>
    <link rel="icon" type="image/png"  href="/static/img/Birrete.ico">
    <link rel="stylesheet" href="/static/css/registro.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
    <!-- [LEY 21.719] Estilos de las casillas de consentimiento -->
    <link rel="stylesheet" href="/static/css/privacidad.css">
</head>
<body class="login-body">

    <div class="login-wrapper">
        <div class="login-left">
            <div class="login-brand">
                <div class="logo-icon">🎓</div>
                <div class="logo-info">
                    <h2>Mi Ayudante</h2>
                    <span>Tu futuro, nuestra guía</span>
                </div>
            </div>

            <div class="login-hero-text">
                <h1>Únete a <span>nuestra comunidad</span></h1>
                <p>Crea tu cuenta gratuita y comienza a explorar todas las herramientas para descubrir tu vocación.</p>
            </div>
        </div>

        <div class="login-right">
            <div class="login-form-container">
                <h2>Regístrate para continuar</h2>

                <?php if (!empty($error)): ?>
                    <div class="alert alert-error" style="color: #dc2626; background: #ffeeef; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px;">
                        <?= htmlspecialchars($error) ?>
                    </div>
                <?php endif; ?>

                <?php if (!empty($exito)): ?>
                    <div class="alert alert-success" style="color: #16a34a; background: #f0fdf4; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px;">
                        <?= htmlspecialchars($exito) ?>
                    </div>
                <?php endif; ?>

                <form action="registro.php" method="POST">

                    <div class="form-group-line">
                        <label for="correo">Correo</label>
                        <input type="email" id="correo" name="correo" placeholder="Ingresa un correo" value="<?= htmlspecialchars($correo ?? '') ?>" required>
                    </div>

                    <div class="form-group-line">
                        <label for="nombre">Nombre</label>
                        <input type="text" id="nombre" name="nombre" placeholder="Ingresa un nombre" value="<?= htmlspecialchars($nombre ?? '') ?>" required>
                    </div>

                    <div class="form-group-line">
                        <label for="apellidos">Apellidos</label>
                        <input type="text" id="apellidos" name="apellidos" placeholder="Ingresa apellidos" value="<?= htmlspecialchars($apellidos ?? '') ?>" required>
                    </div>

                    <div class="form-group-line">
                        <label for="password">Contraseña</label>
                        <input type="password" id="password" name="password" placeholder="Crea una contraseña" required>
                    </div>

                    <!-- [LEY 21.719] Consentimiento expreso: casillas SIN marcar por defecto -->
                    <div class="consentimiento">
                        <label class="consentimiento-opcion">
                            <input type="checkbox" name="acepta_privacidad" value="1" required>
                            <span>Leí y acepto la <a href="privacidad.php" target="_blank">Política de privacidad</a>. Autorizo a Mi Ayudante a guardar mi correo, mi nombre y los resultados de mi test vocacional para mostrarlos en mi cuenta.</span>
                        </label>
                        <label class="consentimiento-opcion">
                            <input type="checkbox" name="mayor_14" value="1" required>
                            <span>Declaro tener 14 años o más. Si eres menor de 14, puedes usar el buscador, el comparador, el test y el asistente sin crear una cuenta.</span>
                        </label>
                    </div>

                    <button type="submit" class="btn-submit" style="margin-top: 15px;">Registrarme</button>
                </form>

                <p class="login-subtitle" style="margin-top: 20px; text-align: center;">
                    ¿Ya tienes cuenta en Mi Ayudante? <br>
                    <a href="login.php">Inicia sesión aquí</a>.
                </p>
            </div>
        </div>
    </div>

</body>
</html>
