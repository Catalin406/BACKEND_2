/* ============================================================
   STATIC/JS/APP.JS / COMPORTAMIENTO LIGERO DE LA INTERFAZ
   JavaScript nativo (sin jQuery):
   - Cuenta regresiva de la pantalla de redirección (respaldo del
     <meta http-equiv="refresh">).
   - Carga de datos en el modal de confirmación de cambio de estado.
   - Envío automático del selector "Ver carro de".
   ============================================================ */
(function () {
    "use strict";

    /* ============================================================
       CUENTA REGRESIVA DE REDIRECCIÓN
       ============================================================ */
    function iniciarCuentaRegresiva() {
        var contador = document.querySelector("[data-cuenta-regresiva]");
        if (!contador) {
            return;
        }
        var segundos = parseInt(contador.getAttribute("data-cuenta-regresiva"), 10) || 3;
        var destino = contador.getAttribute("data-destino") || "/";
        contador.textContent = segundos;
        var intervalo = window.setInterval(function () {
            segundos -= 1;
            contador.textContent = Math.max(segundos, 0);
            if (segundos <= 0) {
                window.clearInterval(intervalo);
                window.location.replace(destino);
            }
        }, 1000);
    }

    /* ============================================================
       MODAL DE CAMBIO DE ESTADO
       Los botones indican el estado destino y el texto a mostrar.
       ============================================================ */
    function prepararModalEstado() {
        var modal = document.getElementById("modalEstado");
        if (!modal) {
            return;
        }
        modal.addEventListener("show.bs.modal", function (evento) {
            var boton = evento.relatedTarget;
            if (!boton) {
                return;
            }
            modal.querySelector("[name='estado']").value = boton.getAttribute("data-estado");
            modal.querySelector("[data-modal-titulo]").textContent = boton.getAttribute("data-titulo");
            modal.querySelector("[data-modal-mensaje]").textContent = boton.getAttribute("data-mensaje");
            var confirmar = modal.querySelector("[data-modal-confirmar]");
            confirmar.textContent = boton.getAttribute("data-boton");
            confirmar.className = "btn " + boton.getAttribute("data-clase");
        });
    }

    /* ============================================================
       SELECTOR AUTOMÁTICO
       ============================================================ */
    function prepararSelectoresAutomaticos() {
        document.querySelectorAll("[data-enviar-al-cambiar]").forEach(function (campo) {
            campo.addEventListener("change", function () {
                if (campo.value) {
                    campo.form.submit();
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        iniciarCuentaRegresiva();
        prepararModalEstado();
        prepararSelectoresAutomaticos();
    });
})();
