<?php
session_start();
require_once 'api.php';
$error = "";

// Inicializar la variable de correo como vacía al entrar a la página
$correo = "";

// Si ya inició sesión, redirigir al index
if (isset($_SESSION['usuario'])) {
    header("Location: index.php");
    exit();
}

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $correo = trim($_POST["correo"] ?? "");
    $password = $_POST["password"] ?? "";

    if (empty($correo) || empty($password)) {
        $error = "Por favor, completa todos los campos.";
    } else {
        // Django valida la contraseña y entrega un token JWT
        $resultado = api_post('/api/v1/auth/login/', ['correo' => $correo, 'password' => $password]);

        if ($resultado['codigo'] === 200) {
            // Nuevo identificador de sesión al iniciar sesión, para evitar secuestro de sesión
            session_regenerate_id(true);
            $_SESSION['usuario'] = $resultado['datos']['usuario'];
            $_SESSION['token_acceso'] = $resultado['datos']['access'];
            $_SESSION['token_refresco'] = $resultado['datos']['refresh'];

            header("Location: index.php");
            exit();
        } elseif ($resultado['codigo'] === 401) {
            $error = "Correo o contraseña incorrectos, o la cuenta no existe.";
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
    <title>Iniciar sesión - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/login.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body class="login-body">

    <div class="login-wrapper">
        <!-- ILUSTRACIÓN Y MARCA -->
        <div class="login-left">
            <div class="login-brand">
                <div class="logo-icon">🎓</div>
                <div class="logo-info">
                    <h2>Mi Ayudante</h2>
                    <span>Tu futuro, nuestra guía</span>
                </div>
            </div>

            <div class="login-hero-text">
                <h1>Tu futuro <span>empieza hoy</span></h1>
                <p>Inicia sesión para acceder a herramientas que te ayudarán a encontrar la carrera ideal para ti.</p>
            </div>

            <div class="login-image-container">
                <img src="/static/img/login-ilustracion.png" alt="Estudiantes orientándose">
            </div>
        </div>

        <!-- SECCIÓN DERECHA: FORMULARIO -->
        <div class="login-right">
            <div class="login-form-container">
                <h2>Iniciar sesión</h2>
                <p class="login-subtitle">Bienvenido de nuevo a Mi Ayudante</p>

                <?php if (!empty($error)): ?>
                    <div class="alert-error" style="color: #dc2626; background: #ffeeef; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px;">
                        <?= htmlspecialchars($error) ?>
                    </div>
                <?php endif; ?>

                <!-- Formulario con autocomplete deshabilitado -->
                <form action="login.php" method="POST" autocomplete="off">
                    <div class="form-group">
                        <label for="correo">Correo electrónico</label>
                        <div class="input-with-icon">
                            <span class="input-icon">✉️</span>
                            <input type="email" id="correo" name="correo" placeholder="Ingresa tu correo electrónico" value="<?= htmlspecialchars($correo) ?>" autocomplete="off" required>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="password">Contraseña</label>
                        <div class="input-with-icon">
                            <span class="input-icon">🔒</span>
                            <input type="password" id="password" name="password" placeholder="Ingresa tu contraseña" autocomplete="new-password" required>
                            <span class="toggle-password">👁️</span>
                        </div>
                    </div>

                    <div class="form-options">
                        <label class="checkbox-container">
                            <input type="checkbox" name="recordarme"> Recordarme
                        </label>
                        <a href="recuperar.php" class="forgot-link">¿Olvidaste tu contraseña?</a>
                    </div>

                    <button type="submit" class="btn-submit">Iniciar sesión</button>
                </form>

                <p class="register-redirect">
                    ¿No tienes una cuenta? <a href="registro.php">Regístrate aquí</a>
                </p>
            </div>
        </div>
    </div>

</body>
</html>