<?php
// [LEY 21.719] ARCHIVO NUEVO. Para cuentas creadas antes de la política de privacidad (o con una
// versión anterior): login.php redirige aquí cuando Django responde consentimiento_vigente = false.
session_start();
require_once 'api.php';

if (!isset($_SESSION['usuario'], $_SESSION['token_acceso'])) {
    header('Location: login.php');
    exit;
}
if (empty($_SESSION['csrf_privacidad'])) {
    $_SESSION['csrf_privacidad'] = bin2hex(random_bytes(16));
}

$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($_SESSION['csrf_privacidad'], (string) ($_POST['csrf'] ?? ''))) {
        $error = 'La página expiró. Vuelve a intentarlo.';
    } elseif (!isset($_POST['acepta_privacidad'], $_POST['mayor_14'])) {
        $error = 'Para seguir usando tu cuenta debes aceptar la política y declarar tener 14 años o más.';
    } else {
        $r = api_solicitud('POST', '/api/v1/auth/consentimiento/',
            ['acepta_privacidad' => true, 'mayor_14' => true], $_SESSION['token_acceso']);
        if ($r['codigo'] === 201) {
            unset($_SESSION['consentimiento_pendiente']);
            header('Location: index.php');
            exit;
        } elseif ($r['codigo'] === 401) {
            // El token venció: se pide iniciar sesión de nuevo
            header('Location: logout.php');
            exit;
        } else {
            $error = $r['datos']['error'] ?? 'No pudimos guardar tu respuesta. Inténtalo más tarde.';
        }
    }
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Política de privacidad - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/registro.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
    <link rel="stylesheet" href="/static/css/privacidad.css">
</head>
<body class="login-body">
    <div class="login-wrapper">
        <div class="login-right" style="margin: 0 auto;">
            <div class="login-form-container">
                <h2>Actualizamos nuestra Política de privacidad</h2>
                <p class="login-subtitle">
                    Para cumplir la Ley N.° 21.719 de protección de datos personales necesitamos tu aceptación
                    para seguir guardando los datos de tu cuenta.
                </p>

                <?php if ($error): ?>
                    <div class="alert alert-error" style="color: #dc2626; background: #ffeeef; padding: 10px; border-radius: 8px; font-size: 14px; margin-bottom: 16px;">
                        <?= htmlspecialchars($error) ?>
                    </div>
                <?php endif; ?>

                <form method="POST" action="aceptar_politica.php">
                    <input type="hidden" name="csrf" value="<?= htmlspecialchars($_SESSION['csrf_privacidad']) ?>">
                    <div class="consentimiento">
                        <label class="consentimiento-opcion">
                            <input type="checkbox" name="acepta_privacidad" value="1" required>
                            <span>Leí y acepto la <a href="privacidad.php" target="_blank">Política de privacidad</a>.</span>
                        </label>
                        <label class="consentimiento-opcion">
                            <input type="checkbox" name="mayor_14" value="1" required>
                            <span>Declaro tener 14 años o más.</span>
                        </label>
                    </div>
                    <button type="submit" class="btn-submit" style="margin-top: 15px;">Aceptar y continuar</button>
                </form>

                <p class="login-subtitle" style="margin-top: 20px; text-align: center;">
                    ¿No quieres aceptarla? Puedes <a href="logout.php">cerrar sesión</a> y seguir usando la plataforma sin cuenta,
                    o eliminar tu cuenta desde <a href="perfil.php#privacidad">tu perfil</a>.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
