(function () {
    "use strict";

    var elementoDados = document.getElementById("dados-grafico");
    var canvas = document.getElementById("grafico-serie");
    var falha = document.getElementById("grafico-falha");

    function mostrarFalha() {
        if (canvas) { canvas.hidden = true; }
        if (falha) { falha.hidden = false; }
    }

    if (!elementoDados || !canvas || typeof Chart === "undefined") {
        mostrarFalha();
        return;
    }

    var dados = JSON.parse(elementoDados.textContent);
    var COR_NORMAL = "rgba(54, 116, 181, 0.55)";
    var COR_ANOMALIA = "rgba(192, 38, 38, 0.85)";

    function formatar(valor) {
        return valor === null || valor === undefined
            ? "—"
            : Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
    }

    try {
        new Chart(canvas, {
            data: {
                labels: dados.rotulos,
                datasets: [
                    {
                        type: "bar",
                        label: "Notificações",
                        data: dados.observado,
                        backgroundColor: dados.anomalia.map(function (acima) {
                            return acima ? COR_ANOMALIA : COR_NORMAL;
                        }),
                        order: 3
                    },
                    {
                        type: "line",
                        label: "Média móvel (8 semanas)",
                        data: dados.media_movel,
                        borderColor: "#1f2937",
                        backgroundColor: "#1f2937",
                        borderWidth: 2,
                        pointRadius: 0,
                        spanGaps: false,
                        order: 2
                    },
                    {
                        type: "line",
                        label: "Limite μ + 2σ",
                        data: dados.limite_superior,
                        borderColor: "#b45309",
                        backgroundColor: "#b45309",
                        borderWidth: 2,
                        borderDash: [6, 4],
                        pointRadius: 0,
                        spanGaps: false,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    x: { ticks: { maxRotation: 60, autoSkip: true, maxTicksLimit: 14 } },
                    y: { beginAtZero: true, title: { display: true, text: "Notificações" } }
                },
                plugins: {
                    legend: { position: "bottom" },
                    tooltip: {
                        callbacks: {
                            label: function (item) {
                                return item.dataset.label + ": " + formatar(item.parsed.y);
                            }
                        }
                    }
                }
            }
        });
    } catch (erro) {
        mostrarFalha();
    }
})();