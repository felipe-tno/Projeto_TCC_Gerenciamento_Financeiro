const chatBox = document.getElementById("chat");
const input = document.getElementById("mensagem");
const btnEnviar = document.getElementById("enviar");
const graficoCanvas = document.getElementById("grafico");

// Cria botão para gerar gráfico
const botaoGrafico = document.createElement("button");
botaoGrafico.textContent = "📊 Gerar Gráfico";
botaoGrafico.id = "gerarGrafico";
botaoGrafico.style.marginTop = "10px";
document.querySelector(".chat-container").appendChild(botaoGrafico);

// Cria espaço para mostrar o total do mês
const totalMesDiv = document.createElement("div");
totalMesDiv.id = "totalMes";
totalMesDiv.style.textAlign = "center";
totalMesDiv.style.marginTop = "8px";
totalMesDiv.style.fontWeight = "bold";
document.querySelector(".chat-container").appendChild(totalMesDiv);

let grafico = null;

// === Funções de chat ===
btnEnviar.addEventListener("click", enviarMensagem);
input.addEventListener("keypress", function (e) {
    if (e.key === "Enter") enviarMensagem();
});

function adicionarMensagem(texto, classe) {
    const div = document.createElement("div");
    div.className = `mensagem ${classe}`;
    div.innerText = texto;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function enviarMensagem() {
    const texto = input.value.trim();
    if (!texto) return;

    adicionarMensagem(texto, "usuario");
    fetch("/mensagem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto }),
    })
        .then((res) => res.json())
        .then((data) => {
            adicionarMensagem(data.resposta, "bot");
        })
        .catch((err) => console.error(err));

    input.value = "";
}

// === Funções do gráfico ===

// Clique no botão para gerar gráfico
botaoGrafico.addEventListener("click", atualizarGrafico);

function atualizarGrafico() {
    fetch("/gastos")
        .then((res) => res.json())
        .then((dados) => {
            if (!dados || dados.length === 0) {
                alert("Nenhum gasto encontrado para este mês.");
                return;
            }

            // Filtro por mês atual
            const agora = new Date();
            const mesAtual = agora.getMonth() + 1;
            const anoAtual = agora.getFullYear();

            const gastosMes = dados.filter((g) => {
                const dataGasto = new Date(g.criado_em);
                return (
                    dataGasto.getMonth() + 1 === mesAtual &&
                    dataGasto.getFullYear() === anoAtual
                );
            });

            if (gastosMes.length === 0) {
                alert("Sem dados de gastos neste mês.");
                totalMesDiv.textContent = "";
                return;
            }

            // Agrupar por categoria
            const totais = {};
            gastosMes.forEach((g) => {
                const cat = g.categoria || "outros";
                totais[cat] = (totais[cat] || 0) + g.valor;
            });

            const categorias = Object.keys(totais);
            const valores = Object.values(totais);

            // Cores (todas iguais – azul)
            const corPadrao = "rgba(54, 162, 235, 0.7)";
            const cores = categorias.map(() => corPadrao);

            // Destroi gráfico anterior se existir
            if (grafico) grafico.destroy();

            // Renderiza novo gráfico
            grafico = new Chart(graficoCanvas, {
                type: "bar",
                data: {
                    labels: categorias,
                    datasets: [
                        {
                            label: "Gastos deste mês (R$)",
                            data: valores,
                            backgroundColor: cores,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        title: {
                            display: true,
                            text: `Distribuição de Gastos - ${mesAtual}/${anoAtual}`,
                        },
                    },
                    scales: {
                        y: { beginAtZero: true },
                    },
                },
            });

            // Calcular e exibir total do mês
            const totalMes = valores.reduce((acc, v) => acc + v, 0);
            totalMesDiv.textContent = `💰 Total de gastos em ${mesAtual}/${anoAtual}: R$ ${totalMes.toFixed(2)}`;
        })
        .catch((err) => console.error("Erro ao gerar gráfico:", err));
}

// Ajusta o tamanho do gráfico
graficoCanvas.style.width = "350px";
graficoCanvas.style.height = "180px";

// --- MODAL DE ORÇAMENTO ---
const modal = document.getElementById("orcamentoModal");
const btnDefinir = document.getElementById("definirOrcamento");
const btnSalvar = document.getElementById("salvarOrcamento");
const btnCancelar = document.getElementById("cancelarOrcamento");

btnDefinir.addEventListener("click", () => modal.style.display = "flex");
btnCancelar.addEventListener("click", () => modal.style.display = "none");

btnSalvar.addEventListener("click", () => {
    const categoria = document.getElementById("categoriaOrcamento").value;
    const valor = parseFloat(document.getElementById("valorOrcamento").value);
    if (!valor || valor <= 0) {
        alert("Por favor, insira um valor válido.");
        return;
    }

    fetch("/definir_orcamento", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ categoria, valor })
    })
    .then(res => res.json())
    .then(data => {
        adicionarMensagem(data.mensagem, "bot");
        modal.style.display = "none";
        atualizarGrafico();
    })
    .catch(err => console.error(err));
});
