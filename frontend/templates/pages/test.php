<?php
// Test vocacional Ikigai: 40 ítems validados por juicio de expertos, escala Likert de 1 a 5.
// Las preguntas y el cálculo vienen de Django (/api/v1/ikigai/...). Si hay sesión, se envía
// el JWT para que Django guarde el resultado del usuario.
require_once __DIR__ . '/../sesion.php';
requerir_sesion();
require_once __DIR__ . '/../api.php';

$usuario = $_SESSION['usuario'] ?? null;
$token = $_SESSION['token_acceso'] ?? null;
$avatar = (!empty($usuario['avatar'])) ? $usuario['avatar'] : '/static/img/gato-avatar.png';

// Token simple contra envíos desde otros sitios (el resultado puede quedar guardado en la cuenta)
if (empty($_SESSION['csrf_test'])) {
    $_SESSION['csrf_test'] = bin2hex(random_bytes(16));
}

$datos_test = api_get('/api/v1/ikigai/preguntas/');
$preguntas = $datos_test['preguntas'] ?? [];
$escala = $datos_test['escala'] ?? [];
$dimensiones = [];
foreach ($datos_test['dimensiones'] ?? [] as $dim) {
    $dimensiones[$dim['clave']] = $dim;
}

$respuestas = [];   // valores marcados, para no perderlos si hay un error
$resultado = null;
$error = '';
$aviso = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && !empty($preguntas)) {
    if (!hash_equals($_SESSION['csrf_test'], (string) ($_POST['csrf'] ?? ''))) {
        $error = 'La página expiró. Vuelve a enviar el test.';
    }

    $valores_validos = array_map(fn($op) => (int) $op['valor'], $escala);
    $enviadas = is_array($_POST['respuestas'] ?? null) ? $_POST['respuestas'] : [];
    $faltantes = [];
    foreach ($preguntas as $p) {
        $numero = (int) $p['numero'];
        $valor = is_scalar($enviadas[$numero] ?? null) ? (int) $enviadas[$numero] : 0;
        if (in_array($valor, $valores_validos, true)) {
            $respuestas[(string) $numero] = $valor;
        } else {
            $faltantes[] = $numero;
        }
    }

    if ($error === '' && !empty($faltantes)) {
        $error = 'Responde todas las preguntas. Faltan: ' . implode(', ', $faltantes) . '.';
    }

    if ($error === '') {
        // (object) para que json_encode envíe {"1": 4, ...} y no una lista
        $envio = ['respuestas' => (object) $respuestas];
        $r = api_post('/api/v1/ikigai/resultado/', $envio, $token);
        if ($r['codigo'] === 401 && $token !== null) {
            // El token venció: se calcula igual, pero sin guardar
            $r = api_post('/api/v1/ikigai/resultado/', $envio);
            $aviso = 'Tu sesión expiró, así que este resultado no quedó guardado. Inicia sesión de nuevo para guardarlo.';
        }

        if (in_array($r['codigo'], [200, 201], true) && is_array($r['datos'])) {
            $resultado = $r['datos'];
        } elseif ($r['codigo'] === 400) {
            $error = $r['datos']['error'] ?? 'Revisa tus respuestas.';
        } else {
            $error = 'No pudimos calcular tu resultado. Inténtalo más tarde.';
        }
    }
}

// Si no hay un resultado nuevo, mostrar el último guardado del usuario (si existe)
$resultado_anterior = null;
if ($resultado === null && $token !== null && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    $r = api_solicitud('GET', '/api/v1/ikigai/resultado/', null, $token);
    if ($r['codigo'] === 200 && is_array($r['datos'])) {
        $resultado_anterior = $r['datos'];
    }
}

function fecha_resultado(?string $iso): string {
    if (!$iso) {
        return '';
    }
    $fecha = date_create($iso);
    return $fecha ? $fecha->format('d-m-Y') : '';
}

function porcentaje_texto($valor): string {
    return number_format((float) $valor, 0, ',', '.') . ' %';
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test vocacional - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/carreras.css">
    <link rel="stylesheet" href="/static/css/test.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body class="portal-body">

    <!-- BARRA DE NAVEGACIÓN SUPERIOR UNIFICADA -->
    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-logo-icon">🎓</span>
            <div class="nav-logo-text">
                <strong>Mi Ayudante</strong>
                <span>Tu futuro, nuestra guía</span>
            </div>
        </div>
        <ul class="nav-links">
            <li><a href="../index.php">Inicio</a></li>
            <li><a href="../carreras.php">Explorar carreras</a></li>
            <li><a href="../comparar.php">Comparar</a></li>
            <li><a href="test.php" class="active" aria-current="page">Test vocacional</a></li>
        </ul>
        <div class="nav-actions">
            <a href="../guardados.php" class="btn-action-saved" title="Guardados">
                <span>❤️</span> Guardados
            </a>
            <?php if ($usuario): ?>
                <details class="user-menu-container">
                    <summary class="user-menu-btn" title="Perfil">
                        <img src="<?= htmlspecialchars($avatar) ?>" alt="Perfil" class="user-avatar-img">
                        <span class="dropdown-arrow">▼</span>
                    </summary>
                    <div class="user-dropdown">
                        <a href="../perfil.php" class="dropdown-item">Perfil</a>
                        <div class="dropdown-divider"></div>
                        <a href="../logout.php" class="dropdown-item logout-item">Cerrar sesión</a>
                    </div>
                </details>
            <?php else: ?>
                <a href="../login.php" class="btn-action-saved">Iniciar sesión</a>
            <?php endif; ?>
        </div>
    </nav>

    <main class="test-contenedor">

        <header class="test-cabecera">
            <h1>Test vocacional Ikigai</h1>
            <p>
                Responde cada afirmación según cuánto te representa. No hay respuestas correctas ni mejores que otras:
                el resultado es orientativo, no es un diagnóstico y no reemplaza la orientación de profesionales.
            </p>
            <?php if (!$usuario): ?>
                <p class="test-nota">
                    Puedes hacer el test sin cuenta. Si <a href="../login.php">inicias sesión</a>, guardaremos tu resultado.
                </p>
            <?php endif; ?>
        </header>

        <?php if ($aviso !== ''): ?>
            <div class="test-alerta test-alerta-aviso" role="status"><?= htmlspecialchars($aviso) ?></div>
        <?php endif; ?>

        <?php if ($error !== ''): ?>
            <div class="test-alerta test-alerta-error" role="alert"><?= htmlspecialchars($error) ?></div>
        <?php endif; ?>

        <?php
        $mostrar = $resultado ?? $resultado_anterior;
        if ($mostrar !== null):
            $areas_top = array_slice($mostrar['areas'] ?? [], 0, 3);
        ?>
            <!-- RESULTADO -->
            <section class="test-tarjeta test-resultado" id="resultado" aria-labelledby="titulo-resultado">
                <h2 id="titulo-resultado">
                    <?= $resultado !== null ? 'Tu resultado' : 'Tu último resultado' ?>
                </h2>
                <?php if (!empty($mostrar['guardado'])): ?>
                    <p class="test-nota">
                        <?= $resultado !== null ? 'Quedó guardado en tu cuenta' : 'Guardado' ?>
                        <?= fecha_resultado($mostrar['creado_en'] ?? null) ? ' el ' . htmlspecialchars(fecha_resultado($mostrar['creado_en'])) : '' ?>.
                    </p>
                <?php endif; ?>

                <h3>Dimensiones Ikigai</h3>
                <ul class="test-barras">
                    <?php foreach ($mostrar['dimensiones'] ?? [] as $dim): ?>
                        <li>
                            <div class="test-barra-texto">
                                <strong><?= htmlspecialchars($dim['nombre']) ?></strong>
                                <span><?= porcentaje_texto($dim['porcentaje']) ?></span>
                            </div>
                            <div class="test-barra" role="img"
                                 aria-label="<?= htmlspecialchars($dim['nombre'] . ': ' . porcentaje_texto($dim['porcentaje'])) ?>">
                                <span style="width: <?= max(0, min(100, (float) $dim['porcentaje'])) ?>%"></span>
                            </div>
                            <small><?= htmlspecialchars($dim['descripcion']) ?></small>
                        </li>
                    <?php endforeach; ?>
                </ul>

                <h3>Áreas con mayor coincidencia</h3>
                <ol class="test-areas-top">
                    <?php foreach ($areas_top as $area): ?>
                        <li>
                            <div class="test-barra-texto">
                                <strong><?= htmlspecialchars($area['nombre']) ?></strong>
                                <span><?= porcentaje_texto($area['porcentaje']) ?></span>
                            </div>
                            <small>Por ejemplo: <?= htmlspecialchars($area['ejemplos']) ?>.</small>
                        </li>
                    <?php endforeach; ?>
                </ol>

                <details class="test-todas-areas">
                    <summary>Ver todas las áreas</summary>
                    <ul class="test-barras">
                        <?php foreach ($mostrar['areas'] ?? [] as $area): ?>
                            <li>
                                <div class="test-barra-texto">
                                    <span><?= htmlspecialchars($area['nombre']) ?></span>
                                    <span><?= porcentaje_texto($area['porcentaje']) ?></span>
                                </div>
                                <div class="test-barra test-barra-fina" aria-hidden="true">
                                    <span style="width: <?= max(0, min(100, (float) $area['porcentaje'])) ?>%"></span>
                                </div>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                </details>

                <div class="test-acciones">
                    <a href="../carreras.php" class="test-btn test-btn-primario">Explorar carreras</a>
                    <a href="#formulario-test" class="test-btn test-btn-secundario">
                        <?= $resultado !== null ? 'Responder de nuevo' : 'Hacer el test otra vez' ?>
                    </a>
                </div>
            </section>
        <?php endif; ?>

        <?php if (empty($preguntas)): ?>
            <div class="test-alerta test-alerta-error" role="alert">
                No pudimos cargar las preguntas del test. Inténtalo más tarde.
            </div>
        <?php else: ?>
            <!-- FORMULARIO DEL TEST -->
            <form method="post" action="test.php#resultado" class="test-formulario" id="formulario-test">
                <input type="hidden" name="csrf" value="<?= htmlspecialchars($_SESSION['csrf_test']) ?>">

                <div class="test-tarjeta test-escala" aria-hidden="true">
                    <strong>Escala de respuesta</strong>
                    <ul>
                        <?php foreach ($escala as $op): ?>
                            <li><span><?= (int) $op['valor'] ?></span> <?= htmlspecialchars($op['etiqueta']) ?></li>
                        <?php endforeach; ?>
                    </ul>
                </div>

                <?php
                $dimension_actual = null;
                foreach ($preguntas as $p):
                    $numero = (int) $p['numero'];
                    if ($p['dimension'] !== $dimension_actual):
                        if ($dimension_actual !== null) {
                            echo '</section>';
                        }
                        $dimension_actual = $p['dimension'];
                        $dim = $dimensiones[$dimension_actual] ?? ['nombre' => $dimension_actual, 'descripcion' => ''];
                ?>
                    <section class="test-tarjeta test-seccion" aria-labelledby="dim-<?= htmlspecialchars($dimension_actual) ?>">
                        <h2 id="dim-<?= htmlspecialchars($dimension_actual) ?>"><?= htmlspecialchars($dim['nombre']) ?></h2>
                        <p class="test-nota"><?= htmlspecialchars($dim['descripcion']) ?></p>
                <?php endif; ?>

                        <fieldset class="test-pregunta">
                            <legend><span class="test-numero"><?= $numero ?>.</span> <?= htmlspecialchars($p['enunciado']) ?></legend>
                            <div class="test-opciones">
                                <?php foreach ($escala as $op):
                                    $valor = (int) $op['valor'];
                                    $id = "p{$numero}-{$valor}";
                                    $marcado = (($respuestas[(string) $numero] ?? null) === $valor && $resultado === null);
                                ?>
                                    <div class="test-opcion">
                                        <input type="radio" id="<?= $id ?>" name="respuestas[<?= $numero ?>]"
                                               value="<?= $valor ?>" required <?= $marcado ? 'checked' : '' ?>>
                                        <label for="<?= $id ?>">
                                            <span class="test-opcion-valor"><?= $valor ?></span>
                                            <span class="test-opcion-texto"><?= htmlspecialchars($op['etiqueta']) ?></span>
                                        </label>
                                    </div>
                                <?php endforeach; ?>
                            </div>
                        </fieldset>
                <?php endforeach; ?>
                    </section>

                <div class="test-enviar">
                    <p class="test-nota">Todas las preguntas son obligatorias.</p>
                    <button type="submit" class="test-btn test-btn-primario">Ver mi resultado</button>
                </div>
            </form>
        <?php endif; ?>

    </main>

</body>
</html>
