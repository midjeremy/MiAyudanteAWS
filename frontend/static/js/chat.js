// Asistente de IA: conecta el widget flotante con templates/chat.php
(function () {
    const widget = document.getElementById('ai-assistant-wrapper');
    if (!widget) {
        return;
    }

    const URL_CHAT = '/templates/chat.php';
    const CLAVE_HISTORIAL = 'miayudante_chat';
    const MAX_TURNOS = 10; // Debe coincidir con MAX_TURNOS_HISTORIAL en chatbot/views.py
    const ERROR_CONEXION = 'No pudimos conectar con el asistente. Revisa tu conexión e inténtalo de nuevo.';

    const cuerpo = widget.querySelector('.ai-chat-body');
    const formulario = widget.querySelector('.ai-chat-footer');
    const entrada = formulario.querySelector('input');
    const boton = formulario.querySelector('button');

    cuerpo.setAttribute('aria-live', 'polite');

    // sessionStorage puede fallar en modo privado: el chat sigue funcionando sin guardar
    function leerHistorial() {
        try {
            const guardado = JSON.parse(sessionStorage.getItem(CLAVE_HISTORIAL));
            return Array.isArray(guardado) ? guardado : [];
        } catch (error) {
            return [];
        }
    }

    function guardarHistorial() {
        try {
            sessionStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(historial));
        } catch (error) {
            // Sin almacenamiento la conversación solo dura hasta cambiar de página
        }
    }

    function agregarMensaje(texto, clase) {
        const mensaje = document.createElement('div');
        mensaje.className = 'ai-message conversacion ' + clase;
        // textContent evita que una respuesta se interprete como HTML
        mensaje.textContent = texto;
        cuerpo.appendChild(mensaje);
        bajarAlFinal();
        return mensaje;
    }

    function bajarAlFinal() {
        cuerpo.scrollTop = cuerpo.scrollHeight;
    }

    function bloquearEnvio(bloqueado) {
        entrada.disabled = bloqueado;
        boton.disabled = bloqueado;
        if (!bloqueado && widget.open) {
            entrada.focus();
        }
    }

    async function pedirRespuesta(texto) {
        const respuesta = await fetch(URL_CHAT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mensaje: texto, historial: historial }),
        });
        const datos = await respuesta.json();
        if (!respuesta.ok || !datos.respuesta) {
            throw new Error(datos.error || ERROR_CONEXION);
        }
        return datos.respuesta;
    }

    let historial = leerHistorial();
    historial.forEach(function (turno) {
        agregarMensaje(turno.content, turno.role === 'user' ? 'user' : 'bot');
    });

    formulario.addEventListener('submit', async function (evento) {
        evento.preventDefault();
        const texto = entrada.value.trim();
        if (!texto) {
            return;
        }

        entrada.value = '';
        agregarMensaje(texto, 'user');
        const escribiendo = agregarMensaje('Escribiendo...', 'bot escribiendo');
        bloquearEnvio(true);

        try {
            const respuesta = await pedirRespuesta(texto);
            escribiendo.remove();
            agregarMensaje(respuesta, 'bot');
            historial = historial.concat(
                { role: 'user', content: texto },
                { role: 'assistant', content: respuesta }
            ).slice(-MAX_TURNOS);
            guardarHistorial();
        } catch (error) {
            escribiendo.remove();
            const mensaje = error instanceof SyntaxError || error instanceof TypeError
                ? ERROR_CONEXION
                : error.message;
            agregarMensaje(mensaje, 'bot error');
        } finally {
            bloquearEnvio(false);
        }
    });

    // Mientras está cerrado el panel no tiene altura, así que se ajusta al abrirlo
    widget.addEventListener('toggle', function () {
        if (widget.open) {
            bajarAlFinal();
            entrada.focus();
        }
    });
})();
