<?php
// [LEY 21.719] ARCHIVO NUEVO. Deber de información y transparencia: Política de privacidad.
// Al cambiar el texto, subir VERSION y avisar a Fernanda para que suba VERSION_POLITICA en
// backend_api/usuarios/privacidad.py (así se pide aceptar de nuevo la nueva versión).
session_start();
const VERSION = '2026-11';
const FECHA = '17 de noviembre de 2026';
$con_sesion = isset($_SESSION['usuario']);
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Política de privacidad - Mi Ayudante</title>
    <link rel="icon" type="image/png" href="/static/img/Birrete.ico">
    <link rel="stylesheet" href="/static/css/carreras.css">
    <link rel="stylesheet" href="/static/css/privacidad.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body class="portal-body">

    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-logo-icon">🎓</span>
            <div class="nav-logo-text">
                <a href="index.php"><strong style="color: #000000;">Mi Ayudante</strong></a>
                <span>Tu futuro, nuestra guía</span>
            </div>
        </div>
        <ul class="nav-links">
            <li><a href="index.php">Inicio</a></li>
            <li><a href="carreras.php">Explorar carreras</a></li>
            <li><a href="comparar.php">Comparar</a></li>
            <li><a href="pages/test.php">Test vocacional</a></li>
        </ul>
        <div class="nav-actions">
            <?php if ($con_sesion): ?>
                <a href="perfil.php#privacidad" class="btn-action-saved">Mis datos</a>
            <?php else: ?>
                <a href="login.php" class="btn-action-saved">Iniciar sesión</a>
            <?php endif; ?>
        </div>
    </nav>

    <main class="politica">
        <h1>Política de privacidad</h1>
        <p class="politica-version">Versión <?= VERSION ?> · vigente desde el <?= FECHA ?></p>

        <p>
            Mi Ayudante es una plataforma para buscar, comparar y explorar carreras de educación superior,
            desarrollada como proyecto de título de Ingeniería en Informática de INACAP. Esta política explica
            qué datos personales tratamos, para qué y cómo puedes ejercer tus derechos, según la
            Ley N.° 21.719 de protección de datos personales.
        </p>

        <h2>1. Responsable</h2>
        <p>Equipo Mi Ayudante. Contacto: <a href="mailto:privacidad@mi-ayudante.cl">privacidad@mi-ayudante.cl</a>.</p>

        <h2>2. Qué datos tratamos</h2>
        <ul>
            <li><strong>Si creas una cuenta:</strong> correo, nombre, apellidos y tu contraseña cifrada (nunca la vemos).</li>
            <li><strong>Si haces el test con sesión iniciada:</strong> tus respuestas y el resultado por dimensión y área.</li>
            <li><strong>Al usar el sitio:</strong> tu dirección IP, solo para proteger el servicio de abusos.</li>
        </ul>
        <p>Sin cuenta puedes usar el buscador, el comparador, el test y el asistente: en ese caso no guardamos datos tuyos.</p>

        <h2>3. Para qué los usamos</h2>
        <p>
            Para crear y mantener tu cuenta, guardar y mostrarte tu resultado del test, y proteger la plataforma.
            No vendemos tus datos ni los usamos para publicidad. El test es un apoyo de autoexploración:
            no es un diagnóstico ni una decisión automatizada sobre ti.
        </p>

        <h2>4. Base legal</h2>
        <p>Tu consentimiento, que entregas al crear la cuenta y puedes revocar en cualquier momento eliminándola.</p>

        <h2>5. Con quién se comparten</h2>
        <ul>
            <li><strong>Amazon Web Services</strong> (Estados Unidos): aloja la plataforma y la base de datos.</li>
            <li><strong>OpenAI</strong> (Estados Unidos): procesa los mensajes que escribes al asistente para responderte. Mi Ayudante no guarda esos mensajes; por eso te pedimos no escribir datos personales en el chat.</li>
        </ul>
        <p>Ambos actúan como encargados del tratamiento. Al estar fuera de Chile, se trata de transferencias internacionales de datos.</p>

        <h2>6. Cuánto tiempo los guardamos</h2>
        <p>
            Mientras tengas tu cuenta. Si no inicias sesión en 24 meses, la cuenta y sus datos se eliminan
            automáticamente. Las copias de respaldo se sobrescriben a los 7 días.
        </p>

        <h2>7. Tus derechos</h2>
        <p>Tienes derecho de acceso, rectificación, supresión, oposición, portabilidad y bloqueo. Desde tu perfil puedes:</p>
        <ul>
            <li>Descargar todos tus datos (acceso y portabilidad).</li>
            <li>Corregir tu nombre (rectificación).</li>
            <li>Borrar tus resultados del test o eliminar tu cuenta (supresión).</li>
        </ul>
        <p>Para oposición, bloqueo u otra solicitud escribe a <a href="mailto:privacidad@mi-ayudante.cl">privacidad@mi-ayudante.cl</a>. Respondemos en un máximo de 30 días corridos.</p>

        <h2>8. Menores de edad</h2>
        <p>Las cuentas son para personas de 14 años o más. Los menores de 14 pueden usar la plataforma sin cuenta.</p>

        <h2>9. Seguridad</h2>
        <p>Conexión cifrada (HTTPS), contraseñas protegidas con hash, base de datos sin acceso público y monitoreo permanente.</p>

        <h2>10. Cambios a esta política</h2>
        <p>Si cambia, actualizaremos la versión y la fecha, y te pediremos aceptarla de nuevo al iniciar sesión.</p>
    </main>

    <footer class="footer">
        <p>© <?= date("Y") ?> Mi Ayudante</p>
    </footer>
</body>
</html>
