<?php
session_start();
$error = "";

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
        $encontrado = false;
        $nombre_usuario = "";

        // Recorrer la lista de usuarios registrados para validar
        if (isset($_SESSION['usuarios_registrados'])) {
            foreach ($_SESSION['usuarios_registrados'] as $user) {
                if ($user['correo'] === $correo && $user['password'] === $password) {
                    $encontrado = true;
                    $nombre_usuario = $user['nombre'];
                    break;
                }
            }
        }

        if ($encontrado) {
            // Guardar sesión activa del usuario correcto
            $_SESSION['usuario'] = [
                'correo' => $correo,
                'nombre' => $nombre_usuario
            ];

            header("Location: index.php");
            exit();
        } else {
            // Si pones un correo al azar o contraseña errónea, muestra error y no entra
            $error = "Correo o contraseña incorrectos, o la cuenta no existe.";
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

                <form action="login.php" method="POST">
                    <div class="form-group">
                        <label for="correo">Correo electrónico</label>
                        <div class="input-with-icon">
                            <span class="input-icon">✉️</span>
                            <input type="email" id="correo" name="correo" placeholder="Ingresa tu correo electrónico" value="<?= htmlspecialchars($correo ?? '') ?>" required>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="password">Contraseña</label>
                        <div class="input-with-icon">
                            <span class="input-icon">🔒</span>
                            <input type="password" id="password" name="password" placeholder="Ingresa tu contraseña" required>
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